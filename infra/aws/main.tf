# Least-privilege AWS access for the release workflow's live-model evals.
#
#   GitHub OIDC token (repo + ai-eval environment)
#     → sts:AssumeRoleWithWebIdentity on the eval role
#     → bedrock:InvokeModel on the registered model(s) only
#
# No long-lived AWS keys exist anywhere in the pipeline.

data "aws_caller_identity" "current" {}

locals {
  oidc_host = "token.actions.githubusercontent.com"
  oidc_arn  = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${local.oidc_host}"
  # GitHub's immutable subject format (repo:owner@id/repo@id:...), which this
  # repo uses. The IDs survive renames and cannot be claimed by someone who
  # later creates a repo under an old name.
  github_owner = split("/", var.github_repository)[0]
  github_repo  = split("/", var.github_repository)[1]
  oidc_subject = "repo:${local.github_owner}@${var.github_owner_id}/${local.github_repo}@${var.github_repository_id}:environment:${var.github_environment}"
  model_arns   = [for id in var.model_ids : "arn:aws:bedrock:${var.region}::foundation-model/${id}"]
}

resource "aws_iam_openid_connect_provider" "github" {
  count = var.manage_oidc_provider ? 1 : 0

  url            = "https://${local.oidc_host}"
  client_id_list = ["sts.amazonaws.com"]
  # AWS validates GitHub's OIDC certificate against its own trust store and
  # ignores thumbprints for this provider; they are kept so the configuration
  # matches what was created.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]

  lifecycle {
    # Account-wide: other repos' roles may trust it.
    prevent_destroy = true
  }
}

data "aws_iam_policy_document" "trust" {
  statement {
    sid     = "GitHubActionsAiEvalEnvironmentOnly"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    # The ARN string, not a resource reference: Checkov can only recognise a
    # GitHub OIDC trust (and run CKV_AWS_358) when the principal visibly names
    # token.actions.githubusercontent.com. Ordering is kept by depends_on below.
    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Exact subject — no wildcards. Jobs without `environment: ai-eval`, other
    # repos, forks and pull requests all present a different subject.
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = [local.oidc_subject]
    }
  }
}

resource "aws_iam_role" "bedrock_eval" {
  name                 = "ai-governance-gate-bedrock-eval"
  description          = "GitHub Actions (${var.github_repository}, ${var.github_environment} environment) - invoke registered Bedrock model for release evals"
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  max_session_duration = 3600

  depends_on = [aws_iam_openid_connect_provider.github]
}

data "aws_iam_policy_document" "invoke" {
  statement {
    sid       = "InvokeRegisteredModelOnly"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel"] # Converse API is authorized by InvokeModel
    resources = local.model_arns
  }
}

resource "aws_iam_role_policy" "invoke" {
  name   = "invoke-amazon-nova-lite"
  role   = aws_iam_role.bedrock_eval.id
  policy = data.aws_iam_policy_document.invoke.json
}
