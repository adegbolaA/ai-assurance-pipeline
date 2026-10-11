#!/usr/bin/env bash
# Model supply-chain gate.
#   1. Negative control: build a malicious pickle and prove ModelScan blocks it.
#   2. Scan every model artifact in the repo. Any finding fails the gate.
# Writes gate-results/modelscan.json.
#
# This app calls a hosted model (no weights in the repo), so step 2 normally
# finds nothing to scan. The gate still runs: the moment someone commits a
# .pkl/.pt/.h5/.onnx/.safetensors file, it is scanned before it can ship.
set -euo pipefail

OUT=gate-results
mkdir -p "$OUT"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# ── 1. Negative control ─────────────────────────────────────────────────────
python3 - "$WORK/malicious.pkl" <<'PY'
import os, pickle, sys
class Payload:
    def __reduce__(self):
        return (os.system, ("echo pwned",))  # never executed; ModelScan reads opcodes only
with open(sys.argv[1], "wb") as f:
    pickle.dump(Payload(), f)
PY
set +e
modelscan -p "$WORK/malicious.pkl" -r json -o "$WORK/control.json" >/dev/null 2>&1
CONTROL_RC=$?
set -e
if [[ $CONTROL_RC -ne 1 ]]; then
  echo "::error::Negative control failed: ModelScan did not flag a malicious pickle (exit $CONTROL_RC)"
  exit 1
fi
echo "negative control: ModelScan flagged the malicious pickle (exit 1) ✓"

# ── 2. Scan real artifacts ───────────────────────────────────────────────────
mapfile -t ARTIFACTS < <(git ls-files | grep -Ei '\.(pkl|pickle|joblib|dill|pt|pth|bin|h5|keras|pb|onnx|safetensors|npy|npz)$' || true)

if [[ ${#ARTIFACTS[@]} -eq 0 ]]; then
  echo "no model artifacts tracked in the repo — hosted model only"
  printf '{"passed": true, "negative_control": "blocked", "artifacts": [], "issues": 0}\n' > "$OUT/modelscan.json"
  exit 0
fi

ISSUES=0
for a in "${ARTIFACTS[@]}"; do
  set +e
  modelscan -p "$a" -r json -o "$WORK/scan.json" >/dev/null 2>&1
  RC=$?
  set -e
  case $RC in
    0|3) echo "clean: $a" ;;
    1)   echo "::error file=$a::ModelScan found unsafe operators"; ISSUES=$((ISSUES + 1)) ;;
    *)   echo "::error file=$a::ModelScan error (exit $RC)"; ISSUES=$((ISSUES + 1)) ;;
  esac
done

python3 - "$OUT/modelscan.json" "$ISSUES" "${ARTIFACTS[@]}" <<'PY'
import json, sys
out, issues, artifacts = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
json.dump({"passed": issues == 0, "negative_control": "blocked", "artifacts": artifacts, "issues": issues},
          open(out, "w"), indent=2)
PY
[[ $ISSUES -eq 0 ]]
