mock_provider "aws" {
  mock_data "aws_sns_topic" {
    defaults = {
      arn  = "arn:aws:sns:us-east-1:241077340022:henrybissonnette-budget-notifications"
      name = "henrybissonnette-budget-notifications"
    }
  }

  mock_resource "aws_acm_certificate" {
    defaults = {
      domain_validation_options = [
        {
          domain_name           = "henrybissonnette.com"
          resource_record_name  = "_apex-validation.henrybissonnette.com"
          resource_record_type  = "CNAME"
          resource_record_value = "_apex.acm-validations.aws"
        },
        {
          domain_name           = "www.henrybissonnette.com"
          resource_record_name  = "_www-validation.henrybissonnette.com"
          resource_record_type  = "CNAME"
          resource_record_value = "_www.acm-validations.aws"
        }
      ]
    }
  }
}

run "staging_increment" {
  command = plan

  variables {
    custom_domain_enabled = false
  }

  assert {
    condition     = length(aws_acm_certificate.site) == 0
    error_message = "staging must not request an ACM certificate before Route 53 is authoritative"
  }

  assert {
    condition     = length(aws_route53_record.certificate_validation) == 0
    error_message = "staging must not create certificate validation records"
  }

  assert {
    condition     = length(aws_route53_record.site_alias_ipv4) == 0 && length(aws_route53_record.site_alias_ipv6) == 0
    error_message = "staging must not create apex or www aliases"
  }

  assert {
    condition     = length(aws_cloudfront_distribution.site.aliases) == 0
    error_message = "staging distribution must use only its generated CloudFront hostname"
  }

  assert {
    condition     = aws_cloudfront_distribution.site.viewer_certificate[0].cloudfront_default_certificate
    error_message = "staging must use the CloudFront default certificate"
  }
}

run "custom_domain_increment" {
  command = plan

  variables {
    custom_domain_enabled = true
  }

  assert {
    condition     = length(aws_acm_certificate.site) == 1
    error_message = "custom-domain increment must add exactly one apex-and-www certificate"
  }

  assert {
    condition     = length(aws_route53_record.certificate_validation) == 2
    error_message = "custom-domain increment must add exactly the apex and www validation records"
  }

  assert {
    condition     = length(aws_route53_record.site_alias_ipv4) == 2 && length(aws_route53_record.site_alias_ipv6) == 2
    error_message = "custom-domain increment must add A and AAAA aliases for exactly apex and www"
  }

  assert {
    condition     = toset(aws_cloudfront_distribution.site.aliases) == toset(["henrybissonnette.com", "www.henrybissonnette.com"])
    error_message = "custom-domain distribution aliases must be exactly apex and www"
  }

  assert {
    condition     = !aws_cloudfront_distribution.site.viewer_certificate[0].cloudfront_default_certificate
    error_message = "custom-domain increment must replace the default viewer certificate"
  }
}
