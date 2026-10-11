# AI impact assessment — Benefits Caseworker Assistant

Required for high-impact AI under OMB M-25-21 and referenced from `ai-system.yaml`.
The policy gate fails the build if a high-impact system has no impact assessment.

## 1. Purpose and expected benefit

Caseworkers spend significant time locating the right rule in program policy.
The assistant retrieves the relevant policy text and drafts a determination
note. Expected benefit: faster, more consistent application of written rules.

## 2. Why this is high-impact

The drafted note can become a principal basis for a decision about access to a
government benefit. Errors could wrongly delay or deny housing assistance.

## 3. Data

| Source | Contents | PII | Control |
|---|---|---|---|
| `app/corpus` | Published program policy text | None | Presidio gate on every PR |
| `evals/promptfooconfig.yaml` | Synthetic test questions | None | Presidio gate on every PR |

No applicant data is sent to the model. Ingesting case files would change this
assessment and require `pii_handling` in `ai-system.yaml`.

## 4. Risks and mitigations

| Risk | Mitigation | Evidence |
|---|---|---|
| Injected instructions in corpus alter answers (AIGG-LAB-02) | Red-team evals; corpus provenance review | `gate-results/evals.json`, POA&M |
| Leakage of internal configuration (AIGG-LAB-01) | Evals with canary detection | `gate-results/evals.json`, POA&M |
| Unsafe rendering of output (AIGG-LAB-03) | Evals; output encoding | `gate-results/evals.json`, POA&M |
| Cost/availability abuse (AIGG-LAB-04) | Unit test guard; request limits | `gate-results/pytest.xml`, POA&M |
| Wrong or invented rules (confabulation) | Answers cite sources; accuracy evals | `gate-results/evals.json` |
| Unapproved model swapped in | Registry policy gate + runtime refusal | `gate-results/policy.json` |
| Disparate outcomes across groups | **Not yet tested** — bias eval set required before production | Open |

## 5. Human oversight

Human-in-the-loop: a caseworker reviews every drafted note and makes the
determination. The assistant is instructed never to approve or deny, and an
eval checks it. Releases require AI governance board approval through the
`ai-high-impact` GitHub Environment; the approver is recorded in the evidence.

## 6. Monitoring and decommissioning

- Registry approval expires on `review_by`; the policy gate blocks after that date.
- Every release re-runs evals against the live model.
- To withdraw the model, set its registry `status` to anything but `approved`:
  CI blocks new releases and the running service refuses to start.

## 7. Sign-off

Recorded per release in `evidence/<version>/evidence.json` → `gates.human-approval`.
