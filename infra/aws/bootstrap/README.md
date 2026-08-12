# Permanent AWS bootstrap foundation

CloudFormation stack name: `henrybissonnette-bootstrap`

[`template.json`](template.json) permanently owns the GitHub OIDC provider,
the one broad apply role, the retained Terraform-state bucket and policy, and
the SNS notification foundation. Terraform must consume their stable
non-secret identifiers without declaring, importing, replacing, or destroying
them.

The template is launched later, not by this source task. The authorized handoff
is an exact public-commit download, a recorded SHA-256 comparison, and console
**Upload a template file** in account `241077340022`. The only private input is
`BudgetNotificationEmail`; it has no source default or output. Do not use a raw
GitHub quick-create URL, copy the template into another owner, or improvise a
different state bucket name.

An ordinary failed first launch may be deleted only before the first Terraform
state write. After state has been used, the retained bucket, policy, trust, and
stack are an owner-authority recovery boundary. See
[`docs/aws-infrastructure.md`](../../../docs/aws-infrastructure.md) for the
verification and recovery contracts.
