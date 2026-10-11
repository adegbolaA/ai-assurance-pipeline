# NEGATIVE CONTROL — must fail CKV_AWS_358 (GitHub OIDC trust not pinned to a
# repo: only the audience is checked, so any GitHub repo can assume the role).
# Never applied.
data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "any_repo" {
  name               = "negative-control-any-repo"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}
