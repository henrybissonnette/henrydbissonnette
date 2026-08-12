from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_aws_operation import CommandFailure, CommandRunner, OperationExecutor  # noqa: E402
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
            ["source_sha", "account", "region", "action_counts", "category", "status"],
        )
        self.assertEqual(summary["action_counts"]["replace"], 1)
        self.assertEqual(summary["action_counts"]["update"], 1)
        encoded = json.dumps(summary)
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn("address", encoded)
        self.assertNotIn("password", encoded)

    def test_malformed_input_returns_one_fixed_safe_failure(self) -> None:
        first = build_summary("not-a-sha", "anything", "success", {"raw": "SECRET"})
        second = build_summary("e" * 40, "none", "success", {"resource_changes": "hostile"})
        self.assertEqual(first, second)
        self.assertEqual(first["category"], "renderer-failure")
        self.assertEqual(first["status"], "safe-failure")
        self.assertNotIn("SECRET", json.dumps(first))


class FakeRunner(CommandRunner):
    def __init__(self, workspace: Path, fail_at: str | None = None, unexpected_at: str | None = None):
        super().__init__(workspace)
        self.fail_at = fail_at
        self.unexpected_at = unexpected_at
        self.commands: list[list[str]] = []

    def run(self, label: str, command: list[str], allowed=(0,)) -> Path:
        self.trace.append(label)
        self.commands.append(command)
        capture = self.workspace / f"{len(self.trace):02d}-{label}.private"
        values = {
            "terraform-version": "Terraform v1.15.8\n",
            "aws-version": "aws-cli/2.36.21 Python/3.13 Linux/x86_64\n",
            "sts-identity": json.dumps({"Account": "241077340022", "Arn": "SENTINEL_PRIVATE_ARN"}),
            "terraform-show-plan": json.dumps(
                {
                    "resource_changes": [
                        {
                            "address": "SENTINEL_PRIVATE_ADDRESS",
                            "change": {"actions": ["update"], "before": {"secret": "SENTINEL"}},
                        }
                    ]
                }
            ),
            "terraform-output-content_bucket_name": "henry-content-bucket\n",
            "terraform-output-cloudfront_distribution_id": "EDIST123\n",
            "terraform-output-cloudfront_staging_hostname": "d123.cloudfront.net\n",
            "cloudfront-invalidate": json.dumps({"Invalidation": {"Id": "INV123"}}),
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
    ) -> tuple[OperationExecutor, int, dict, FakeRunner]:
        outer = tempfile.TemporaryDirectory()
        self.addCleanup(outer.cleanup)
        root = Path(outer.name)
        summary = root / "summary.md"
        created: list[FakeRunner] = []

        def factory(workspace: Path) -> FakeRunner:
            runner = FakeRunner(workspace, fail_at, unexpected_at)
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
        with patch.dict(os.environ, environment, clear=False):
            executor = OperationExecutor(operation, factory, verifier)
            result = executor.execute()
        encoded = re.search(r"`(\{.*\})`", summary.read_text(encoding="utf-8")).group(1)
        return executor, result, json.loads(encoded), created[0]

    def test_all_operation_traces_have_fixed_authority(self) -> None:
        deploy, result, summary, runner = self.run_operation("deploy")
        self.assertEqual(result, 0)
        self.assertEqual(summary["status"], "success")
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
        plan_command = runner.commands[runner.trace.index("terraform-plan")]
        apply_command = runner.commands[runner.trace.index("terraform-apply")]
        plan_path = next(argument.removeprefix("-out=") for argument in plan_command if argument.startswith("-out="))
        self.assertEqual(apply_command[-1], plan_path)
        upload_command = runner.commands[runner.trace.index("site-upload")]
        reconcile_command = runner.commands[runner.trace.index("site-reconcile")]
        # aws s3 sync deletes only when asked; the CLI has no --no-delete option.
        self.assertNotIn("--delete", upload_command)
        self.assertNotIn("--no-delete", upload_command)
        self.assertIn("--delete", reconcile_command)
        invalidation_command = runner.commands[runner.trace.index("cloudfront-invalidate")]
        self.assertEqual(invalidation_command[invalidation_command.index("--paths") + 1], "/*")
        self.assertTrue(all(mode == 0o600 for mode in deploy.capture_modes))
        self.assertFalse(deploy.last_workspace.exists())

        plan, result, _, _ = self.run_operation("plan")
        self.assertEqual(result, 0)
        self.assertIn("terraform-plan", plan.trace)
        self.assertNotIn("terraform-apply", plan.trace)
        self.assertNotIn("site-upload", plan.trace)

        refresh, result, _, refresh_runner = self.run_operation("refresh-plan")
        self.assertEqual(result, 0)
        plan_command = refresh_runner.commands[refresh_runner.trace.index("terraform-plan")]
        self.assertIn("-refresh-only", plan_command)
        self.assertFalse(any("apply" in command for command in refresh_runner.commands))

        status, result, _, _ = self.run_operation("site-status")
        self.assertEqual(result, 0)
        self.assertNotIn("terraform-plan", status.trace)
        self.assertNotIn("terraform-apply", status.trace)
        self.assertIn("status-cloudfront", status.trace)
        self.assertIn("status-origin-access", status.trace)

    def test_failures_stop_at_each_mutation_boundary_and_cleanup(self) -> None:
        cases = (
            ("sts-identity", "safe-failure", ("terraform-plan", "terraform-apply", "site-upload")),
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
