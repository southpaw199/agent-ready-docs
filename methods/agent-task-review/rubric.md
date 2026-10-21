# Rubric

Use these values in the `outcome` and `root_cause` columns of the run log, so results can be compared across case studies.

## Outcome

| Value | Meaning |
| --- | --- |
| `pass` | The agent completed the task and the result met every success criterion, with no hints. |
| `pass-with-hints` | The agent completed the task after one or more hints. Record the count in `hints_given`. |
| `fail` | The agent could not complete the task, or its result did not meet the success criteria. |

## Root cause

Record the main reason for each stall, hint, or failure. Leave it blank for a clean `pass`.

| Value | The docs... |
| --- | --- |
| `missing-prerequisite` | Didn't state something required before starting: a version, package, account, key, or setting. |
| `ambiguous-instruction` | Gave a step that could reasonably be read more than one way. |
| `incomplete-example` | Showed code that doesn't run as written: missing imports, data, or setup. |
| `missing-error-guidance` | Didn't explain an error the agent hit, or how to recover from it. |
| `discoverability` | Had the answer, but on a page the agent couldn't find from the entry point. |
| `outdated-content` | Described an API or behavior that no longer matches the product. |
| `product-defect` | Weren't the cause: the product itself misbehaved. Report separately from docs findings. |
| `other` | None of the above. Explain in `notes`. |
