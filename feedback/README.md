# Scene QR customer feedback round

Status: preparation complete; recruitment and live sessions not started.
No customer feedback has been collected. All participant details and outcomes
remain [TO CONFIRM]. This kit does not authorize outreach or public release.

## Round setup

- Published frontend URL: [TO CONFIRM]
- Accessible guest QR URL and printed station label: [TO CONFIRM]
- Approved test business/workspace and staff access: [TO CONFIRM]
- Owner/coordinator and session dates: [TO CONFIRM]
- Participants: [TO CONFIRM]; include people unfamiliar with Scene and people
  who actually handle guest requests. A small first round could include 3–5
  guests and two staff; this is a proposal, not recruited participants.
- Use an isolated test business or an explicitly approved test window. Never
  surprise an operating business with test requests. Use synthetic request text
  and no real customer contact, payment or sensitive information.
- Verify that participants can access the design. Repository deployment notes
  describe Sites as owner-private; a published design may still require access.
  Do not change sharing, hosting or permissions without scoped approval.
- Verify the guest page and authenticated staff queue connect to the same backend.
  If only a visual prototype is available, test comprehension/navigation and mark
  sending, staff receipt and completion UNTESTED. Do not simulate success as live.

## Run in order

1. Confirm the URL, test workspace, participants and access. Review the exact
   invitation in invitations.md; record recipient/destination/scope approval in
   config/APPROVALS.md before sending. No invitation has been sent.
2. Rehearse the test with synthetic local/test data. Check a station QR, staff
   queue access and receipt polling; stop if private data appears unexpectedly.
3. Use test-script.md, starting with unprompted comprehension. Ask the guest to
   try first; avoid explaining the intended solution before observing it.
4. Record results in sessions.csv. Treat assistance, mistakes and failures as
   findings. Ask the short questions in survey.md after the task.
5. Add evidence-backed issues to findings.csv using session aliases and exact
   quotes only when consented. Keep identifying notes and consent privately.
6. Fix the most consequential repeated workflow issue, then rerun that task with
   fresh participants where possible. Do not publish claims of customer approval
   or success rates from invented, missing or synthetic evidence.

## Decision criteria

Assess three separate outcomes:
- Comprehension: can a guest explain what scanning lets them do?
- Handoff: does the request reach the correct business and show the correct
  table/chair/bay station without a staff member asking where it came from?
- Closure: can staff complete it and can the guest recognize the updated state?

Record each as independent / assisted / failed / not tested. Measure task time
only when directly observed; a wrong-station handoff or privacy leak blocks
acceptance regardless of speed. A participant saying they like the design does
not prove the operational flow works. Small qualitative rounds identify issues;
they do not establish representative adoption, ROI or statistical success rates.

## Privacy and evidence

Use aliases such as G01/S01, never guessed or fabricated people. Recording is
optional and requires explicit participant consent. Avoid capturing dashboards
with real requests, credentials, emails, receipt tokens or QR secrets. Collect
only what is needed; keep recordings/identities outside this public repository.
Agree retention/deletion privately before collecting anything. CSV files in this
kit contain headers only; do not commit real responses or customer information.
