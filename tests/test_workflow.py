from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_aws_operation import CommandFailure, CommandRunner, OperationExecutor, redirect_matches  # noqa: E402
from safe_summary import build_summary  # noqa: E402
from workflow_gate import GateFailure, resolve_head, resolve_operation  # noqa: E402


class WorkflowSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        workflows = list((ROOT / ".github/workflows").glob("*"))
        self.assertEqual([path.name for path in workflows], ["aws.yml"])
        self.source = workflows[0].read_text(encoding="utf-8")

    def test_trigger_gate_concurrency_and_permissions_are_fixed(self) -> None:
        for required in (
            "push:\n    branches:\n      - main",
            "workflow_dispatch:",
            "type: choice",
            "group: henrybissonnette-aws-operations",
            "cancel-in-progress: false",
            "queue: max",
            "timeout-minutes: 120",
            "vars.AWS_BOOTSTRAPPED == 'true'",
            "id-token: write",
            "contents: read",
        ):
            self.assertIn(required, self.source)
        self.assertEqual(self.source.count("id-token: write"), 1)
        for forbidden in ("pull_request", "schedule:", "environment:", "cancel-in-progress: true"):
            self.assertNotIn(forbidden, self.source)

    def test_dispatch_has_only_the_closed_operation_enum(self) -> None:
        input_block = self.source.split("inputs:", 1)[1].split("permissions:", 1)[0]
        self.assertEqual(re.findall(r"^      ([a-z_-]+):$", input_block, flags=re.MULTILINE), ["operation"])
        for operation in ("deploy", "plan", "refresh-plan", "site-status"):
            self.assertIn(f"          - {operation}\n", input_block)
        for forbidden in ("command", "path", "root", "account", "region", "target", "probe"):
            self.assertNotRegex(input_block, rf"^\s+{forbidden}:")

    def test_actions_and_tools_are_immutable(self) -> None:
        action_refs = re.findall(r"uses:\s+([^\s]+)", self.source)
        self.assertEqual(len(action_refs), 5)
        for reference in action_refs:
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")
        self.assertIn("python-version: 3.11.15", self.source)
        self.assertIn("scripts/install_tool.py terraform", self.source)
        self.assertIn("scripts/install_aws_cli.py", self.source)
        self.assertIn("role-duration-seconds: 7200", self.source)
        self.assertEqual((ROOT / ".aws-cli-version").read_text(encoding="utf-8").strip(), "2.36.21")
        installer = (ROOT / "scripts/install_aws_cli.py").read_text(encoding="utf-8")
        self.assertIn("b665b24dae1ed70bc38ef03998570307a0363839196b564bf04f8d7502132b9a", installer)
        self.assertIn("4cad0c3f28d6f598863dfe9cfef7fd166e23b853a9ccddd1b73a0938c92ce3e4", installer)
        self.assertIn('"aarch64"', installer)

    def test_validation_precedes_oidc_and_uses_actual_checks(self) -> None:
        validation = self.source.split("  aws-operation:", 1)[0]
        for command in (
            "scripts/workflow_gate.py",
            "scripts/check_site.py",
            "scripts/check_infrastructure.sh",
            "python3 -m unittest discover -s tests -v",
        ):
            self.assertIn(command, validation)
        self.assertNotIn("id-token: write", validation)
        self.assertLess(self.source.index("Install pinned authority-path tools"), self.source.index("Exchange exact-main OIDC identity"))

    def test_no_artifact_or_unsafe_output_path_exists(self) -> None:
        for forbidden in (
            "upload-artifact",
            "download-artifact",
            "tee ",
            "set -x",
            "terraform show |",
            "secrets.AWS",
            "refresh-only -auto-approve",
        ):
            self.assertNotIn(forbidden, self.source)


