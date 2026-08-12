#!/usr/bin/env python3
"""Credential-free structural checks for the permanent AWS source boundary."""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "infra/aws/bootstrap"
TERRAFORM = ROOT / "infra/aws/terraform/main"
TEMPLATE = BOOTSTRAP / "template.json"
EXPECTED_BUCKET = "henrybissonnette-terraform-state-241077340022"
EXPECTED_STATE_KEY = "main/terraform.tfstate"
EXPECTED_SUBJECT = "repo:henrybissonnette/henrydbissonnette:ref:refs/heads/main"


class CheckFailure(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def resource(template: dict[str, Any], name: str, resource_type: str) -> dict[str, Any]:
    candidate = template["Resources"].get(name)
    require(candidate is not None, f"bootstrap resource {name}: missing")
    require(candidate.get("Type") == resource_type, f"bootstrap resource {name}: expected {resource_type}")
    return candidate


def statement(document: dict[str, Any], sid: str) -> dict[str, Any]:
    matches = [item for item in document["Statement"] if item.get("Sid") == sid]
    require(len(matches) == 1, f"policy statement {sid}: expected exactly one")
    return matches[0]


def walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def check_bootstrap() -> None:
    definitions = [path for path in BOOTSTRAP.iterdir() if path.suffix in {".json", ".yaml", ".yml"}]
    require(definitions == [TEMPLATE], "bootstrap: expected exactly one CloudFormation definition template.json")

    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    require(template.get("AWSTemplateFormatVersion") == "2010-09-09", "bootstrap: CloudFormation version missing")
    expected_resources = {
        "GitHubOidcProvider",
        "GitHubApplyRole",
        "TerraformStateBucket",
        "TerraformStateBucketPolicy",
        "BudgetNotificationsTopic",
        "BudgetNotificationsTopicPolicy",
        "BudgetNotificationSubscription",
    }
    require(set(template.get("Resources", {})) == expected_resources, "bootstrap: resource ownership set changed")

    parameters = template.get("Parameters", {})
    require(set(parameters) == {"BudgetNotificationEmail"}, "bootstrap parameters: only private budget email is allowed")
    email = parameters["BudgetNotificationEmail"]
    require(email.get("NoEcho") is True and "Default" not in email, "BudgetNotificationEmail: must be required NoEcho input")

    oidc = resource(template, "GitHubOidcProvider", "AWS::IAM::OIDCProvider")["Properties"]
    require(oidc.get("Url") == "https://token.actions.githubusercontent.com", "GitHubOidcProvider: exact issuer required")
    require(oidc.get("ClientIdList") == ["sts.amazonaws.com"], "GitHubOidcProvider: exact audience required")

    role = resource(template, "GitHubApplyRole", "AWS::IAM::Role")["Properties"]
    require(role.get("ManagedPolicyArns") == ["arn:aws:iam::aws:policy/AdministratorAccess"], "GitHubApplyRole: expected one broad AdministratorAccess policy")
    require(role.get("MaxSessionDuration") == 7200, "GitHubApplyRole: session must match the bounded 120-minute workflow")
    trust_statements = role["AssumeRolePolicyDocument"]["Statement"]
    require(len(trust_statements) == 1, "GitHubApplyRole: expected one trust statement")
    trust = trust_statements[0]
    require(trust.get("Action") == "sts:AssumeRoleWithWebIdentity", "GitHubApplyRole: only web-identity assumption is allowed")
    require(
        trust.get("Condition", {}).get("StringEquals")
        == {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub": EXPECTED_SUBJECT,
        },
        "GitHubApplyRole: audience and direct-main subject must be exact",
    )

    forbidden_identity_types = {"AWS::IAM::User", "AWS::IAM::AccessKey"}
    actual_types = {item["Type"] for item in template["Resources"].values()}
    require(not actual_types & forbidden_identity_types, "bootstrap: IAM users and access keys are forbidden")
    require(sum(item["Type"] == "AWS::IAM::Role" for item in template["Resources"].values()) == 1, "bootstrap: exactly one role is allowed")

    bucket_resource = resource(template, "TerraformStateBucket", "AWS::S3::Bucket")
    bucket = bucket_resource["Properties"]
    require(bucket_resource.get("DeletionPolicy") == "Retain", "TerraformStateBucket: deletion retention required")
    require(bucket_resource.get("UpdateReplacePolicy") == "Retain", "TerraformStateBucket: replacement retention required")
    require(bucket.get("BucketName") == EXPECTED_BUCKET, "TerraformStateBucket: stable bucket name changed")
    require(bucket.get("VersioningConfiguration") == {"Status": "Enabled"}, "TerraformStateBucket: versioning must be enabled")
    require("LifecycleConfiguration" not in bucket, "TerraformStateBucket: state versions must not expire")
    require(
        bucket.get("PublicAccessBlockConfiguration")
        == {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True,
        },
        "TerraformStateBucket: full public-access block required",
    )
    encryption = bucket.get("BucketEncryption", {}).get("ServerSideEncryptionConfiguration", [])
    require(encryption == [{"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}], "TerraformStateBucket: SSE-S3 required")
    ownership = bucket.get("OwnershipControls", {}).get("Rules", [])
    require(ownership == [{"ObjectOwnership": "BucketOwnerEnforced"}], "TerraformStateBucket: bucket-owner enforcement required")

    policy_resource = resource(template, "TerraformStateBucketPolicy", "AWS::S3::BucketPolicy")
    require(policy_resource.get("DeletionPolicy") == "Retain" and policy_resource.get("UpdateReplacePolicy") == "Retain", "TerraformStateBucketPolicy: retention must follow retained bucket")
    policy = policy_resource["Properties"]["PolicyDocument"]
    tls = statement(policy, "DenyInsecureTransport")
    require(tls.get("Effect") == "Deny" and tls.get("Condition") == {"Bool": {"aws:SecureTransport": "false"}}, "DenyInsecureTransport: exact non-TLS denial required")
    location = statement(policy, "AllowApplyRoleBucketLocation")
    require(location.get("Action") == "s3:GetBucketLocation", "bucket location: exact action required")
    require("Condition" not in location, "bucket location: s3:prefix does not apply to GetBucketLocation")
    bucket_list = statement(policy, "AllowApplyRoleBucketList")
    require(bucket_list.get("Action") == "s3:ListBucket", "bucket list: exact action required")
    require(
        bucket_list.get("Condition")
        == {"StringLike": {"s3:prefix": ["main/terraform.tfstate", "main/terraform.tfstate.tflock"]}},
        "bucket list: fixed state-key prefixes required",
    )
    state_access = statement(policy, "AllowApplyRoleStateReadWrite")
    require(set(state_access.get("Action", [])) == {"s3:GetObject", "s3:PutObject"}, "state object: normal access must not include deletion")
    require(state_access.get("Resource") == {"Fn::Sub": "${TerraformStateBucket.Arn}/main/terraform.tfstate"}, "state object: fixed key required")
    lock_access = statement(policy, "AllowApplyRoleNativeLock")
    require(set(lock_access.get("Action", [])) == {"s3:DeleteObject", "s3:GetObject", "s3:PutObject"}, "native lock: read/write/delete required")
    require(lock_access.get("Resource") == {"Fn::Sub": "${TerraformStateBucket.Arn}/main/terraform.tfstate.tflock"}, "native lock: adjacent fixed key required")

    topic_policy = resource(template, "BudgetNotificationsTopicPolicy", "AWS::SNS::TopicPolicy")["Properties"]["PolicyDocument"]
    budgets = statement(topic_policy, "AllowBudgetsPublish")
    require(budgets.get("Principal") == {"Service": "budgets.amazonaws.com"}, "budget topic: only AWS Budgets service may publish")
    require(budgets.get("Action") == "sns:Publish", "budget topic: least-sufficient publish action required")
    subscription = resource(template, "BudgetNotificationSubscription", "AWS::SNS::Subscription")["Properties"]
    require(subscription.get("Protocol") == "email", "budget subscription: email protocol required")
    require(subscription.get("Endpoint") == {"Ref": "BudgetNotificationEmail"}, "budget subscription: endpoint must be private parameter")

    outputs = template.get("Outputs", {})
    require(set(outputs) == {"AccountId", "ApplyRoleArn", "StateBucketName", "BudgetTopicArn"}, "bootstrap outputs: safe named interface changed")
    for name, output in outputs.items():
        require({"Ref": "BudgetNotificationEmail"} not in list(walk(output)), f"bootstrap output {name}: private email reference forbidden")

    workload_types = {
        "AWS::Route53::HostedZone",
        "AWS::CloudFront::Distribution",
        "AWS::CertificateManager::Certificate",
        "AWS::Budgets::Budget",
    }
    require(not actual_types & workload_types, "bootstrap: website workload resource crossed ownership boundary")


def terraform_resources(source: str) -> list[tuple[str, str]]:
    return re.findall(r'^resource\s+"([^"]+)"\s+"([^"]+)"', source, flags=re.MULTILINE)


def check_terraform() -> None:
    roots = sorted({path.parent for path in (ROOT / "infra/aws/terraform").rglob("*.tf")})
    require(roots == [TERRAFORM], "terraform: expected exactly one root under infra/aws/terraform/main")

    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(TERRAFORM.glob("*.tf")))
    resources = terraform_resources(source)
    types = [kind for kind, _ in resources]
    forbidden_types = {
        "aws_iam_openid_connect_provider",
        "aws_iam_role",
        "aws_iam_user",
        "aws_iam_access_key",
        "aws_sns_topic",
        "aws_sns_topic_policy",
        "aws_sns_topic_subscription",
        "aws_dynamodb_table",
        "aws_kms_key",
    }
    require(not set(types) & forbidden_types, "terraform: bootstrap identity/state/topic or forbidden lock/KMS owner declared")
    require(types.count("aws_route53_zone") == 1, "terraform: expected one hosted zone")
    require(types.count("aws_cloudfront_distribution") == 1, "terraform: expected one CloudFront distribution")
    require(types.count("aws_s3_bucket") == 1, "terraform: expected one content bucket")
    require(types.count("aws_budgets_budget") == 1, "terraform: expected one actual-cost budget")
    require("prevent_destroy = true" in source, "hosted zone: prevent_destroy required")
    require('custom_domain_enabled = false' in (TERRAFORM / "terraform.tfvars").read_text(encoding="utf-8"), "domain phase: committed initial value must be false")

    backend = (TERRAFORM / "backend.tf").read_text(encoding="utf-8")
    for required in (
        f'bucket       = "{EXPECTED_BUCKET}"',
        f'key          = "{EXPECTED_STATE_KEY}"',
        'region       = "us-east-1"',
        'use_lockfile = true',
    ):
        require(required in backend, f"terraform backend: missing {required.strip()}")
    require("dynamodb" not in backend.lower(), "terraform backend: DynamoDB locking is forbidden")

    versions = (TERRAFORM / "versions.tf").read_text(encoding="utf-8")
    pinned_cli = (ROOT / ".terraform-version").read_text(encoding="utf-8").strip()
    require(f'required_version = "= {pinned_cli}"' in versions, "terraform: CLI pin must match .terraform-version")
    provider_match = re.search(
        r'source\s*=\s*"hashicorp/aws"\s+version\s*=\s*"= ([0-9]+\.[0-9]+\.[0-9]+)"',
        versions,
    )
    require(provider_match is not None, "terraform: AWS provider must be exactly pinned")
    lock = TERRAFORM / ".terraform.lock.hcl"
    require(lock.is_file(), "terraform: committed provider lock file is required")
    lock_text = lock.read_text(encoding="utf-8")
    require(provider_match.group(1) in lock_text and "hashicorp/aws" in lock_text, "terraform lock: pinned AWS provider missing")
    require(lock_text.count('"zh:') >= 2 and '"h1:' in lock_text, "terraform lock: multi-platform checksums required")

    storage = (TERRAFORM / "storage.tf").read_text(encoding="utf-8")
    for required in (
        'object_ownership = "BucketOwnerEnforced"',
        "block_public_acls       = true",
        "block_public_policy     = true",
        "ignore_public_acls      = true",
        "restrict_public_buckets = true",
        'sse_algorithm = "AES256"',
        'status = "Enabled"',
        'identifiers = ["cloudfront.amazonaws.com"]',
        'variable = "AWS:SourceArn"',
        "values   = [aws_cloudfront_distribution.site.arn]",
    ):
        require(required in storage, f"content origin: missing safe boundary {required}")
    require("lifecycle_rule" not in storage and "expiration" not in storage, "content origin: versions must not expire")

    cloudfront = (TERRAFORM / "cloudfront.tf").read_text(encoding="utf-8")
    for required in (
        'default_root_object = "index.html"',
        'viewer_protocol_policy = "redirect-to-https"',
        "compress               = true",
        'response_page_path    = "/404.html"',
        "cloudfront_default_certificate = !var.custom_domain_enabled",
    ):
        require(required in cloudfront, f"CloudFront: missing behavior {required}")
    require(cloudfront.count("custom_error_response {") == 2, "CloudFront: exact 403 and 404 mappings required")

    budget = (TERRAFORM / "budget.tf").read_text(encoding="utf-8")
    for required in (
        'budget_type  = "COST"',
        'limit_amount = "10"',
        'limit_unit   = "USD"',
        'time_unit    = "MONTHLY"',
        'notification_type         = "ACTUAL"',
        "subscriber_sns_topic_arns = [data.aws_sns_topic.budget_notifications.arn]",
    ):
        require(required in budget, f"budget: missing actual-cost notification boundary {required}")

    outputs = set(re.findall(r'^output\s+"([^"]+)"', source, flags=re.MULTILINE))
    require(
        outputs
        == {
            "content_bucket_name",
            "cloudfront_distribution_id",
            "cloudfront_staging_hostname",
            "hosted_zone_id",
            "hosted_zone_name_servers",
            "custom_domain_enabled",
        },
        "terraform outputs: safe named interface changed",
    )

    edge = (TERRAFORM / "edge_redirects.js").read_text(encoding="utf-8")
    require(edge.count("request.uri ===") == 3, "edge function: routing must remain exactly three comparisons")
    for old, new in {
        "/resume/": "/about.html",
        "/programming/": "/projects.html",
        "/design/": "/projects.html",
    }.items():
        require(f'"{old}"' in edge and f'"{new}"' in edge, f"edge function: exact redirect {old} -> {new} missing")
    require("statusCode: 308" in edge, "edge function: permanent 308 required")


def tracked_paths() -> list[Path]:
    """Read ordinary Git index v2/v3 entries without requiring a Git executable."""
    dot_git = ROOT / ".git"
    if dot_git.is_file():
        pointer = dot_git.read_text(encoding="utf-8").strip()
        require(pointer.startswith("gitdir: "), "tracked material: malformed .git worktree pointer")
        git_dir = (ROOT / pointer.removeprefix("gitdir: ")).resolve()
    else:
        git_dir = dot_git
    data = (git_dir / "index").read_bytes()
    require(len(data) >= 12, "tracked material: Git index is truncated")
    signature, version, count = struct.unpack_from(">4sII", data)
    require(signature == b"DIRC", "tracked material: Git index signature is invalid")
    require(version in {2, 3}, f"tracked material: unsupported Git index version {version}; expected v2 or v3")
    offset = 12
    paths: list[Path] = []
    for entry_number in range(count):
        entry_start = offset
        require(offset + 62 <= len(data), f"tracked material: Git index entry {entry_number} is truncated")
        flags = struct.unpack_from(">H", data, offset + 60)[0]
        offset += 62
        if flags & 0x4000:
            require(offset + 2 <= len(data), f"tracked material: Git index entry {entry_number} flags are truncated")
            offset += 2
        path_end = data.find(b"\0", offset)
        require(path_end >= 0, f"tracked material: Git index entry {entry_number} has no path terminator")
        paths.append(Path(data[offset:path_end].decode("utf-8", errors="surrogateescape")))
        entry_size = path_end + 1 - entry_start
        offset = entry_start + ((entry_size + 7) // 8) * 8
    return paths


def check_tracked_material() -> None:
    paths = tracked_paths()
    forbidden_parts = {".terraform", ".aws-runner"}
    for path in paths:
        name = path.name
        require(not forbidden_parts.intersection(path.parts), f"tracked material: forbidden generated path {path}")
        forbidden_terraform_material = (
            name.endswith((".tfstate", ".tfplan", ".plan", ".plan.json", ".tflock", ".tfdiag"))
            or ".tfstate." in name
        )
        require(not forbidden_terraform_material, f"tracked material: forbidden Terraform material {path}")
        require(not (path.suffix.lower() == ".csv" and "dns" in path.name.lower()), f"tracked material: private DNS export forbidden: {path}")

    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for required in (".tools/", "**/.terraform/", "*.tfstate", "*.tfplan", "*.plan.json", "*.tflock", "*.tfdiag"):
        require(required in ignore, f"tracked material: .gitignore must exclude {required}")


def main() -> int:
    try:
        check_bootstrap()
        check_terraform()
        check_tracked_material()
    except (CheckFailure, json.JSONDecodeError, OSError, struct.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Infrastructure structural checks passed: bootstrap ownership, Terraform boundary, pins, and tracked-material safety.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
