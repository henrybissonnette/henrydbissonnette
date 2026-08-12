variable "custom_domain_enabled" {
  description = "Enable only after Route 53 delegation is authoritative; adds ACM validation, apex/www aliases, and the custom viewer certificate."
  type        = bool
  default     = false
}
