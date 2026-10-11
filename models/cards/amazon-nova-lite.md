# Model card — Amazon Nova Lite (`amazon.nova-lite-v1:0`)

| Field | Value |
|---|---|
| Provider | AWS Bedrock (managed API — weights are not in our supply chain) |
| Registry status | Approved by ai-governance-board, review by 2027-04-10 |
| Used by | `benefits-caseworker-assistant` |
| Max system risk tier | high-impact (with human-in-the-loop) |

## Intended use

Generate answers grounded in retrieved program-policy text, and draft
determination notes that a caseworker reviews before anything is filed.

## Out of scope

- Autonomous eligibility decisions without human review
- Processing applicant PII in prompts (the corpus and eval data are PII-free and
  the PII gate enforces it)

## Known limitations and risks

| Risk | NIST AI 600-1 category | Mitigation in this repo |
|---|---|---|
| Follows instructions embedded in retrieved text | Information Security | Red-team evals (`evals/`), planted `AIGG-LAB-02` |
| Confident but wrong answers | Confabulation | Answers cite retrieved sources; caseworker review |
| Inconsistent outcomes across groups | Harmful Bias and Homogenization | Out of scope for this scaffold — add a bias eval set before production use |

## Evaluation

Evaluated on every release by `evals/promptfooconfig.yaml` against the live
model. Results and control mappings are published in each release's evidence
bundle.
