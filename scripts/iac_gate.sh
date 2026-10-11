#!/usr/bin/env bash
# IaC gate for infra/ (Terraform).
#   1. Negative controls: prove Checkov fails two planted IAM mistakes —
#      an admin "*:*" policy, and a GitHub OIDC trust policy with no repo
#      subject (any GitHub repo could assume the role).
#   2. Scan the real Terraform. Any failed check fails the gate.
# Writes gate-results/iac.json.
#
# Checkov rather than Trivy: Trivy's IaC checks did not flag an admin "*:*"
# aws_iam_policy in testing, and this stack is entirely IAM.
set -euo pipefail

OUT=gate-results
mkdir -p "$OUT"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

failed_ids() { # dir -> sorted failed check IDs, one per line
  # checkov exits 1 when checks fail — expected here, so don't let pipefail abort
  { checkov -d "$1" --framework terraform --quiet --compact -o json 2>/dev/null || true; } |
    python3 -c 'import json,sys
d=json.load(sys.stdin); d=d[0] if isinstance(d,list) else d
print("\n".join(sorted({c["check_id"] for c in d.get("results",{}).get("failed_checks",[])})))'
}

# ── 1. Negative controls ─────────────────────────────────────────────────────
mkdir -p "$WORK/admin" "$WORK/oidc"
cat > "$WORK/admin/main.tf" <<'EOF'
resource "aws_iam_policy" "admin" {
  name = "negative-control-admin"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "*", Resource = "*" }]
  })
}
EOF
cat > "$WORK/oidc/main.tf" <<'EOF'
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
EOF

ADMIN=$(failed_ids "$WORK/admin")
OIDC=$(failed_ids "$WORK/oidc")
grep -qx CKV_AWS_62 <<<"$ADMIN" || { echo "::error::Negative control failed: admin *:* policy not flagged (CKV_AWS_62)"; exit 1; }
grep -qx CKV_AWS_358 <<<"$OIDC" || { echo "::error::Negative control failed: OIDC trust without repo subject not flagged (CKV_AWS_358)"; exit 1; }
echo "negative controls: admin policy → $(wc -l <<<"$ADMIN") failed checks; OIDC any-repo → CKV_AWS_358 ✓"

# Mutation control on the real stack: strip the repo-subject condition from
# infra/aws and require Checkov to notice. This proves the scanner can actually
# see our trust policy — Checkov skips CKV_AWS_358 when it cannot resolve the
# principal (e.g. a resource reference instead of the OIDC provider ARN).
cp -r infra/aws "$WORK/mutant"
rm -rf "$WORK/mutant/.terraform"
python3 - "$WORK/mutant/main.tf" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p).read()
mutated = re.sub(r'\n    condition \{\n      test     = "StringEquals"\n      variable = "\$\{local\.oidc_host\}:sub"\n.*?\n    \}\n', "\n", s, flags=re.S)
if mutated == s:
    sys.exit("mutation control: could not find the :sub condition in infra/aws/main.tf — update this script")
open(p, "w").write(mutated)
PY
grep -qx CKV_AWS_358 <<<"$(failed_ids "$WORK/mutant")" || {
  echo "::error::Mutation control failed: removing the OIDC :sub condition from infra/aws went undetected — Checkov cannot see the real trust policy"
  exit 1
}
echo "mutation control: real trust policy without :sub → CKV_AWS_358 ✓"

# ── 2. Scan the real Terraform ───────────────────────────────────────────────
set +e
checkov -d infra --framework terraform --quiet --compact -o json > "$WORK/scan.json" 2>/dev/null
set -e
python3 - "$WORK/scan.json" "$OUT/iac.json" <<'PY'
import json, sys
src, out = sys.argv[1:]
docs = json.load(open(src))
docs = docs if isinstance(docs, list) else [docs]
failed = [
    {"check_id": c["check_id"], "name": c["check_name"], "file": c["file_path"], "resource": c["resource"]}
    for d in docs for c in d.get("results", {}).get("failed_checks", [])
]
passed = sum(d.get("summary", {}).get("passed", 0) for d in docs)
json.dump({"passed": not failed, "checks_passed": passed, "failed": failed,
           "negative_controls": ["CKV_AWS_62 admin policy", "CKV_AWS_358 OIDC any-repo trust"]},
          open(out, "w"), indent=2)
for f in failed:
    print(f"::error file=infra/{f['file'].lstrip('/')}::{f['check_id']} {f['name']} ({f['resource']})")
print(f"infra: {passed} checks passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
PY
