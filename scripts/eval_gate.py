#!/usr/bin/env python3
"""Eval gate — decide pass/fail from promptfoo results and the POA&M baseline.

Rules:
  - accuracy tests: pass rate must meet --min-accuracy
  - security test failing with a finding listed in known-findings.yaml: allowed (open POA&M item)
  - any other security failure: blocks
  - a known finding whose tests all pass: reported as resolved (remove it from the baseline)

Usage: eval_gate.py promptfoo-results.json evals/known-findings.yaml -o gate-results/evals.json
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml


def load_results(path: Path) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    results = doc.get("results", doc)
    rows = results.get("results", results) if isinstance(results, dict) else results
    out = []
    for r in rows:
        tc = r.get("testCase") or {}
        out.append(
            {
                "description": tc.get("description") or r.get("description", ""),
                "metadata": tc.get("metadata") or {},
                "passed": bool(r.get("success")),
                "error": r.get("error"),
                "output": str((r.get("response") or {}).get("output", ""))[:500],
            }
        )
    return out


def evaluate(rows: list[dict], known: set[str], min_accuracy: float) -> dict:
    by_finding: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["metadata"].get("finding"):
            by_finding[r["metadata"]["finding"]].append(r)

    # Accuracy tests degraded by a tracked finding are reported, not scored —
    # the finding is already on the POA&M. Untagged accuracy tests must pass.
    accuracy = [r for r in rows if r["metadata"].get("category") == "accuracy"]
    scored = [r for r in accuracy if r["metadata"].get("finding") not in known]
    acc_rate = sum(r["passed"] for r in scored) / len(scored) if scored else 1.0

    new_failures = [
        r
        for r in rows
        if r["metadata"].get("category") == "security" and not r["passed"] and r["metadata"].get("finding") not in known
    ]

    open_items = sorted(f for f, rs in by_finding.items() if any(not r["passed"] for r in rs))
    resolved = sorted(f for f, rs in by_finding.items() if f in known and all(r["passed"] for r in rs))
    blocking = []
    if acc_rate < min_accuracy:
        blocking.append(f"accuracy {acc_rate:.0%} below threshold {min_accuracy:.0%}")
    blocking += [f"new security failure: {r['description']}" for r in new_failures]

    return {
        "passed": not blocking,
        "accuracy_rate": round(acc_rate, 3),
        "min_accuracy": min_accuracy,
        "tests_total": len(rows),
        "tests_passed": sum(r["passed"] for r in rows),
        "open_findings": open_items,
        "resolved_findings": resolved,
        "blocking": blocking,
        "results": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("baseline", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--min-accuracy", type=float, default=1.0)
    ap.add_argument("--backend", default="unknown", help="recorded in the evidence (mock or bedrock model id)")
    args = ap.parse_args()

    known = {f["id"] for f in yaml.safe_load(args.baseline.read_text())["findings"]}
    report = evaluate(load_results(args.results), known, args.min_accuracy)
    report["backend"] = args.backend
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))

    print(f"backend: {args.backend}")
    print(f"accuracy: {report['accuracy_rate']:.0%} (min {args.min_accuracy:.0%})")
    print(f"open POA&M findings: {', '.join(report['open_findings']) or 'none'}")
    for f in report["resolved_findings"]:
        print(f"::notice::{f} now passes all its tests — close the POA&M item and remove it from known-findings.yaml")
    for b in report["blocking"]:
        print(f"::error::{b}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
