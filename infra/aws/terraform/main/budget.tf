data "aws_sns_topic" "budget_notifications" {
  name = local.budget_topic_name
}

resource "aws_budgets_budget" "site" {
  name         = "henrybissonnette-monthly-actual-cost"
  budget_type  = "COST"
  limit_amount = "10"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [data.aws_sns_topic.budget_notifications.arn]
  }
}