class WorkflowGateTests(unittest.TestCase):
    def checkout(self, sha: str) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / ".git").mkdir()
        (root / ".git/HEAD").write_text(f"{sha}\n", encoding="utf-8")
        return temporary

    def test_push_and_dispatch_resolve_only_on_exact_main_checkout(self) -> None:
        sha = "a" * 40
        temporary = self.checkout(sha)
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.assertEqual(resolve_operation("push", "refs/heads/main", "site-status", sha, root), "deploy")
        for operation in ("deploy", "plan", "refresh-plan", "site-status"):
            self.assertEqual(resolve_operation("workflow_dispatch", "refs/heads/main", operation, sha, root), operation)

    def test_unsupported_event_ref_operation_and_checkout_fail_closed(self) -> None:
        sha = "b" * 40
        temporary = self.checkout(sha)
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        cases = (
            ("pull_request", "refs/heads/main", "deploy", sha),
            ("workflow_dispatch", "refs/tags/v1", "deploy", sha),
            ("workflow_dispatch", "refs/heads/main", "destroy", sha),
            ("push", "refs/heads/main", "", "c" * 40),
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(GateFailure):
                resolve_operation(*case, root)


class SafeSummaryTests(unittest.TestCase):
    def test_hostile_plan_is_reduced_to_exact_allowlist(self) -> None:
        sentinel = "SENTINEL_TOKEN_DO_NOT_RENDER"
        plan = {
            "resource_changes": [
                {
                    "address": f"aws_secret.{sentinel}",
                    "change": {
                        "actions": ["create", "delete"],
                        "before": {"password": sentinel},
                        "after": {"token": sentinel},
                        "after_sensitive": {"token": True},
                    },
                },
                {"address": "aws_s3_bucket.site", "change": {"actions": ["update"]}},
            ],
            "diagnostics": [{"detail": sentinel}],
            "variables": {"private_email": {"value": sentinel}},
        }
        summary = build_summary("d" * 40, "none", "success", plan)
        self.assertEqual(
            list(summary),
            ["source_sha", "account", "region", "action_counts", "public_endpoints", "category", "status"],
        )
        self.assertEqual(summary["action_counts"]["replace"], 1)
        self.assertEqual(summary["action_counts"]["update"], 1)
        encoded = json.dumps(summary)
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn("address", encoded)
        self.assertNotIn("password", encoded)
        self.assertEqual(summary["public_endpoints"], {"staging_hostname": None, "authoritative_name_servers": []})

    def test_malformed_input_returns_one_fixed_safe_failure(self) -> None:
        first = build_summary("not-a-sha", "anything", "success", {"raw": "SECRET"})
        second = build_summary("e" * 40, "none", "success", {"resource_changes": "hostile"})
        absent_changes = build_summary("e" * 40, "none", "success", {})
        self.assertEqual(first, second)
        self.assertEqual(absent_changes, first)
        self.assertEqual(first["category"], "renderer-failure")
        self.assertEqual(first["status"], "safe-failure")
        self.assertNotIn("SECRET", json.dumps(first))

        hostile_endpoint = build_summary(
            "e" * 40,
            "none",
            "success",
            None,
            {"staging_hostname": "SENTINEL", "authoritative_name_servers": []},
        )
        self.assertEqual(hostile_endpoint, first)


class PublicProbeTests(unittest.TestCase):
    def test_redirect_query_preservation_is_semantic_not_order_sensitive(self) -> None:
        self.assertTrue(redirect_matches("/about.html?source=workflow&empty=", "/about.html"))
        self.assertTrue(redirect_matches("/about.html?empty=&source=workflow", "/about.html"))
        for mismatch in (
            "/about.html?source=workflow",
            "/about.html?source=workflow&empty=&extra=value",
            "/about.html?source=other&empty=",
            "https://example.com/about.html?source=workflow&empty=",
            "/projects.html?source=workflow&empty=",
            "/about.html?source=workflow&empty=#fragment",
        ):
            with self.subTest(mismatch=mismatch):
                self.assertFalse(redirect_matches(mismatch, "/about.html"))


class FakeRunner(CommandRunner):
    def __init__(
        self,
        workspace: Path,
        fail_at: str | None = None,
        unexpected_at: str | None = None,
        workload_exists: bool = True,
        malformed_plan: bool = False,
        malformed_foundation: bool = False,
        malformed_invalidation: bool = False,
        no_drift: bool = False,
    ):
        super().__init__(workspace)
        self.fail_at = fail_at
        self.unexpected_at = unexpected_at
        self.workload_exists = workload_exists
        self.malformed_plan = malformed_plan
        self.malformed_foundation = malformed_foundation
        self.malformed_invalidation = malformed_invalidation
        self.no_drift = no_drift
        self.refresh_plan = False
        self.commands: list[list[str]] = []
        self.commands_by_label: dict[str, list[str]] = {}

    def run(self, label: str, command: list[str], allowed=(0,)) -> Path:
        if label == "terraform-plan":
            self.refresh_plan = "-refresh-only" in command
        self.trace.append(label)
        self.commands.append(command)
        self.commands_by_label[label] = command
        capture = self.workspace / f"{len(self.trace):02d}-{label}.private"
        values = {
            "terraform-version": "Terraform v1.15.8\n",
            "aws-version": "aws-cli/2.36.21 Python/3.13 Linux/x86_64\n",
            "sts-identity": json.dumps({"Account": "241077340022", "Arn": "SENTINEL_PRIVATE_ARN"}),
            "foundation-stack": json.dumps({"Stacks": ["malformed"] if self.malformed_foundation else [{
                "StackStatus": "UPDATE_COMPLETE", "Outputs": [
                {"OutputKey": "AccountId", "OutputValue": "241077340022"},
                {"OutputKey": "ApplyRoleArn", "OutputValue": "arn:aws:iam::241077340022:role/henrybissonnette-github-apply"},
                {"OutputKey": "StateBucketName", "OutputValue": "henrybissonnette-terraform-state-241077340022"},
                {"OutputKey": "BudgetTopicArn", "OutputValue": "arn:aws:sns:us-east-1:241077340022:henrybissonnette-budget-notifications"},
            ]}]}),
            "foundation-template": json.dumps({"TemplateBody": json.loads((ROOT / "infra/aws/bootstrap/template.json").read_text(encoding="utf-8"))}),
            "foundation-resources": json.dumps({"StackResources": [{"ResourceStatus": "CREATE_COMPLETE"}] * 7}),
            "foundation-role": json.dumps({"Role": {"MaxSessionDuration": 7200, "AssumeRolePolicyDocument": {"Statement": [{
                "Action": "sts:AssumeRoleWithWebIdentity",
                "Condition": {"StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    "token.actions.githubusercontent.com:sub": "repo:henrybissonnette/henrydbissonnette:ref:refs/heads/main",
                }},
            }]}}}),
            "foundation-role-policies": json.dumps({"AttachedPolicies": [{"PolicyName": "AdministratorAccess", "PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}]}),
            "foundation-oidc-provider": json.dumps({"Url": "token.actions.githubusercontent.com", "ClientIDList": ["sts.amazonaws.com"]}),
            "foundation-versioning": json.dumps({"Status": "Enabled"}),
            "foundation-encryption": json.dumps({"ServerSideEncryptionConfiguration": {"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}, "BucketKeyEnabled": False}]}}),
            "foundation-ownership": json.dumps({"OwnershipControls": {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]}}),
            "foundation-public-block": json.dumps({"PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True}}),
            "foundation-subscription": json.dumps({"Subscriptions": [{"Protocol": "email", "SubscriptionArn": "SENTINEL_PRIVATE_SUBSCRIPTION_ARN"}]}),
            "foundation-state-namespace": json.dumps({"Contents": [{"Key": "main/terraform.tfstate"}]} if self.workload_exists else {"KeyCount": 0}),
            "terraform-show-plan": json.dumps({
                **({} if self.refresh_plan else {"resource_changes": [{
                    "address": "SENTINEL_PRIVATE_ADDRESS",
                    "change": {
                        "actions": ["update"],
                        "before": {"secret": "SENTINEL"},
                    },
                }]}),
                **({} if self.no_drift else {"resource_drift": [{
                    "address": "SENTINEL_PRIVATE_DRIFT_ADDRESS",
                    "change": None if self.malformed_plan else {
                        "actions": ["update"],
                        "before": {"secret": "SENTINEL"},
                    },
                }]}),
            }),
            "terraform-output-content_bucket_name": "henry-content-bucket\n",
            "terraform-output-cloudfront_distribution_id": "EDIST123\n",
            "terraform-output-cloudfront_staging_hostname": "d123.cloudfront.net\n",
            "terraform-output-hosted_zone_name_servers": json.dumps([
                "ns-1.awsdns-1.com",
                "ns-2.awsdns-2.net",
                "ns-3.awsdns-3.org",
                "ns-4.awsdns-4.co.uk",
            ]),
            "cloudfront-invalidate": json.dumps(
                {"Invalidation": "malformed"}
                if self.malformed_invalidation else {"Invalidation": {"Id": "INV123"}}
            ),
        }
        descriptor = os.open(capture, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(values.get(label, ""))
        self.capture_modes.append(capture.stat().st_mode & 0o777)
        if label == "terraform-plan":
            plan_path = Path(next(argument.removeprefix("-out=") for argument in command if argument.startswith("-out=")))
            plan_descriptor = os.open(plan_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(plan_descriptor)
        if label == self.unexpected_at:
            raise RuntimeError("synthetic unexpected failure")
        if label == self.fail_at:
            raise CommandFailure(label)
        return capture


class OperationTraceTests(unittest.TestCase):
    def run_operation(
        self,
        operation: str,
        fail_at: str | None = None,
        fail_verification: bool = False,
        unexpected_at: str | None = None,
        workload_exists: bool = True,
        malformed_plan: bool = False,
        malformed_foundation: bool = False,
        malformed_invalidation: bool = False,
        no_drift: bool = False,
    ) -> tuple[OperationExecutor, int, dict, FakeRunner]:
        outer = tempfile.TemporaryDirectory()
        self.addCleanup(outer.cleanup)
        root = Path(outer.name)
        summary = root / "summary.md"
        created: list[FakeRunner] = []

        def factory(workspace: Path) -> FakeRunner:
            runner = FakeRunner(
                workspace,
                fail_at,
                unexpected_at,
                workload_exists,
                malformed_plan,
                malformed_foundation,
                malformed_invalidation,
                no_drift,
            )
            created.append(runner)
            return runner

        def verifier(hostname: str, bucket: str, attempts: int, delay: int) -> None:
            self.assertEqual(hostname, "d123.cloudfront.net")
            self.assertEqual(bucket, "henry-content-bucket")
            if fail_verification:
                raise ValueError("synthetic verifier failure")

        environment = {
            "GITHUB_SHA": resolve_head(ROOT),
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_STEP_SUMMARY": str(summary),
            "AWS_REGION": "us-east-1",
            "AWS_DEFAULT_REGION": "us-east-1",
            "TERRAFORM_BIN": "/fixed/terraform",
            "AWS_BIN": "/fixed/aws",
            "RUNNER_TEMP": str(root),
        }
        public_output = io.StringIO()
        public_error = io.StringIO()
        with (
            patch.dict(os.environ, environment, clear=False),
            redirect_stdout(public_output),
            redirect_stderr(public_error),
        ):
            executor = OperationExecutor(operation, factory, verifier)
            result = executor.execute()
        self.assertEqual(public_output.getvalue().count("AWS workflow result: "), 1)
        self.assertNotIn("SENTINEL", public_output.getvalue())
        self.assertNotIn("SENTINEL", public_error.getvalue())
        encoded = re.search(r"`(\{.*\})`", summary.read_text(encoding="utf-8")).group(1)
        return executor, result, json.loads(encoded), created[0]

    def test_all_operation_traces_have_fixed_authority(self) -> None:
        deploy, result, summary, runner = self.run_operation("deploy")
        self.assertEqual(result, 0)
        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["public_endpoints"]["staging_hostname"], "d123.cloudfront.net")
        self.assertEqual(len(summary["public_endpoints"]["authoritative_name_servers"]), 4)
        ordered = [
            "terraform-plan",
            "terraform-show-plan",
            "terraform-apply",
            "site-upload",
            "site-reconcile",
            "cloudfront-invalidate",
            "cloudfront-wait",
            "public-verification",
        ]
        self.assertEqual([deploy.trace.index(label) for label in ordered], sorted(deploy.trace.index(label) for label in ordered))
        self.assertEqual(deploy.trace.count("terraform-plan"), 1)
        self.assertEqual(deploy.trace.count("terraform-apply"), 1)
        self.assertEqual(deploy.trace.count("cloudfront-invalidate"), 1)
        self.assertLess(deploy.trace.index("foundation-verified"), deploy.trace.index("terraform-init"))
        plan_command = runner.commands_by_label["terraform-plan"]
        apply_command = runner.commands_by_label["terraform-apply"]
        plan_path = next(argument.removeprefix("-out=") for argument in plan_command if argument.startswith("-out="))
        self.assertEqual(apply_command[-1], plan_path)
        upload_command = runner.commands_by_label["site-upload"]
        reconcile_command = runner.commands_by_label["site-reconcile"]
        # aws s3 sync deletes only when asked; the CLI has no --no-delete option.
        self.assertNotIn("--delete", upload_command)
        self.assertNotIn("--no-delete", upload_command)
        self.assertIn("--delete", reconcile_command)
        invalidation_command = runner.commands_by_label["cloudfront-invalidate"]
        self.assertEqual(invalidation_command[invalidation_command.index("--paths") + 1], "/*")
        self.assertTrue(all(mode == 0o600 for mode in deploy.capture_modes))
        self.assertFalse(deploy.last_workspace.exists())

        plan, result, _, _ = self.run_operation("plan")
        self.assertEqual(result, 0)
        self.assertIn("terraform-plan", plan.trace)
        self.assertNotIn("terraform-apply", plan.trace)
        self.assertNotIn("site-upload", plan.trace)

        refresh, result, refresh_summary, refresh_runner = self.run_operation("refresh-plan")
        self.assertEqual(result, 0)
        self.assertEqual(refresh_summary["action_counts"]["update"], 1)
        plan_command = refresh_runner.commands_by_label["terraform-plan"]
        self.assertIn("-refresh-only", plan_command)
        self.assertFalse(any("apply" in command for command in refresh_runner.commands))

        no_drift, result, no_drift_summary, _ = self.run_operation("refresh-plan", no_drift=True)
        self.assertEqual(result, 0)
        self.assertEqual(no_drift_summary["status"], "success")
        self.assertEqual(no_drift_summary["action_counts"], {
            "create": 0,
            "update": 0,
            "delete": 0,
            "replace": 0,
            "read": 0,
            "no-op": 0,
        })
        self.assertNotIn("terraform-apply", no_drift.trace)

        status, result, _, _ = self.run_operation("site-status")
        self.assertEqual(result, 0)
        self.assertNotIn("terraform-plan", status.trace)
        self.assertNotIn("terraform-apply", status.trace)
        self.assertIn("status-cloudfront", status.trace)
        self.assertIn("status-origin-access", status.trace)

        prework, result, summary, _ = self.run_operation("site-status", workload_exists=False)
        self.assertEqual(result, 0)
        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["category"], "foundation-ready")
        self.assertEqual(summary["action_counts"], {"create": 0, "update": 0, "delete": 0, "replace": 0, "read": 0, "no-op": 0})
        self.assertEqual(summary["public_endpoints"], {"staging_hostname": None, "authoritative_name_servers": []})
        self.assertIn("foundation-ready-workload-absent", prework.trace)
        self.assertNotIn("terraform-init", prework.trace)
        self.assertNotIn("terraform-plan", prework.trace)
        self.assertNotIn("terraform-apply", prework.trace)
        self.assertNotIn("status-cloudfront", prework.trace)

    def test_malformed_plan_is_a_bounded_plan_failure(self) -> None:
        executor, result, summary, _ = self.run_operation("refresh-plan", malformed_plan=True)
        self.assertEqual(result, 1)
        self.assertEqual(summary["source_sha"], resolve_head(ROOT))
        self.assertEqual(summary["category"], "plan-failed")
        self.assertEqual(summary["status"], "safe-failure")
        self.assertEqual(summary["action_counts"], {
            "create": 0,
            "update": 0,
            "delete": 0,
            "replace": 0,
            "read": 0,
            "no-op": 0,
        })
        self.assertIn("terraform-show-plan", executor.trace)

    def test_malformed_aws_shapes_keep_their_operation_categories(self) -> None:
        _, result, summary, _ = self.run_operation("site-status", malformed_foundation=True)
        self.assertEqual(result, 1)
        self.assertEqual(summary["category"], "foundation-failed")

        _, result, summary, _ = self.run_operation("deploy", malformed_invalidation=True)
        self.assertEqual(result, 1)
        self.assertEqual(summary["category"], "publication-failed")
        self.assertEqual(summary["status"], "inspection-required")

    def test_failures_stop_at_each_mutation_boundary_and_cleanup(self) -> None:
        cases = (
            ("sts-identity", "safe-failure", ("terraform-plan", "terraform-apply", "site-upload")),
            ("foundation-template", "safe-failure", ("terraform-init", "terraform-plan", "terraform-apply", "site-upload")),
            ("terraform-plan", "safe-failure", ("terraform-apply", "site-upload")),
            ("terraform-apply", "inspection-required", ("site-upload",)),
            ("site-upload", "inspection-required", ("site-reconcile", "cloudfront-invalidate")),
            ("site-reconcile", "inspection-required", ("cloudfront-invalidate",)),
            ("cloudfront-invalidate", "inspection-required", ("cloudfront-wait", "public-verification")),
        )
        for fail_at, expected_status, forbidden_after in cases:
            with self.subTest(fail_at=fail_at):
                executor, result, summary, _ = self.run_operation("deploy", fail_at=fail_at)
                self.assertEqual(result, 1)
                self.assertEqual(summary["status"], expected_status)
                for forbidden in forbidden_after:
                    self.assertNotIn(forbidden, executor.trace)
                self.assertFalse(executor.last_workspace.exists())

    def test_verification_failure_requires_inspection_and_cleans_up(self) -> None:
        executor, result, summary, _ = self.run_operation("deploy", fail_verification=True)
        self.assertEqual(result, 1)
        self.assertEqual(summary["category"], "verification-failed")
        self.assertEqual(summary["status"], "inspection-required")
        self.assertFalse(executor.last_workspace.exists())
        self.assertNotIn("SENTINEL", json.dumps(summary))

    def test_unexpected_failure_after_apply_is_never_reported_safe(self) -> None:
        executor, result, summary, _ = self.run_operation(
            "deploy",
            unexpected_at="terraform-output-content_bucket_name",
        )
        self.assertEqual(result, 1)
        self.assertEqual(summary["category"], "apply-uncertain")
        self.assertEqual(summary["status"], "inspection-required")
        self.assertFalse(executor.last_workspace.exists())


if __name__ == "__main__":
    unittest.main()
