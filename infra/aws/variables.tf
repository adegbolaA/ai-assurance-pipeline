variable "region" {
  description = "Region of the Bedrock model the release evals call."
  type        = string
  default     = "us-east-1"
}

variable "github_repository" {
  description = "owner/repo allowed to assume the eval role."
  type        = string
  default     = "adegbolaA/ai-assurance-pipeline"
}

variable "github_environment" {
  description = <<-EOT
    GitHub Environment the eval job runs in. The role trusts only this
    environment's OIDC subject, and the environment is restricted to main —
    so only release runs from main can assume the role.
  EOT
  type        = string
  default     = "ai-eval"
}

variable "model_ids" {
  description = <<-EOT
    Bedrock foundation models the role may invoke. Keep in sync with the
    approved entries in models/registry.yaml: the registry is the governance
    record, this is its enforcement in AWS.
  EOT
  type        = list(string)
  default     = ["amazon.nova-lite-v1:0"]
}

variable "manage_oidc_provider" {
  description = <<-EOT
    Create the account-wide GitHub OIDC provider here. Set false if another
    stack owns it (one provider per account, shared by every repo).
  EOT
  type        = bool
  default     = true
}
