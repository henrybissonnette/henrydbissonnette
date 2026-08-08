# AWS pre-work for henrybissonnette.com

Status: member account created; root centralization, federated access, and
registrar readiness remain

This runbook contains only the human-owned work needed before the project can
bootstrap its AWS infrastructure. It intentionally stops before creating any
workload resources. The project will define those resources in source and
manage them through Terraform.

## Known inputs

- Domain: `henrybissonnette.com`
- Source repository: `henrybissonnette/henrydbissonnette`
- Registrar: name.com
- AWS member account: `henrybissonnette_personal` (`241077340022`), created
  2026-08-08 in the existing AWS Organization
- Primary deployment region: `us-east-1`
- Budget notification address: supplied out of band; do not commit it

The region is a default for the initial workload, not a requirement that every
future project use it. CloudFront certificates must be created in `us-east-1`.

## Phase 1: create and enter the workload account

### 1. Prepare a unique account email address — complete

Choose a monitored mailbox or alias that:

- is not already attached to an AWS account;
- can receive account-recovery mail; and
- is controlled independently of this website's availability.

Do not put this address, its credentials, or recovery details in the source
repository.

### 2. Create the member account — complete

This must be done from the AWS Organizations **management account** (or by a
principal to which that operation has been delegated). The existing Womb
infrastructure member account cannot create a sibling member account.

In the AWS console:

1. Sign in to the Organizations management account.
2. Open **AWS Organizations**.
3. Select **AWS accounts**, then **Add an AWS account**.
4. Select **Create an AWS account**.
5. Use:
   - Account name: `henrybissonnette_personal`
   - Account email: the unique address prepared above
   - IAM role name: `OrganizationAccountAccessRole`
6. Add these tags if the organization does not already apply an equivalent
   tagging standard:
   - `Project = henrybissonnette`
   - `Environment = production`
   - `ManagedBy = terraform`
7. Put the account in the organization's existing workload or production OU.
   Do not create a new OU or weaken an organization policy just for this
   project.
8. Wait until account creation reports `Active`.
9. Record the 12-digit account ID in a private operational record. The account
   ID is not a credential, but it should not be mixed with passwords, access
   keys, or recovery codes.

AWS documents the management-account requirement and account-creation flow in
[Creating an AWS account in your organization](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_create.html).

### 3. Grant federated administrative access for bootstrap

Use the organization's existing IAM Identity Center setup:

1. In **IAM Identity Center**, assign Hank's existing user or administrative
   group to `henrybissonnette_personal`.
2. Assign the organization's normal administrative permission set for the
   bootstrap period. Scope the assignment to this member account.
3. Open the account from the AWS access portal.
4. Verify that the console header shows the new account name and account ID.

Do not create an IAM user, an IAM-user access key, a root access key, or a
long-lived GitHub secret. AWS documents account assignments in
[Assign user or group access to AWS accounts](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-accounts.html).

### 4. Enable centralized root access

The organization currently has centralized root access disabled. Enable it;
this is the recommended security posture for an Organization and the fact that
this is only the second account is not a reason to defer it.

From the Organizations management account:

1. Open the **IAM** console.
2. In the left navigation, choose **Root access management**.
3. Choose **Enable**. If AWS first asks to enable trusted access for IAM in
   Organizations, accept that prerequisite.
4. Enable both capabilities:
   - **Root credentials management**; and
   - **Privileged root actions in member accounts**.
5. Leave **Delegated administrator** empty for now. Delegating this authority
   is optional and deserves an explicit organization-security decision; it is
   not required to secure the new account.
6. Choose **Enable** and verify that root access management reports enabled.
7. In the account list, verify that `henrybissonnette_personal` has no root
   credentials. Do not recover a root password or add root MFA merely to make
   a credential exist.

If a future exceptional task truly requires root authority, use a centrally
authorized, short-lived privileged action or temporarily allow recovery, then
remove the recovered credentials when the task is complete. Never create root
access keys.

New Organizations accounts can be created without root credentials, and AWS
recommends centralized root access for member accounts. See
[Best practices for member accounts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_member-acct.html)
and [Centralize root access for member accounts](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-enable-root-access.html).

### 5. Identify the account parent and policy guardrails

The 12-digit value `241077340022` is the **account ID**, not an OU. An
organizational unit (OU) is a folder-like grouping of accounts under the
Organization's top-level **Root**. A service control policy (SCP) is an
organization-level ceiling on what accounts may do; it does not grant access,
but it can deny services even to an administrator.

From the Organizations management account:

1. Open **AWS Organizations** and choose **AWS accounts**.
2. Select `henrybissonnette_personal`.
3. In the hierarchy or account details, note its parent. With a small
   Organization this will probably be **Root**, which is acceptable for now.
   Do not create an OU solely to complete this checklist.
