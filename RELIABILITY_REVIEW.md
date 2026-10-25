# Scene QR — connection recovery review

The uploaded engineering-roadmap recording emphasizes testing, evaluation and production operation. This focused change applies those principles to the existing QR flow; it adds no AI pipeline, billing or new backend service.

## Changes

- Guest receipts now distinguish their last confirmed status from a failed status check. A visible warning explains the interruption and offers Check status again.
- Retrying checks existing private receipts only; it never resubmits requests. Successful checks clear the warning, update status and persist it.
- Receipt checks cannot overlap. A response for an abandoned QR token cannot update the current receipt view.
- The optional local-demo availability check no longer blocks restoring a real signed-in workspace.

## Evidence

| Flow | Evidence | Result |
| --- | --- | --- |
| Receipt connection loss | Actual preview browser at 375px; create local sample request, disconnect development API forwarding | Warning appears; last confirmed New remains |
| Recovery | Restore development forwarding, click Check status again | Warning clears; existing request remains New; no request is resubmitted |
| Concurrent/stale checks | Node regression with delayed response and QR change | Only one check runs; old QR response does not overwrite current view |
| Session startup | Node regression with indefinitely pending demo discovery | Real /api/me request still starts and resolves |
| Production readiness endpoint | Actual browser opens public Sites /readyz through existing Render proxy | {"ok":true} |
| Frontend checks | npm test | 60 pass |
| Backend baseline | /workspace/scene-test-env/bin/python -m pytest -q tests | 79 pass, 26 skipped; one dependency deprecation warning |
| Build | JS syntax check, npm run build, npm run validate | Pass |

Production authenticated owner actions, physical iPhone behavior, email delivery acceptance and field performance metrics were not tested in this pass. The production readiness endpoint establishes current backend readiness, not a complete commercial-launch certification. Stripe, POS and confirmed bookings remain outside this requests-only beta.
