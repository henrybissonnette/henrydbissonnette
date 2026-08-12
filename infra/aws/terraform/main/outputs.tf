output "content_bucket_name" {
  description = "Private versioned origin bucket consumed by the publication workflow."
  value       = aws_s3_bucket.content.bucket
}

output "cloudfront_distribution_id" {
  description = "Distribution identifier consumed by publication and bounded inspection."
  value       = aws_cloudfront_distribution.site.id
}

output "cloudfront_staging_hostname" {
  description = "Generated CloudFront hostname used before custom-domain activation."
  value       = aws_cloudfront_distribution.site.domain_name
}

output "hosted_zone_id" {
  description = "Route 53 zone identifier used by DNS parity and delegation work."
  value       = aws_route53_zone.site.zone_id
}

output "hosted_zone_name_servers" {
  description = "Public authoritative nameservers supplied to the registrar only after parity review."
  value       = aws_route53_zone.site.name_servers
}

output "custom_domain_enabled" {
  description = "Current two-increment domain phase."
  value       = var.custom_domain_enabled
}
