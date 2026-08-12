# AWS infrastructure operating contract

This repository has one permanent AWS foundation and one website workload.
They deliberately have different declarative owners and must not adopt each
other's resources.

## Fixed identities

| Item | Value |
| --- | --- |
| AWS account | `241077340022` |
| Primary and certificate region | `us-east-1` |
| Bootstrap stack | `henrybissonnette-bootstrap` |
| GitHub apply role | `henrybissonnette-github-apply` (7,200-second maximum session) |
| Terraform state bucket | `henrybissonnette-terraform-state-241077340022` |
| Terraform state key | `main/terraform.tfstate` |
| Terraform lock object | `main/terraform.tfstate.tflock` |
| Terraform root | `infra/aws/terraform/main/` |
| Initial domain phase | `custom_domain_enabled = false` |

CloudFormation under `infra/aws/bootstrap/` exclusively owns the GitHub OIDC
provider, broad in-account apply role, retained state bucket and policy, and
the budget notification topic, policy, and email subscription. Update those
resources by updating the permanent template and then updating that named
stack.

Terraform's single `infra/aws/terraform/main/` root exclusively owns the
Route 53 zone and explicit public records, private content bucket, OAC,
CloudFront distribution and function, conditional ACM and aliases, and the
actual-cost budget. Update them through the one serialized Terraform workflow.
There is no second root, workspace, DynamoDB lock, or hand-managed bridge.

## Bootstrap and verification

The first bootstrap is a finite human-authorized action. Use an exact checkout
of the public repository, calculate and record the SHA-256 digest of
`infra/aws/bootstrap/template.json`, and upload that exact file in the AWS
CloudFormation console as stack `henrybissonnette-bootstrap`. Enter the budget
notification email only in the `NoEcho` parameter. Do not paste it into source,
logs, messages, stack metadata, tags, or outputs.

Before allowing Terraform to use the foundation, verify in this order:

1. the deployed template digest matches the reviewed local template;
2. the stack account is `241077340022` and region is `us-east-1`;
3. the stack outputs name the expected role, state bucket, and topic;
4. the state bucket is private, encrypted, bucket-owner-enforced, versioned,
   retained, and has its complete public-access block;
5. the OIDC provider and role trust use the exact audience and main-branch
   subject in the template; and
6. the private email subscription has been confirmed.

The bootstrap outputs are non-secret identifiers only: `AccountId`,
`ApplyRoleArn`, `StateBucketName`, and `BudgetTopicArn`.
The email is intentionally not an output. If the stable bucket name is not
available, stop before the first state write and revise the template, backend,
and this contract together. A failed bootstrap stack may be deleted only
before the first state write. Once state has been used, foundation trust or
bucket recovery is an owner-authority incident, not stack cleanup.

## Two deployment increments

Keep `custom_domain_enabled = false` for the staging increment. Terraform then
creates the hosted zone, private versioned origin, OAC, exact redirect
function, default-certificate CloudFront distribution, and budget. Name.com
remains authoritative, so neither ACM validation nor public aliases can block
staging.

After staging is verified, add every reviewed surviving public DNS record from
the private name.com export as an explicit `aws_route53_record` beside the
documented extension point in `dns.tf`. Do not commit or import the export and
do not introduce a generic record importer. Delegate at the registrar and wait
until the Route 53 name servers are observably authoritative.

Only then change `custom_domain_enabled` to `true`. The second increment adds
the apex/`www` ACM certificate and DNS validation, swaps CloudFront to that
certificate, and creates both aliases. Both hosts serve the same content; no
`www` redirect or wildcard certificate is intended.

Safe Terraform outputs are individually named: `custom_domain_enabled`,
`content_bucket_name`, `cloudfront_distribution_id`,
`cloudfront_staging_hostname`, `hosted_zone_id`, `hosted_zone_name_servers`,
and no others. Treat state as confidential even though these specific values
are safe. Never print or retain raw state, saved plans, plan JSON, provider
debug output, credentials, tokens, the private DNS export, or the subscription
email. Do not use commands that dump all outputs as an ordinary diagnostic.

## State recovery

Recovery is diagnosis-first and private. After confirming state loss or
corruption, an authorized operator may list versions for the exact
`main/terraform.tfstate` object, select a known prior version explicitly, and
copy that exact version back to the current key. Then run a private refresh and
plan and inspect the proposed changes before considering any apply. Never
display or download state contents into source, messages, process state, or CI
artifacts. This is not an automatic rollback, scheduled drill, state migration
facility, or permission to guess a version.

## Reproducible local checks and deferred evidence

Run `scripts/check_infrastructure.sh` from the repository's declared Python
3.11 workbench. Python installs the exact Terraform and Node releases into
ignored `.tools/` after checking hard-coded upstream SHA-256 digests; the
entrypoint does not require ambient `git`, `node`, `curl`, or `unzip` commands.
It then performs formatting and lockfile checks, initializes without the real
backend, validates the configuration, runs native mocked plans for both domain
phases, executes focused ownership/security assertions, and executes the real
edge-function source in pinned Node. A fresh cache needs network access for the
two pinned tools and provider, but no AWS credentials, and the check never
contacts the real backend. `.terraform-version` and `.node-version` are the
tool-version interface; archive digests for both supported Linux architectures
are part of `scripts/install_tool.py`. This cold authoring cache grows with the
number of distinct tool-version pins used in one worktree: one executable per
Terraform or Node version. It is ignored, is never a runtime dependency, and
may be deleted as a unit; the next check reconstructs only the two current
pins.

These local checks do not claim live AWS facts. Task 06 must witness the exact
deployed template, bucket controls, SNS confirmation, and real main-branch OIDC
assumption. Task 07 must witness real provider plan/apply, direct-S3 denial,
staging behavior, DNS review/delegation, and state-version recovery. Task 09
must witness the custom-domain graph and both public hosts.

The serialized execution, inspection, public-summary, and failure-custody
contract is documented in [`aws-deployment.md`](aws-deployment.md).

## Bounds and exclusions

The viewer function performs three constant exact-path comparisons per
request. Terraform work scales with the resource count in this one root, and a
single native S3 lock object serializes its one state key. Content versions
grow with deploy count times changed site bytes; state versions grow with
state writes times state size. Both stores intentionally retain noncurrent
versions at this initial scale. Material observed version growth is the trigger
for a separately reviewed lifecycle policy.

There is no recurring inventory scan, drift poll, project-owned production
cache, VPC, database, queue, runtime, second account, legacy import, App Engine
migration, DNSSEC configuration, automatic shutdown, generalized redirect
engine, or future-workload scaffold in this boundary.
