locals {
  aws_account_id = "241077340022"
  aws_region     = "us-east-1"
  domain_name    = "henrybissonnette.com"
  www_name       = "www.henrybissonnette.com"

  content_bucket_name     = "henrybissonnette-site-content-241077340022"
  budget_topic_name       = "henrybissonnette-budget-notifications"
  cloudfront_origin_id    = "private-site-content"
  cloudfront_cache_policy = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  custom_domain_hostnames = [local.domain_name, local.www_name]
}
