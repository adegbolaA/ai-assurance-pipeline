# NEGATIVE CONTROL — must fail CKV_AWS_62 (full admin privileges). Never applied.
resource "aws_iam_policy" "admin" {
  name = "negative-control-admin"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "*", Resource = "*" }]
  })
}