4. Open the account's **Policies** tab and select **Service control policies**.
5. If the only attached policy is `FullAWSAccess`, report that and stop. If
   other SCPs are attached, report only their names. Do not detach or edit
   them.

The project will later verify whether any non-default SCP categorically denies
the services expected for the first deployment:

- CloudFormation, IAM, STS, and the GitHub OIDC provider;
- S3, including S3 lockfiles, for Terraform state;
- Route 53, ACM, CloudFront, and AWS Budgets.

If a policy blocks one of these services, the project will adapt the design or
request a narrow organization-level change rather than asking you to loosen it
speculatively.

## Phase 2: verify registrar readiness without changing DNS

This is a readiness check, not the DNS cutover. Public DNS inspection already
confirmed that the domain uses name.com's four authoritative nameservers,
publishes no DS record, and currently has no apex A, AAAA, or MX records. There
is one apex TXT record. The account-side export is still needed because public
DNS cannot enumerate arbitrary subdomain records.

1. Sign in at name.com.
2. Secure the registrar account:
   - choose the user icon in the upper-right, then **Settings**;
   - choose **Two-Step Verification** under **Security**;
   - if no authenticator is listed, choose **Setup Authenticator App**, scan
     the QR code, enter the generated code, and complete verification; and
   - generate backup codes and store them in a password manager, not in this
     repository or conversation.
   Name.com's current instructions are in
   [Setting up Two-Step Verification](https://www.name.com/support/articles/205934297-setting-up-two-step-verification-with-google-authenticator).
3. Verify domain renewal:
   - choose **My Domains**, then `henrybissonnette.com`;
   - confirm that the domain status is active;
   - under **Quick Actions**, turn **Automatic Renewal** on; and
   - note the expiration date, but do not send payment information here.
4. Verify billing readiness:
   - choose the user icon, then **Billing**;
   - confirm there is a current default payment profile; and
   - update it if necessary.
   Name.com documents the per-domain renewal control in
   [Enabling or disabling automatic renewal](https://www.name.com/support/articles/205189058-enabling-disabling-automatic-renewal-for-your-domains).
5. Export the current zone:
   - return to **My Domains** and select `henrybissonnette.com`;
   - under **Domain Actions**, choose **Manage DNS Records**;
   - choose **Export DNS Records (CSV)** above the records; and
   - save the CSV privately. Do not commit it or paste its TXT values into the
     conversation. Keep it available for the later Route 53 migration.
   Name.com documents this control in
   [Exporting DNS records as a CSV file](https://www.name.com/support/articles/360007694113-exporting-dns-records-as-a-csv-file).
6. Confirm the current nameservers without changing them:
   - return to the domain details page;
   - under **Domain Actions**, choose **Manage Nameservers**; and
   - verify that four name.com nameservers are present.
7. No DNSSEC action is needed now. Public DNS shows no DS record, and name.com's
   own nameservers do not provide DNSSEC. We can enable Route 53 DNSSEC later
   as a separate automated change plus the unavoidable registrar-side DS
   update.

Do **not** change the nameservers yet. Terraform must first create the Route 53
hosted zone and reproduce every record that must survive the cutover. The
eventual name.com operation is documented in
[Changing nameservers for DNS management](https://www.name.com/support/articles/205934547-changing-nameservers-for-dns-management).

## Do not create these resources manually

Stop after the account, federated access, root-posture check, and registrar
readiness check. In particular, do not manually create:

- an S3 state or website bucket;
- a GitHub OIDC provider or deployment role;
- IAM users or access keys;
- a Route 53 hosted zone or DNS records;
- ACM certificates or CloudFront distributions;
- budgets, alarms, application services, or databases; or
- GitHub repository secrets containing AWS credentials.

The project will check in a bootstrap definition for the small circular trust
boundary, then manage the remaining resources through Terraform. GitHub will
use repository-scoped OIDC and temporary AWS credentials rather than stored
AWS keys. See GitHub's
[OIDC configuration for AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).

Do not clean or rearrange the old repository before the bootstrap. The project
will preserve its history and move obsolete site content under `legacy/` as a
separate, reviewable source change.

## Safe completion report

Reply with only these non-secret facts:

- new account status: created / blocked;
- account name and 12-digit account ID;
- OU name;
- IAM Identity Center access: verified / blocked;
- centralized root access: enabled / disabled / unknown;
- blocking SCP names, if any;
- name.com access and two-step verification: verified / blocked;
- DNSSEC: enabled / disabled / unknown; and
- current DNS contains mail or other records that must be preserved: yes / no
  / unknown.

Do not send passwords, access keys, session tokens, recovery codes, payment
details, the account-owner mailbox, or complete DNS TXT record values.

## What happens next

After this checklist is complete, the project can produce the exact bootstrap
stack and a reviewed Terraform plan. The remaining human actions should be
limited to:

1. launching the checked-in bootstrap stack once from the new member account;
2. supplying the budget notification address as a non-source parameter;
3. changing name.com's nameservers only after the replacement zone has been
   verified; and
4. making a product-level decision if a proposed change risks irreversible
   loss of product data or capability, or performing account/trust recovery
   that only the account owner can authorize.

Routine selection, creation, modification, verification, and deployment of
infrastructure remain agent-owned work. Terraform's use of a resource
replacement is not, by itself, a reason to involve a human.

## Review feedback

Reviewed by claude/clause, 2026-08-08, against Hank's three objectives:
(1) minimal human involvement, (2) light and simple with maximum agent
liberty, (3) extensible without further human effort.

### Overall

This is a strong draft. The core shape is right: a dedicated member account,
federated human access, no manual resources, no long-lived keys, GitHub OIDC
for deployment credentials, and everything past the bootstrap owned by
Terraform. The closing rule — humans step in only for irreversible loss of
product data or capability, or for account/trust recovery, and a Terraform
resource replacement is not by itself a human matter — is exactly the right
place to draw the red-tape line. The notes below are refinements, not
objections.

### 1. Agent credential path is the biggest open question (objectives 1 and 2)

The draft gives GitHub Actions an OIDC path to AWS, but never says how the
agents themselves reach AWS for day-to-day work: `terraform plan`, reading
CloudFront or Route 53 state, debugging a failed deploy. If CI is the only
credentialed path, every inspection requires a commit and a workflow run —
that is exactly the procedural drag objective 2 warns against.

Recommendation: the bootstrap stack should establish a credential path the
agent workbench can use directly, decided explicitly rather than left
implicit. Reasonable options, simplest first:

- Hank runs `aws sso login` (or equivalent) against the member account when
  starting a work session and exposes the short-lived credentials to the
  agent environment; zero new infrastructure, but re-involves the human on a
  session cadence.
- The bootstrap stack creates a role the agent environment can assume
  through some existing trust (only if Womb infrastructure already has AWS
  identity of its own).
- Fallback: agents drive everything through CI, but then add a manually
  triggerable plan/inspect workflow (`workflow_dispatch`) so exploration
  does not require synthetic commits.

Whichever is chosen, it belongs in the bootstrap stack now, not as a later
retrofit.

### 2. Make the deployment role broad; let the account be the guardrail (objectives 2 and 3)

The draft does not yet state how the OIDC deployment role is scoped. This is
the single decision that most determines whether future phases bounce back
to Hank. If the role is scoped to today's static-site services (S3,
CloudFront, Route 53, ACM), then the planned "more dynamic" phase — Lambda,
API Gateway, a database — requires the human to re-run the bootstrap to
widen it, violating objective 3.

Recommendation: state as a bootstrap design requirement that the deployment
role is broadly permissioned within the account (administrator- or
power-user-level plus the IAM permissions Terraform needs), and rely on the
account boundary, SCPs, and budget alarms as the real blast-radius controls.
In a dedicated single-purpose account, fine-grained IAM on the deploy role
is mostly ceremony: it adds recurring human effort and blocks agent work
while protecting little that the account boundary does not already protect.
This is also the justification for the member-account step — it is the
heaviest human task in the runbook, but it is what makes "broad role, light
procedure" safe. Keep it.

### 3. Minimize the bootstrap launch itself (objective 1)

"Launching the checked-in bootstrap stack once" should be specified as a
single action: one copy-pasteable CLI command or a CloudFormation
quick-create link, with the budget notification address as its only
parameter. If the address is stored at bootstrap time (e.g. as an SSM
parameter), later stacks can reference it and no future work needs to ask
Hank for it again — small, but it removes a recurring human touchpoint.

### 4. Smaller notes

- **State locking:** prefer Terraform's native S3 lockfile (`use_lockfile`,
  Terraform ≥ 1.10) and drop the DynamoDB table entirely. The draft already
  allows this; make it the default — one less resource, nothing lost.
- **Repository name:** "Known inputs" lists the source repository as
  `henrybissonnette/henrydbissonnette` (note the extra `d`). If that is the
  real legacy repo name, fine; otherwise fix the typo before it propagates
  into OIDC trust conditions, where an exact-match repo claim would fail.
- **Correct and worth keeping as-is:** the us-east-1 ACM/CloudFront note;
  refusing to touch nameservers before Route 53 reproduces existing records
  (especially mail); the root-access posture handling; the "report, don't
  loosen" SCP stance; and the non-secret completion report format.

### Verdict

Approve with the additions above. Items 1 and 2 should be resolved in the
bootstrap stack design before the human runs Phase 1, since both affect what
the bootstrap creates; item 3 and the smaller notes can be folded in as the
bootstrap definition is written. Terraform's use of a resource
replacement is not, by itself, a reason to involve a human.
