output "eval_role_arn" {
  description = "Set as the AWS_EVAL_ROLE_ARN variable on the ai-eval GitHub Environment."
  value       = aws_iam_role.bedrock_eval.arn
}

output "allowed_models" {
  value = local.model_arns
}
