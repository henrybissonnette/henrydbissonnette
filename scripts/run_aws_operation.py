#!/usr/bin/env python3
"""Execute one fixed AWS workflow operation with private command custody."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable

from safe_summary import EXPECTED_ACCOUNT, EXPECTED_REGION, append_summary, bounded_action_plan
from workflow_gate import MAIN_REF, resolve_head


ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_ROOT = ROOT / "infra/aws/terraform/main"
SITE_ROOT = ROOT / "site"
EXPECTED_BACKEND_BUCKET = "henrybissonnette-terraform-state-241077340022"
EXPECTED_BACKEND_KEY = "main/terraform.tfstate"
EXPECTED_BOOTSTRAP_STACK = "henrybissonnette-bootstrap"
EXPECTED_APPLY_ROLE = "henrybissonnette-github-apply"
EXPECTED_BUDGET_TOPIC = "henrybissonnette-budget-notifications"
EXPECTED_OIDC_SUBJECT = "repo:henrybissonnette/henrydbissonnette:ref:refs/heads/main"
BOOTSTRAP_TEMPLATE = ROOT / "infra/aws/bootstrap/template.json"
EXPECTED_TERRAFORM_VERSION = (ROOT / ".terraform-version").read_text(encoding="utf-8").strip()
EXPECTED_AWS_CLI_VERSION = (ROOT / ".aws-cli-version").read_text(encoding="utf-8").strip()
OPERATIONS = ("deploy", "plan", "refresh-plan", "site-status", "recover-lock")
REDIRECT_QUERY = (("source", "workflow"), ("empty", ""))


class CommandFailure(Exception):
    def __init__(self, label: str):
        super().__init__(label)
        self.label = label


class OperationFailure(Exception):
    def __init__(self, category: str, status: str):
        super().__init__(category)
        self.category = category
        self.status = status


class CommandRunner:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.trace: list[str] = []
        self.capture_modes: list[int] = []
        self.environment = os.environ.copy()
        for name in (
            "TF_LOG",
            "TF_LOG_PATH",
            "TF_CLI_ARGS",
            "TF_CLI_ARGS_plan",
            "TF_CLI_ARGS_apply",
            "AWS_CLI_AUTO_PROMPT",
        ):
            self.environment.pop(name, None)
        self.environment["TF_IN_AUTOMATION"] = "1"
        self.environment["AWS_PAGER"] = ""

    def run(self, label: str, command: list[str], allowed: Iterable[int] = (0,)) -> Path:
        self.trace.append(label)
        capture = self.workspace / f"{len(self.trace):02d}-{label}.private"
        descriptor = os.open(capture, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=self.environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
            )
        self.capture_modes.append(capture.stat().st_mode & 0o777)
        if completed.returncode not in set(allowed):
            raise CommandFailure(label)
        return capture


def private_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def private_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("private response must be an object")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def http_request(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers={"Accept-Encoding": "identity", "User-Agent": "henry-site-verifier/1"})
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=20) as response:
            return response.status, dict(response.headers.items()), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def redirect_matches(location: str | None, expected_path: str) -> bool:
    if not isinstance(location, str):
        return False
    parsed = urllib.parse.urlsplit(location)
    return (
        parsed.scheme == ""
        and parsed.netloc == ""
        and parsed.path == expected_path
        and parsed.fragment == ""
        and Counter(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        == Counter(REDIRECT_QUERY)
    )


def verify_public_site(hostname: str, bucket: str, attempts: int = 20, delay_seconds: int = 15) -> None:
    if re.fullmatch(r"[a-z0-9.-]+", hostname) is None or re.fullmatch(r"[a-z0-9.-]+", bucket) is None:
        raise ValueError("unsafe named output")
    expected_pages = {
        "/": SITE_ROOT / "index.html",
        "/about.html": SITE_ROOT / "about.html",
        "/projects.html": SITE_ROOT / "projects.html",
        "/contact.html": SITE_ROOT / "contact.html",
        "/404.html": SITE_ROOT / "404.html",
    }
    last_failure: Exception | None = None
    for attempt in range(attempts):
        try:
            for path, source in expected_pages.items():
                status, _, body = http_request(f"https://{hostname}{path}")
                if status != 200 or body != source.read_bytes():
                    raise ValueError("published page mismatch")
            status, _, body = http_request(f"https://{hostname}/workflow-verifier-missing")
            if status != 404 or body != (SITE_ROOT / "404.html").read_bytes():
                raise ValueError("custom 404 mismatch")
            for old, new in {
                "/resume/": "/about.html",
                "/programming/": "/projects.html",
                "/design/": "/projects.html",
            }.items():
                query = urllib.parse.urlencode(REDIRECT_QUERY)
                status, headers, _ = http_request(f"https://{hostname}{old}?{query}")
                location = headers.get("Location") or headers.get("location")
                if status != 308 or not redirect_matches(location, new):
                    raise ValueError("edge redirect mismatch")
            status, _, _ = http_request(f"https://{bucket}.s3.{EXPECTED_REGION}.amazonaws.com/index.html")
            if status != 403:
                raise ValueError("direct S3 access was not denied")
            return
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_failure = exc
            if attempt + 1 < attempts:
                time.sleep(delay_seconds)
    raise ValueError("bounded public verification failed") from last_failure


def active_hosts(staging_hostname: str) -> list[str]:
    phase = (TERRAFORM_ROOT / "terraform.tfvars").read_text(encoding="utf-8")
    if "custom_domain_enabled = false" in phase:
        return [staging_hostname]
    if "custom_domain_enabled = true" in phase:
        return [staging_hostname, "henrybissonnette.com", "www.henrybissonnette.com"]
    raise ValueError("committed custom-domain phase is invalid")


class OperationExecutor:
    def __init__(
        self,
        operation: str,
        runner_factory: Callable[[Path], CommandRunner] = CommandRunner,
        verifier: Callable[[str, str, int, int], None] = verify_public_site,
    ) -> None:
        if operation not in OPERATIONS:
            raise ValueError("unsupported operation")
        self.operation = operation
        self.runner_factory = runner_factory
        self.verifier = verifier
        self.trace: list[str] = []
        self.capture_modes: list[int] = []
        self.last_workspace: Path | None = None
        self.plan: dict | None = None
        self.public_endpoints: dict | None = None
        self.apply_started = False

    def checked(
        self,
        runner: CommandRunner,
        label: str,
        command: list[str],
        category: str,
        status: str = "safe-failure",
        allowed: Iterable[int] = (0,),
    ) -> Path:
        try:
            return runner.run(label, command, allowed)
        except CommandFailure as exc:
            raise OperationFailure(category, status) from exc

    def foundation(self, runner: CommandRunner, aws: str) -> bool:
        try:
            stack = private_json(
                self.checked(
                    runner,
                    "foundation-stack",
                    [aws, "cloudformation", "describe-stacks", "--stack-name", EXPECTED_BOOTSTRAP_STACK, "--output", "json", "--no-cli-pager"],
                    "foundation-failed",
                )
            )
            stacks = stack.get("Stacks")
            if not isinstance(stacks, list) or len(stacks) != 1:
                raise ValueError("unexpected stack count")
            live_stack = stacks[0]
            if live_stack.get("StackStatus") not in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
                raise ValueError("bootstrap stack is not complete")
            outputs = {item.get("OutputKey"): item.get("OutputValue") for item in live_stack.get("Outputs", [])}
            expected_outputs = {"AccountId", "ApplyRoleArn", "StateBucketName", "BudgetTopicArn"}
            if set(outputs) != expected_outputs:
                raise ValueError("bootstrap output interface changed")
            if outputs["AccountId"] != EXPECTED_ACCOUNT or outputs["StateBucketName"] != EXPECTED_BACKEND_BUCKET:
                raise ValueError("bootstrap output identity changed")
            if outputs["ApplyRoleArn"] != f"arn:aws:iam::{EXPECTED_ACCOUNT}:role/{EXPECTED_APPLY_ROLE}":
                raise ValueError("bootstrap apply role changed")
            if outputs["BudgetTopicArn"] != f"arn:aws:sns:{EXPECTED_REGION}:{EXPECTED_ACCOUNT}:{EXPECTED_BUDGET_TOPIC}":
                raise ValueError("bootstrap topic changed")

            template = private_json(
                self.checked(
                    runner,
                    "foundation-template",
                    [aws, "cloudformation", "get-template", "--stack-name", EXPECTED_BOOTSTRAP_STACK, "--template-stage", "Original", "--output", "json", "--no-cli-pager"],
                    "foundation-failed",
                )
            ).get("TemplateBody")
            if isinstance(template, str):
                template = json.loads(template)
            committed_template = json.loads(BOOTSTRAP_TEMPLATE.read_text(encoding="utf-8"))
            if template != committed_template:
                raise ValueError("deployed bootstrap template differs from checkout")

            resources = private_json(
                self.checked(
                    runner,
                    "foundation-resources",
                    [aws, "cloudformation", "describe-stack-resources", "--stack-name", EXPECTED_BOOTSTRAP_STACK, "--output", "json", "--no-cli-pager"],
                    "foundation-failed",
                )
            ).get("StackResources")
            if not isinstance(resources, list) or len(resources) != 7:
                raise ValueError("bootstrap ownership set changed")
            if any(not str(item.get("ResourceStatus", "")).endswith("_COMPLETE") for item in resources):
                raise ValueError("bootstrap resource is not complete")

            role = private_json(
                self.checked(
                    runner,
                    "foundation-role",
                    [aws, "iam", "get-role", "--role-name", EXPECTED_APPLY_ROLE, "--output", "json", "--no-cli-pager"],
                    "foundation-failed",
                )
            ).get("Role", {})
            trust = role.get("AssumeRolePolicyDocument", {}).get("Statement", [])
            expected_condition = {
                "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                "token.actions.githubusercontent.com:sub": EXPECTED_OIDC_SUBJECT,
            }
            if role.get("MaxSessionDuration") != 7200 or len(trust) != 1:
                raise ValueError("apply role boundary changed")
            if trust[0].get("Action") != "sts:AssumeRoleWithWebIdentity":
                raise ValueError("apply role action changed")
            if trust[0].get("Condition", {}).get("StringEquals") != expected_condition:
                raise ValueError("apply role trust changed")
            policies = private_json(
                self.checked(
                    runner,
                    "foundation-role-policies",
                    [aws, "iam", "list-attached-role-policies", "--role-name", EXPECTED_APPLY_ROLE, "--output", "json", "--no-cli-pager"],
                    "foundation-failed",
                )
            ).get("AttachedPolicies")
            if policies != [{"PolicyName": "AdministratorAccess", "PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}]:
                raise ValueError("apply role policy changed")
            provider = private_json(
                self.checked(
                    runner,
                    "foundation-oidc-provider",
                    [aws, "iam", "get-open-id-connect-provider", "--open-id-connect-provider-arn", f"arn:aws:iam::{EXPECTED_ACCOUNT}:oidc-provider/token.actions.githubusercontent.com", "--output", "json", "--no-cli-pager"],
                    "foundation-failed",
                )
            )
            if provider.get("Url") != "token.actions.githubusercontent.com" or provider.get("ClientIDList") != ["sts.amazonaws.com"]:
                raise ValueError("OIDC provider boundary changed")

            versioning = private_json(
                self.checked(runner, "foundation-versioning", [aws, "s3api", "get-bucket-versioning", "--bucket", EXPECTED_BACKEND_BUCKET, "--output", "json", "--no-cli-pager"], "foundation-failed")
            )
            encryption = private_json(
                self.checked(runner, "foundation-encryption", [aws, "s3api", "get-bucket-encryption", "--bucket", EXPECTED_BACKEND_BUCKET, "--output", "json", "--no-cli-pager"], "foundation-failed")
            )
            ownership = private_json(
                self.checked(runner, "foundation-ownership", [aws, "s3api", "get-bucket-ownership-controls", "--bucket", EXPECTED_BACKEND_BUCKET, "--output", "json", "--no-cli-pager"], "foundation-failed")
            )
            public = private_json(
                self.checked(runner, "foundation-public-block", [aws, "s3api", "get-public-access-block", "--bucket", EXPECTED_BACKEND_BUCKET, "--output", "json", "--no-cli-pager"], "foundation-failed")
            )
            if versioning.get("Status") != "Enabled":
                raise ValueError("state bucket versioning changed")
            rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            if len(rules) != 1 or rules[0].get("ApplyServerSideEncryptionByDefault") != {"SSEAlgorithm": "AES256"}:
                raise ValueError("state bucket encryption changed")
            if rules[0].get("BucketKeyEnabled", False) is not False:
                raise ValueError("state bucket key setting changed")
            if ownership.get("OwnershipControls", {}).get("Rules") != [{"ObjectOwnership": "BucketOwnerEnforced"}]:
                raise ValueError("state bucket ownership changed")
            if public.get("PublicAccessBlockConfiguration") != {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }:
                raise ValueError("state bucket public block changed")

            subscriptions = private_json(
                self.checked(
                    runner,
                    "foundation-subscription",
                    [aws, "sns", "list-subscriptions-by-topic", "--topic-arn", outputs["BudgetTopicArn"], "--output", "json", "--no-cli-pager"],
                    "foundation-failed",
                )
            ).get("Subscriptions")
            if not isinstance(subscriptions, list) or len(subscriptions) != 1:
                raise ValueError("budget subscription count changed")
            subscription = subscriptions[0]
            if subscription.get("Protocol") != "email" or subscription.get("SubscriptionArn") in {None, "PendingConfirmation"}:
                raise ValueError("budget subscription is not confirmed")

            namespace = private_json(
                self.checked(
                    runner,
                    "foundation-state-namespace",
                    [aws, "s3api", "list-objects-v2", "--bucket", EXPECTED_BACKEND_BUCKET, "--prefix", "main/", "--output", "json", "--no-cli-pager"],
                    "foundation-failed",
                )
            )
            keys = [item.get("Key") for item in namespace.get("Contents", [])]
            if any(key not in {EXPECTED_BACKEND_KEY, f"{EXPECTED_BACKEND_KEY}.tflock"} for key in keys):
                raise ValueError("state namespace contains an unexpected key")
            runner.trace.append("foundation-verified")
            return EXPECTED_BACKEND_KEY in keys
        except (AttributeError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise OperationFailure("foundation-failed", "safe-failure") from exc

    def preflight(self, runner: CommandRunner, terraform: str, aws: str, sha: str) -> bool:
        if os.environ.get("GITHUB_REF") != MAIN_REF or resolve_head(ROOT) != sha:
            raise OperationFailure("validation-failed", "safe-failure")
        if os.environ.get("AWS_REGION") != EXPECTED_REGION or os.environ.get("AWS_DEFAULT_REGION") != EXPECTED_REGION:
            raise OperationFailure("identity-failed", "safe-failure")
        backend = (TERRAFORM_ROOT / "backend.tf").read_text(encoding="utf-8")
        for exact in (
            f'bucket       = "{EXPECTED_BACKEND_BUCKET}"',
            f'key          = "{EXPECTED_BACKEND_KEY}"',
            'region       = "us-east-1"',
            "use_lockfile = true",
        ):
            if exact not in backend:
                raise OperationFailure("validation-failed", "safe-failure")
        terraform_version = private_text(
            self.checked(runner, "terraform-version", [terraform, "version"], "validation-failed")
        ).splitlines()[0]
        if terraform_version != f"Terraform v{EXPECTED_TERRAFORM_VERSION}":
            raise OperationFailure("validation-failed", "safe-failure")
        aws_version = private_text(self.checked(runner, "aws-version", [aws, "--version"], "identity-failed"))
        if not aws_version.startswith(f"aws-cli/{EXPECTED_AWS_CLI_VERSION} "):
            raise OperationFailure("identity-failed", "safe-failure")
        identity = private_json(
            self.checked(
                runner,
                "sts-identity",
                [aws, "sts", "get-caller-identity", "--output", "json", "--no-cli-pager"],
                "identity-failed",
            )
        )
        if identity.get("Account") != EXPECTED_ACCOUNT:
            raise OperationFailure("identity-failed", "safe-failure")
        workload_exists = self.foundation(runner, aws)
        if self.operation == "site-status" and not workload_exists:
            runner.trace.append("foundation-ready-workload-absent")
            return False
        self.checked(
            runner,
            "terraform-init",
            [terraform, f"-chdir={TERRAFORM_ROOT}", "init", "-input=false", "-lockfile=readonly"],
            "initialization-failed",
        )
        return True

    def create_plan(self, runner: CommandRunner, terraform: str, workspace: Path) -> Path:
        plan_file = workspace / "terraform.tfplan"
        command = [
            terraform,
            f"-chdir={TERRAFORM_ROOT}",
            "plan",
            "-input=false",
            "-detailed-exitcode",
            f"-out={plan_file}",
        ]
        if self.operation == "refresh-plan":
            command.append("-refresh-only")
        self.checked(runner, "terraform-plan", command, "plan-failed", allowed=(0, 2))
        plan_json = self.checked(
            runner,
            "terraform-show-plan",
            [terraform, f"-chdir={TERRAFORM_ROOT}", "show", "-json", str(plan_file)],
            "plan-failed",
        )
        try:
            plan = private_json(plan_json)
            collection = "resource_drift" if self.operation == "refresh-plan" else "resource_changes"
            bounded_plan = bounded_action_plan(
                plan,
                collection,
                absent_is_empty=self.operation == "refresh-plan",
            )
        except (AttributeError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise OperationFailure("plan-failed", "safe-failure") from exc
        self.plan = bounded_plan
        return plan_file

    def output(self, runner: CommandRunner, terraform: str, name: str) -> str:
        path = self.checked(
            runner,
            f"terraform-output-{name}",
            [terraform, f"-chdir={TERRAFORM_ROOT}", "output", "-raw", name],
            "status-failed" if self.operation == "site-status" else "publication-failed",
            "safe-failure" if self.operation == "site-status" else "inspection-required",
        )
        return private_text(path)

    def named_outputs(self, runner: CommandRunner, terraform: str) -> tuple[str, str, str]:
        failure_category = "status-failed" if self.operation == "site-status" else "publication-failed"
        failure_status = "safe-failure" if self.operation == "site-status" else "inspection-required"
        bucket = self.output(runner, terraform, "content_bucket_name")
        distribution = self.output(runner, terraform, "cloudfront_distribution_id")
        hostname = self.output(runner, terraform, "cloudfront_staging_hostname")
        name_servers_path = self.checked(
            runner,
            "terraform-output-hosted_zone_name_servers",
            [terraform, f"-chdir={TERRAFORM_ROOT}", "output", "-json", "hosted_zone_name_servers"],
            failure_category,
            failure_status,
        )
        try:
            name_servers = json.loads(name_servers_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise OperationFailure(failure_category, failure_status) from exc
        if re.fullmatch(r"[a-z0-9.-]+", bucket) is None:
            raise OperationFailure(failure_category, failure_status)
        if re.fullmatch(r"[A-Z0-9]+", distribution) is None:
            raise OperationFailure(failure_category, failure_status)
        if re.fullmatch(r"d[a-z0-9]+\.cloudfront\.net", hostname) is None:
            raise OperationFailure(failure_category, failure_status)
        if (
            not isinstance(name_servers, list)
            or len(name_servers) != 4
            or len(set(name_servers)) != 4
            or not all(
                isinstance(server, str)
                and re.fullmatch(r"ns-[0-9]+\.awsdns-[0-9]+\.(?:com|net|org|co\.uk)", server)
                for server in name_servers
            )
        ):
            raise OperationFailure(failure_category, failure_status)
        self.public_endpoints = {
            "staging_hostname": hostname,
            "authoritative_name_servers": sorted(name_servers),
        }
        return bucket, distribution, hostname

    def deploy(self, runner: CommandRunner, terraform: str, aws: str, workspace: Path, plan_file: Path) -> None:
        self.apply_started = True
        marker = workspace / "apply-started"
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        self.checked(
            runner,
            "terraform-apply",
            [terraform, f"-chdir={TERRAFORM_ROOT}", "apply", "-input=false", "-auto-approve", str(plan_file)],
            "apply-uncertain",
            "inspection-required",
        )
        bucket, distribution, hostname = self.named_outputs(runner, terraform)
        self.checked(
            runner,
            "site-upload",
            [aws, "s3", "sync", str(SITE_ROOT), f"s3://{bucket}", "--only-show-errors", "--no-cli-pager"],
            "publication-failed",
            "inspection-required",
        )
        self.checked(
            runner,
            "site-reconcile",
            [aws, "s3", "sync", str(SITE_ROOT), f"s3://{bucket}", "--delete", "--only-show-errors", "--no-cli-pager"],
            "publication-failed",
            "inspection-required",
        )
        try:
            invalidation = private_json(
                self.checked(
                    runner,
                    "cloudfront-invalidate",
                    [
                        aws,
                        "cloudfront",
                        "create-invalidation",
                        "--distribution-id",
                        distribution,
                        "--paths",
                        "/*",
                        "--output",
                        "json",
                        "--no-cli-pager",
                    ],
                    "publication-failed",
                    "inspection-required",
                )
            )
            invalidation_id = invalidation.get("Invalidation", {}).get("Id")
        except (AttributeError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise OperationFailure("publication-failed", "inspection-required") from exc
        if not isinstance(invalidation_id, str) or re.fullmatch(r"[A-Z0-9]+", invalidation_id) is None:
            raise OperationFailure("publication-failed", "inspection-required")
        self.checked(
            runner,
            "cloudfront-wait",
            [
                aws,
                "cloudfront",
                "wait",
                "invalidation-completed",
                "--distribution-id",
                distribution,
                "--id",
                invalidation_id,
                "--no-cli-pager",
            ],
            "verification-failed",
            "inspection-required",
        )
        try:
            for active_host in active_hosts(hostname):
                self.verifier(active_host, bucket, 20, 15)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise OperationFailure("verification-failed", "inspection-required") from exc
        runner.trace.append("public-verification")

    def site_status(self, runner: CommandRunner, terraform: str, aws: str) -> None:
        bucket, distribution, hostname = self.named_outputs(runner, terraform)
        self.checked(
            runner,
            "status-cloudfront",
            [aws, "cloudfront", "get-distribution", "--id", distribution, "--output", "json", "--no-cli-pager"],
            "status-failed",
        )
        self.checked(
            runner,
            "status-origin-access",
            [aws, "s3api", "get-public-access-block", "--bucket", bucket, "--output", "json", "--no-cli-pager"],
            "status-failed",
        )
        try:
            for active_host in active_hosts(hostname):
                self.verifier(active_host, bucket, 1, 0)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise OperationFailure("status-failed", "safe-failure") from exc
        runner.trace.append("public-verification")

    def state_lock_keys(self, runner: CommandRunner, aws: str, label: str) -> list[str]:
        listing = private_json(
            self.checked(
                runner,
                label,
                [
                    aws,
                    "s3api",
                    "list-objects-v2",
                    "--bucket",
                    EXPECTED_BACKEND_BUCKET,
                    "--prefix",
                    f"{EXPECTED_BACKEND_KEY}.tflock",
                    "--max-keys",
                    "2",
                    "--output",
                    "json",
                    "--no-cli-pager",
                ],
                "lock-recovery-failed",
            )
        )
        contents = listing.get("Contents", [])
        if not isinstance(contents, list):
            raise OperationFailure("lock-recovery-failed", "safe-failure")
        try:
            keys = [item["Key"] for item in contents]
        except (KeyError, TypeError) as exc:
            raise OperationFailure("lock-recovery-failed", "safe-failure") from exc
        expected = f"{EXPECTED_BACKEND_KEY}.tflock"
        if any(not isinstance(key, str) or key != expected for key in keys) or len(keys) > 1:
            raise OperationFailure("lock-recovery-failed", "safe-failure")
        return keys

    def recover_lock(self, runner: CommandRunner, terraform: str, aws: str, workspace: Path) -> None:
        lock_key = f"{EXPECTED_BACKEND_KEY}.tflock"
        if not self.state_lock_keys(runner, aws, "state-lock-list-before"):
            runner.trace.append("state-lock-absent")
            return

        lock_file = workspace / "terraform-lock.private"
        self.checked(
            runner,
            "state-lock-get",
            [
                aws,
                "s3api",
                "get-object",
                "--bucket",
                EXPECTED_BACKEND_BUCKET,
                "--key",
                lock_key,
                "--no-cli-pager",
                str(lock_file),
            ],
            "lock-recovery-failed",
        )
        try:
            lock = private_json(lock_file)
            lock_id = lock.get("ID")
            operation = lock.get("Operation")
            created_text = lock.get("Created")
            path = lock.get("Path")
            if not isinstance(lock_id, str) or re.fullmatch(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                lock_id,
            ) is None:
                raise ValueError("lock ID is invalid")
            if operation not in {"OperationTypeApply", "OperationTypePlan", "OperationTypeRefreshOnlyPlan"}:
                raise ValueError("lock operation is invalid")
            if path != f"{EXPECTED_BACKEND_BUCKET}/{EXPECTED_BACKEND_KEY}":
                raise ValueError("lock path is invalid")
            if not isinstance(created_text, str):
                raise ValueError("lock creation time is invalid")
            created = datetime.fromisoformat(created_text.replace("Z", "+00:00"))
            now = datetime.now(UTC)
            if created > now or now - created < timedelta(minutes=5):
                raise ValueError("lock is not old enough for recovery")
        except (AttributeError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise OperationFailure("lock-recovery-failed", "safe-failure") from exc

        self.checked(
            runner,
            "terraform-force-unlock",
            [terraform, f"-chdir={TERRAFORM_ROOT}", "force-unlock", "-force", lock_id],
            "lock-recovery-failed",
            "inspection-required",
        )
        if self.state_lock_keys(runner, aws, "state-lock-list-after"):
            raise OperationFailure("lock-recovery-failed", "inspection-required")
        runner.trace.append("state-lock-recovered")

    def execute(self) -> int:
        os.umask(0o077)
        source_sha = os.environ.get("GITHUB_SHA", "")
        summary_value = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_value:
            print("AWS workflow operation failed within its bounded public result contract.", file=sys.stderr)
            return 1
        summary = Path(summary_value)
        terraform = os.environ.get("TERRAFORM_BIN", "")
        aws = os.environ.get("AWS_BIN", "")
        category = "none"
        status = "success"
        runner: CommandRunner | None = None
        previous_tf_data = os.environ.get("TF_DATA_DIR")
        runner_temp = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir()))
        try:
            with tempfile.TemporaryDirectory(prefix="henry-aws-", dir=runner_temp) as temporary:
                workspace = Path(temporary)
                workspace.chmod(0o700)
                terraform_data = workspace / "terraform-data"
                terraform_data.mkdir(mode=0o700)
                os.environ["TF_DATA_DIR"] = str(terraform_data)
                self.last_workspace = workspace
                runner = self.runner_factory(workspace)
                if not terraform or not aws:
                    raise OperationFailure("validation-failed", "safe-failure")
                workload_exists = self.preflight(runner, terraform, aws, source_sha)
                if self.operation == "site-status":
                    if workload_exists:
                        self.site_status(runner, terraform, aws)
                    else:
                        category = "foundation-ready"
                elif self.operation == "recover-lock":
                    self.recover_lock(runner, terraform, aws, workspace)
                else:
                    plan_file = self.create_plan(runner, terraform, workspace)
                    if self.operation == "deploy":
                        self.deploy(runner, terraform, aws, workspace, plan_file)
                self.trace = list(runner.trace)
                self.capture_modes = list(runner.capture_modes)
        except OperationFailure as exc:
            category = exc.category
            status = exc.status
            if runner is not None:
                self.trace = list(runner.trace)
                self.capture_modes = list(runner.capture_modes)
        except Exception:  # A public authority boundary must never emit an unbounded traceback.
            category = "apply-uncertain" if self.apply_started else "renderer-failure"
            status = "inspection-required" if self.apply_started else "safe-failure"
        if previous_tf_data is None:
            os.environ.pop("TF_DATA_DIR", None)
        else:
            os.environ["TF_DATA_DIR"] = previous_tf_data
        try:
            encoded_summary = append_summary(
                summary,
                source_sha,
                category,
                status,
                self.plan,
                self.public_endpoints,
            )
        except Exception:
            print("AWS workflow summary could not be written; the run is non-success.", file=sys.stderr)
            return 1
        print(f"AWS workflow result: {encoded_summary}")
        if status != "success":
            print("AWS workflow operation failed within its bounded public result contract.", file=sys.stderr)
            return 1
        print("AWS workflow operation completed with a bounded public result.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation", required=True, choices=OPERATIONS)
    args = parser.parse_args()
    return OperationExecutor(args.operation).execute()


if __name__ == "__main__":
    raise SystemExit(main())
