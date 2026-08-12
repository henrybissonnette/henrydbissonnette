resource "aws_route53_zone" "site" {
  name    = local.domain_name
  comment = "Public authority for henrybissonnette.com after registrar delegation."

  lifecycle {
    prevent_destroy = true
  }
}

# Task 07 adds each explicitly reviewed surviving public name.com record here
# before delegation. There is deliberately no generic CSV or secret input path.

resource "aws_acm_certificate" "site" {
  count = var.custom_domain_enabled ? 1 : 0

  domain_name               = local.domain_name
  subject_alternative_names = [local.www_name]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "certificate_validation" {
  for_each = var.custom_domain_enabled ? toset(local.custom_domain_hostnames) : toset([])

  zone_id = aws_route53_zone.site.zone_id
  name = one([
    for option in aws_acm_certificate.site[0].domain_validation_options : option.resource_record_name
    if option.domain_name == each.value
  ])
  type = one([
    for option in aws_acm_certificate.site[0].domain_validation_options : option.resource_record_type
    if option.domain_name == each.value
  ])
  records = [one([
    for option in aws_acm_certificate.site[0].domain_validation_options : option.resource_record_value
    if option.domain_name == each.value
  ])]
  ttl             = 300
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "site" {
  count = var.custom_domain_enabled ? 1 : 0

  certificate_arn         = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [for record in aws_route53_record.certificate_validation : record.fqdn]
}

resource "aws_route53_record" "site_alias_ipv4" {
  for_each = var.custom_domain_enabled ? toset(local.custom_domain_hostnames) : toset([])

  zone_id = aws_route53_zone.site.zone_id
  name    = each.value
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "site_alias_ipv6" {
  for_each = var.custom_domain_enabled ? toset(local.custom_domain_hostnames) : toset([])

  zone_id = aws_route53_zone.site.zone_id
  name    = each.value
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}
