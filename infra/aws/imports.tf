# These resources were first created with the AWS CLI and adopted into
# Terraform. After the first apply the blocks are no-ops; keep them so a fresh
# state (new machine, lost local state) re-adopts instead of failing on
# "already exists". Remove them if the stack moves to a remote backend.

import {
  for_each = var.manage_oidc_provider ? toset(["github"]) : toset([])
  to       = aws_iam_openid_connect_provider.github[0]
  id       = local.oidc_arn
}

import {
  to = aws_iam_role.bedrock_eval
  id = "ai-governance-gate-bedrock-eval"
}

import {
  to = aws_iam_role_policy.invoke
  id = "ai-governance-gate-bedrock-eval:invoke-amazon-nova-lite"
}
