# SOAIDEATHON-S1 — problem statement → screen

Judge walk: 5 minutes. Hosted app `https://soa-campus.vercel.app` (or local `http://localhost:3000`). Public — no Vercel login. Login as student first.

| PS sentence | What they see | Where |
|---|---|---|
| Understand service requests | Student talks or types in English / Hindi / Odia. Live LLM classifies intent + fields. Voice via Deepgram EN/HI. | Assistant `/assistant`, Intake `/intake` |
| Plan multi-step actions | Plan Canvas: policy search → tool steps, allowlisted only. | Request detail `/requests/:id` |
| Retrieve verified institutional info | Seeded policy RAG (POL-CERT / POL-MAINT / POL-LAB / POL-EMRG / POL-GRV) cited on the case. | Request detail + Policies |
| Route approvals | Bonafide pauses for Dr. R. Mishra. Role switcher → Approver. | Approvals `/approvals` |
| Execute 4 workflows | Leak → auto ticket. Certificate → gated. Daytime lab → draft. Grievance → triage + vault. | Assistant one-liners file and assign the desk |
| Auditable action trail | SHA-256 hash chain. Verify / tamper / rollback. Header bell is live ledger. | Audit `/audit` |
| Human approval before consequential acts | Engine never runs `certificate.generate` until Mishra signs. Vault needs auditor + justification. | Approvals + Grievances |
| Multilingual | Replies in the student's language. UI stays English. Odia voice is labeled demo. | Assistant |
| Detect uncertainty / policy conflict, do not fabricate | Exam-week night lab **abstains** (POL-LAB vs POL-EMRG). Unknown intent asks a follow-up. | Intake chip “Book Physics Lab 3 tonight…” or seeded REQ-1044 |
| Secure platform | Demo JWT + RBAC. Identity escrow for anonymous grievances. Keys only in gitignored `.env`. | Grievances vault |

Scripted path (do this, in order):

1. Student: “AC leaking in Lab 201” → auto maintenance ticket.
2. Student: “I need a bonafide for my visa” → blocks → switch to Mishra → approve.
3. “Book Physics Lab 3 tonight, exam week” → abstain, two policy cites, no fake booking.
4. Anonymous grievance → switch to K. Das → vault unlock with justification.
5. Audit → verify chain.
