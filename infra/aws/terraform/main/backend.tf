terraform {
  backend "s3" {
    bucket       = "henrybissonnette-terraform-state-241077340022"
    key          = "main/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
