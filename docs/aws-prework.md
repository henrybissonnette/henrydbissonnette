# AWS pre-work for henrybissonnette.com

Status: ready for the account owner to follow

This runbook contains only the human-owned work needed before the project can
bootstrap its AWS infrastructure. It intentionally stops before creating any
workload resources. The project will define those resources in source and
manage them through Terraform.

## Known inputs

- Domain: `henrybissonnette.com`
- Source repository: `henrybissonnette/henrydbissonnette`
- Registrar: name.com
- Preferred AWS topology: a dedicated member account in the existing AWS
  Organization
- Primary deployment region: `us-east-1`
- Budget notification address: supplied out of band; do not commit it

The region is a default for the initial workload, not a requirement that every
future project use it. CloudFront certificates must be created in `us-east-1`.

## Phase 1: create and enter the workload account

### 1. Prepare a unique account email address

Choose a monitored mailbox or alias that:

- is not already attached to an AWS account;
- can receive account-recovery mail; and
- is controlled independently of this website's availability.

Do not put this address, its credentials, or recovery details in the source
repository.

### 2. Create the member account

This must be done from the AWS Organizations **management account** (or by a
principal to which that operation has been delegated). The existing Womb
infrastructure member account cannot create a sibling member account.

In the AWS console:

1. Sign in to the Organizations management account.
2. Open **AWS Organizations**.
3. Select **AWS accounts**, then **Add an AWS account**.
4. Select **Create an AWS account**.
5. Use:
   - Account name: `henrybissonnette-prod`
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
   group to `henrybissonnette-prod`.
2. Assign the organization's normal administrative permission set for the
   bootstrap period. Scope the assignment to this member account.
3. Open the account from the AWS access portal.
4. Verify that the console header shows the new account name and account ID.

Do not create an IAM user, an IAM-user access key, a root access key, or a
long-lived GitHub secret. AWS documents account assignments in
[Assign user or group access to AWS accounts](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-accounts.html).

### 4. Check the organization's root-access posture

In the Organizations management account, check whether **IAM > Root access
management** is enabled.

- If centralized root access is enabled, leave the new member account without
  root credentials. Do not recover a password or add root MFA merely for this
  project.
- If it is not enabled, report that fact before changing anything. Enabling it
  is an organization-wide security decision, not website pre-work. If a member
  root login is later required, protect it with MFA and never create root
  access keys.

New Organizations accounts can be created without root credentials, and AWS
recommends centralized root access for member accounts. See
[Best practices for member accounts](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_best-practices_member-acct.html)
and [Centralize root access for member accounts](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-enable-root-access.html).

### 5. Report policy constraints; do not loosen them

Note the OU containing the account and any service control policies that are
attached to it. If practical, verify that they do not categorically deny the
services expected for the first deployment:

- CloudFormation, IAM, STS, and the GitHub OIDC provider;
- S3, including S3 lockfiles, for Terraform state;
- Route 53, ACM, CloudFront, and AWS Budgets.

If a policy blocks one of these services, report the policy name or the denied
operation. Do not detach or weaken an SCP as part of this runbook. We will
adapt the design or request a narrow organization-level change.

## Phase 2: verify registrar readiness without changing DNS

This is a readiness check, not the DNS cutover.

1. Sign in to name.com and confirm that `henrybissonnette.com` is active.
2. Confirm that automatic renewal and the payment method are current.
3. Confirm that two-step verification is enabled and that recovery codes are
   stored securely. Name.com's current instructions are in
   [Setting up Two-Step Verification](https://www.name.com/support/articles/205934297-setting-up-two-step-verification-with-google-authenticator).
4. Record the current authoritative nameservers.
5. Export or privately capture all current DNS records, especially MX, TXT,
   CAA, SRV, and verification records. Do not paste full TXT values into the
   repository or project conversation.
6. Record whether DNSSEC is enabled and whether a DS record is present.

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
