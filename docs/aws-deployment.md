# AWS deployment and inspection workflow

`.github/workflows/aws.yml` is the repository's only routine AWS credential
executor. A push to `main` resolves to `deploy`; a manual run on `main` accepts
only `deploy`, `plan`, `refresh-plan`, or `site-status`. One constant
non-cancelling maximal concurrency queue serializes every operation, and the
credentialed job has a 120-minute ceiling. The maximal queue retains pending
runs up to GitHub's current service limit; overflow is a visible non-started
cancellation, never a partially executed mutation.

## Bootstrap gate and source identity

Every run first checks out the event's exact commit in a read-only job, rejects
any ref except `refs/heads/main`, resolves the closed operation grammar, and
runs the site, infrastructure, workflow, failure-boundary, and renderer tests.
This job has no OIDC permission.

The separate job carrying `id-token: write` is admitted only if validation
succeeds and repository variable `AWS_BOOTSTRAPPED` is the literal `true`.
Absent, false, or any other value leaves the source checks green while the AWS
job is skipped. The variable is a bootstrap readiness gate, not a secret or a
caller input.

The AWS job installs digest-pinned Terraform 1.15.8 and AWS CLI 2.36.21 before
requesting credentials, then exchanges the exact-main OIDC identity for the
bootstrap-owned role. Before contacting the Terraform backend it checks account
`241077340022`, region `us-east-1`, the exact checkout, and the permanent
CloudFormation foundation: deployed-template equality with that checkout,
complete owned resources and safe outputs, exact role/OIDC trust and policy,
state-bucket controls and namespace, and the confirmed budget subscription.
Editing the bootstrap template therefore intentionally makes every operation
fail closed until the retained stack has been updated to those reviewed bytes.
Raw command responses are captured in mode-0600 runner files and are never
logged or uploaded.

## Fixed operations

- `deploy` makes one saved plan and applies that same private file. After a
  successful apply it uploads the complete `site/` tree without deletion,
  reconciles absent keys in a second pass, creates exactly one `/*`
  invalidation, waits within the job, and runs fixed content, redirect, 404,
  and direct-S3-denial probes.
- `plan` makes one ordinary saved plan for a bounded aggregate action summary.
  It never applies or publishes.
- `refresh-plan` makes one `-refresh-only` plan and reports actions from
  Terraform's `resource_drift` collection rather than the ordinary desired-state
  `resource_changes` collection. It never invokes any apply
  form, updates state, or publishes.
- `site-status` first performs the permanent foundation checks above. Before
  the initial workload exists, an empty fixed state namespace is the successful
  `foundation-ready` result and the operation stops without backend
  initialization. Once state exists, it reads the fixed named Terraform
  outputs, CloudFront metadata, origin public-access controls, and the fixed
  public probes. It never plans, applies, syncs, deletes, invalidates, or
  changes cloud configuration.

The public result contains exactly the source SHA, expected account and region,
aggregate resource-action counts, the validated public CloudFront staging
hostname and four Route 53 authoritative nameservers when the workload outputs
are available, one closed diagnostic category, and one closed final status. It
is written to the job summary and repeated as one machine-readable log line so
API-only operators can recover the same bounded result. It is newly constructed
from those primitives; no raw plan, address, private value, response body,
diagnostic, or provider message is forwarded. A malformed renderer input
becomes one fixed `renderer-failure`.
The category enum is `none`, `validation-failed`, `identity-failed`,
`foundation-failed`, `foundation-ready`, `initialization-failed`,
`plan-failed`, `apply-uncertain`, `publication-failed`,
`verification-failed`, `status-failed`, or `renderer-failure`. Final status
is exactly `success`, `safe-failure`, or `inspection-required`.

## Dispatch and durable observation

Record the exact local commit before publication. A push of that commit to
`main` automatically selects `deploy`. To request a read-only operation:

```sh
gh workflow run aws.yml --ref main -f operation=site-status
gh workflow run aws.yml --ref main -f operation=plan
gh workflow run aws.yml --ref main -f operation=refresh-plan
```

Do not supply a tag, pull-request ref, alternate branch, path, command, region,
account, or probe target. Find the run by exact commit and retain its GitHub run
ID, SHA, status, and conclusion:

```sh
gh run list --workflow aws.yml --commit "$source_sha" --json databaseId,headSha,status,conclusion,event
gh run watch "$run_id" --exit-status
```

If a local watcher stops, query that same run ID or exact SHA; do not start a
replacement run merely because observation was interrupted.

## Failure custody and recovery

A proven plan failure before apply starts is `safe-failure`: no publication or
invalidation follows. Once apply might have started, any non-success or missing
verified terminal summary is `inspection-required`. Publication or
verification failures also require inspection because remote content may be
partial or unverified. Run `site-status` and, when infrastructure reconciliation
is needed, `plan` or `refresh-plan`; a partially applied workload whose state
exists but whose named outputs are incomplete reports `status-failed`, making
`plan` the next read-only reconciliation instrument. Inspect the exact prior
GitHub run before choosing another deliberate action. Never blindly retry or
infer success from an absent summary.

An ordinary content regression is reverted in source and deployed through the
same path. State-version recovery follows the diagnosis-first private procedure
in `docs/aws-infrastructure.md`; it is not a workflow mode. Loss of repository,
OIDC trust, the state foundation, account authority, or registrar authority is
an owner-recovery event. No automatic infrastructure/content rollback or
durable diagnostic ledger exists.

Temporary plan bytes, plan JSON, Terraform/AWS output, response bodies, and
provider diagnostics live only in one restrictive runner directory. Reachable
success and failure paths delete it; hard cancellation falls back to hosted
runner teardown. Never enable shell tracing, GitHub debug logging, artifact
upload, or a raw-output fallback for diagnosis.

## Bounds and deferred live evidence

At most one run executes. Deploy performs one plan, at most one apply, an
`O(source files + existing origin keys)` two-pass reconciliation, one
invalidation, and a fixed probe set. Plan modes are each one
`O(terraform resource count)` plan; `site-status` has a fixed read/probe set.
Verification uses at most 20 attempts separated by 15 seconds within the job.
Ephemeral storage is bounded to one plan, its JSON, and one run's captured
responses plus one fixed Terraform/AWS CLI tool installation; hosted-runner
teardown returns all of it to zero. There is no schedule, poller, artifact
history, project outcome store, or release inventory.

This source task proves only credential-free control behavior. Task 05 observes
the bootstrap-gated public `main` run. Task 07 proves real OIDC, all four modes,
no-mutation inspection, state/content versions, staging failures and source
revert. Task 09 proves the enabled custom-domain phase and apex/`www` behavior.
