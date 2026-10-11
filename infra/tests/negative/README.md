# Negative-control fixtures

Deliberately insecure Terraform. Never applied — `iac.yml` scans each fixture
and **fails if Checkov does not flag it**, proving the scanner catches these
mistakes before its verdict on `infra/aws` is trusted. The real scan skips
this directory.

| Fixture | Mistake | Must trigger |
|---|---|---|
| `admin_policy/` | IAM policy allowing `*` on `*` | `CKV_AWS_62` |
| `oidc_any_repo/` | GitHub OIDC trust with no repo subject — any repo can assume the role | `CKV_AWS_358` |
