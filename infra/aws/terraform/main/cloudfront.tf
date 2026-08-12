resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "henrybissonnette-site-content"
  description                       = "SigV4 access from the single site distribution to the private S3 REST origin."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "legacy_redirects" {
  name    = "henrybissonnette-legacy-redirects"
  comment = "Three exact same-host legacy successor redirects; routing remains O(3)."
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = file("${path.module}/edge_redirects.js")
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "henrybissonnette.com static publication"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  aliases             = var.custom_domain_enabled ? local.custom_domain_hostnames : []

  origin {
    domain_name              = aws_s3_bucket.content.bucket_regional_domain_name
    origin_id                = local.cloudfront_origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id

    s3_origin_config {
      origin_access_identity = ""
    }
  }

  default_cache_behavior {
    target_origin_id       = local.cloudfront_origin_id
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = local.cloudfront_cache_policy

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.legacy_redirects.arn
    }
  }

  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  dynamic "viewer_certificate" {
    for_each = var.custom_domain_enabled ? [] : [true]

    content {
      cloudfront_default_certificate = true
    }
  }

  dynamic "viewer_certificate" {
    for_each = var.custom_domain_enabled ? [true] : []

    content {
      acm_certificate_arn      = aws_acm_certificate_validation.site[0].certificate_arn
      ssl_support_method       = "sni-only"
      minimum_protocol_version = "TLSv1.2_2021"
    }
  }
}
