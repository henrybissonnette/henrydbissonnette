# AWS pre-work for henrybissonnette.com

Status: member account created; tracker task `06_authorize_bootstrap_foundation`
records the one-time bootstrap as completed through the project-owned AWS CLI
path. Account guardrails and registrar readiness remain to be completed.

This is the authoritative guide to the remaining human-owned preparation. It
does not authorize manual creation of website infrastructure. After the finite
account, bootstrap, product, and registrar decisions below, GitHub Actions is
the only routine AWS credential executor and routine publication is agent-owned.

## Settled operating model

- Domain: `henrybissonnette.com`
- Public repository: `henrybissonnette/henrydbissonnette`
- AWS member account: `henrybissonnette_personal` (`241077340022`), created
  2026-08-08 in the existing AWS Organization
- Initial region: `us-east-1` (including the CloudFront certificate)
- Registrar: name.com

Remote `master` remains untouched as the legacy archive at commit
`650b89b7cc137d59dcc67679ee08707f9c3eb1a7`. The new Womb lineage is published
as remote `main` by a normal, non-force push. The unrelated histories are not
merged, and old source is not copied into a `legacy/` directory.

GitHub Actions assumes a short-lived AWS session through repository- and
branch-scoped OpenID Connect (OIDC). There is no supported local AWS session,
IAM-user access key, root key, or GitHub AWS secret. Agents author and inspect
bounded workflow operations; humans do not broker recurring AWS sessions.

## Remaining readiness actions

### 1. Confirm account access and organization guardrails

From the existing AWS Organization and IAM Identity Center:

1. Confirm Hank's existing user or administrative group has the normal
   administrative permission set for `henrybissonnette_personal` only.
2. Open the account from the AWS access portal and verify account ID
   `241077340022` in the console header.
3. From the Organizations management account, enable centralized root access,
   including root credentials management and privileged root actions. Leave
   delegated administrator unset unless organization security separately
   decides otherwise. Verify the member account has no root credentials; do
   not recover a password, add root MFA, or create root access keys merely to
   make credentials exist.
4. Note the account's existing parent. Do not create an organizational unit
   solely for this site.
5. Inspect attached service control policy names. If only `FullAWSAccess` is
   attached, record that fact. If another policy may deny CloudFormation, IAM,
   STS, S3, Route 53, ACM, CloudFront, or AWS Budgets, report its name only; do
   not weaken or detach it speculatively.

The account is the durable blast-radius boundary. Initial use of `us-east-1`
does not constrain future projects to one region, static hosting, or a narrow
set of AWS services.

### 2. Confirm registrar readiness without changing DNS

In name.com:

1. Verify account access and enable authenticator-based two-step verification.
   Store recovery codes in a password manager, never in source or project
   communication.
2. Confirm `henrybissonnette.com` is active, automatic renewal is enabled, and
   the private payment profile is current. Do not report payment details.
3. Export the current DNS zone as CSV and retain it privately for the later
   Route 53 parity check. Do not commit the export or paste complete TXT values
   into conversation, logs, CI artifacts, or process state.
4. Confirm the current name.com nameservers without changing them. Record only
   whether DNS contains mail or other records that must survive cutover.
5. Record DNSSEC as enabled, disabled, or unknown. Do not add or remove a DS
   record during readiness.

Nameserver delegation happens only after the Terraform-created Route 53 zone,
all retained records, certificates, staging site, and rollback evidence pass
their later checks.

### 3. Launch the exact bootstrap template once

Status: tracker task `06_authorize_bootstrap_foundation` records stack
`henrybissonnette-bootstrap` as created and termination-protected, so this is
no longer an outstanding action. Check the current stack status before
performing any step below; the console procedure is retained only as the
relaunch and recovery reference.

After the CloudFormation template under `infra/aws/bootstrap/` is committed and
published on remote `main`, the project will provide its exact commit and
SHA-256 digest. The human bootstrap action is:

1. Download the template from that exact commit.
2. Independently compute SHA-256 and compare it with the recorded digest.
   Stop on any mismatch.
3. Enter account `241077340022` through federated console access and open
   CloudFormation in `us-east-1`.
4. Choose **Create stack** and **Upload a template file**, then upload the
   digest-verified local file. Do not use a raw-GitHub quick-create URL.
5. Supply the private budget-notification email to the template's `NoEcho`
   parameter, acknowledge named IAM resource creation, and create the named
   bootstrap stack.
6. Confirm the subscription from the private mailbox. Do not publish the
   address or confirmation link.

The committed template owns only the circular trust and state foundation:
GitHub OIDC provider, GitHub apply role, retained private Terraform-state
bucket, and budget-notification topic/subscription. It does not store the email
in source or expose it as an output. There is no SSM bootstrap alternative or
staging bucket that must be created first.

After launch, agents compare the deployed stack template and safe outputs to
the exact source/digest, verify the state-bucket controls and OIDC assumption
from remote `main`, and only then enable the deployment workflow. If first
creation rolls back before any Terraform state exists, agents diagnose the
events before asking for one corrected relaunch.

## Do not create these resources manually

Apart from uploading the exact committed bootstrap template, do not manually
create or alter:

- Terraform state or website S3 buckets;
- GitHub OIDC providers, deployment roles, IAM users, or access keys;
- Route 53 hosted zones or DNS records;
- ACM certificates or CloudFront distributions;
- budgets, alarms, application services, databases, or project infrastructure;
- repository secrets containing AWS credentials; or
- Terraform plans or state outside their private, workflow-owned boundary.

Terraform owns website resources. GitHub Actions is the routine plan, apply,
publish, and bounded-inspection path. A Terraform replacement is not, by
itself, a human action. Never paste raw plans, state, secret-bearing workflow
output, AWS tokens, or session credentials into source or ordinary agent-visible
state.

## Safe completion report

Report only these bounded, non-secret facts:

- member account access: verified / blocked;
- account name and ID: `henrybissonnette_personal` / `241077340022`;
- existing account parent name;
- centralized root access: enabled / disabled / unknown;
- blocking service control policy names, if any;
- name.com access and two-step verification: verified / blocked;
- DNSSEC: enabled / disabled / unknown;
- current DNS has mail or other records to preserve: yes / no / unknown;
- bootstrap source commit and SHA-256 match: yes / no / not attempted;
- bootstrap stack creation and notification subscription: complete / blocked /
  not attempted.

Do not send passwords, access keys, session tokens, recovery codes, account
owner or notification mailboxes, payment details, the private DNS export,
complete TXT values, CloudFormation confirmation links, raw plans, or state.

## Later human authority

Once readiness and bootstrap are verified, the only planned human actions are:

1. approve or revise the exact proposed public copy, contact identity, and
   assets on the real staging site;
2. confirm the already-settled retirement disposition if staged evidence
   uncovers a genuinely valuable legacy behavior that was missed; and
3. change the registrar nameservers only after the replacement zone and staged
   product pass acceptance, retaining the private DNS export until the rollback
   window closes.

Account or trust recovery may also require owner authority after an actual
failure. Routine infrastructure selection, creation, deployment, inspection,
verification, and static-content publication remain autonomous.
