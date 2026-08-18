// SOA mock seed data — replaced by Supabase backend in Phase 2

export const ROLES = [
  { id: 'requester', name: 'Ananya Sahoo', first: 'Ananya', title: 'Requester · Student', dept: 'CSE, 3rd Year' },
  { id: 'approver', name: 'Dr. R. Mishra', first: 'Dr. Mishra', title: 'Academic Approver', dept: 'Office of Academic Records' },
  { id: 'operator', name: 'S. Behera', first: 'Sasmita', title: 'Unit Operator', dept: 'Facilities & Lab Services' },
  { id: 'auditor', name: 'K. Das', first: 'Kabir', title: 'Institutional Auditor', dept: 'Governance Cell' },
];

export const POLICIES = [
  {
    id: 'POL-CERT', title: 'Certificate Issuance Policy', version: 'v2.1', effective: '2025-01-10',
    unit: 'Academic Records', accessClass: 'Internal', hash: '9f3a41bc77de02aa',
    sections: [
      { ref: '§3.2 · p.4', text: 'Bonafide and enrollment certificates require verification of active enrollment status and a named Academic Approver sign-off prior to issuance. Issuance without approval is prohibited.' },
      { ref: '§4.1 · p.6', text: 'Every certificate request must state its purpose (visa, scholarship, bank, internship). Purpose is recorded on the issued document and in the audit trail.' },
    ],
  },
  {
    id: 'POL-MAINT', title: 'Maintenance & Safety SOP', version: 'v1.4', effective: '2024-11-02',
    unit: 'Facilities', accessClass: 'Internal', hash: 'c21b88e14fa93d07',
    sections: [
      { ref: '§2.5 · p.3', text: 'Water leakage near electrical equipment is a Class-B safety hazard. Tickets are auto-created at LOW autonomy risk and dispatched to the zone crew within 30 minutes.' },
      { ref: '§3.1 · p.5', text: 'Requests reporting a risk of injury are tagged SAFETY and prioritised above routine maintenance in the unit queue.' },
    ],
  },
  {
    id: 'POL-LAB', title: 'Laboratory Booking Policy', version: 'v3.0', effective: '2025-02-15',
    unit: 'Laboratory Services', accessClass: 'Internal', hash: '4d7e90aa12bc55f3',
    sections: [
      { ref: '§5.1 · p.7', text: 'Laboratory bookings outside working hours (18:00–08:00) are NOT permitted for students under any circumstances.' },
      { ref: '§2.2 · p.2', text: 'Bookings within working hours may be auto-confirmed as a draft when the slot is free and equipment requirements are standard.' },
    ],
  },
  {
    id: 'POL-EMRG', title: 'Emergency Laboratory Access Circular', version: 'v1.0', effective: '2025-06-01',
    unit: 'Dean of Research', accessClass: 'Internal', hash: 'e08c33d19ab647f2', newer: true,
    sections: [
      { ref: '§1.2 · p.1', text: 'During examination weeks, supervised laboratory access MAY be granted at any hour, including outside working hours, with faculty supervision.' },
    ],
    conflictsWith: { policy: 'POL-LAB', ref: '§5.1 · p.7' },
  },
  {
    id: 'POL-GRV', title: 'Anonymous Grievance SOP', version: 'v2.0', effective: '2025-03-20',
    unit: 'Student Welfare', accessClass: 'Restricted', hash: '71fa02be48cd93e6',
    sections: [
      { ref: '§6.3 · p.9', text: 'Identity of anonymous complainants is stored in a restricted escrow vault. Unit operators receive only a pseudonymous case file. Vault access requires auditor role and a logged justification.' },
      { ref: '§7.1 · p.11', text: 'Grievances marked CRITICAL require human triage within 2 hours and cannot be closed autonomously.' },
    ],
  },
];

// ---- Seeded service requests ----
export const SEED_REQUESTS = [
  {
    id: 'REQ-1042', type: 'maintenance', typeLabel: 'Maintenance', createdAt: '2025-07-08T09:12:00Z',
    lang: 'hi', langLabel: 'Hindi',
    original: 'लैब 201 में AC से पानी लीक हो रहा है, छात्र फिसल सकते हैं।',
    normalized: 'Water is leaking from the AC unit in Lab 201; students may slip. Safety hazard reported.',
    requester: 'Ananya Sahoo', anonymous: false,
    intent: 'maintenance.report', risk: 'LOW', autonomy: 'AUTO-EXECUTED', status: 'completed',
    unit: 'Facilities · Zone B', recordId: 'MT-2214', recordLabel: 'Maintenance Ticket',
    fields: { location: 'Lab 201, Block C', asset: 'Split AC unit', category: 'Plumbing / HVAC', severity: 'High (safety)', hazard: 'Slip risk' },
    evidence: [ { policy: 'POL-MAINT', ref: '§2.5 · p.3' }, { policy: 'POL-MAINT', ref: '§3.1 · p.5' } ],
    conflict: null,
    plan: [
      { n: 1, title: 'Detect language & normalize request', tool: 'interpret.normalize', actor: 'SOA Agent', risk: 'LOW', status: 'done', output: 'hi → en · intent maintenance.report' },
      { n: 2, title: 'Extract location, asset, severity', tool: 'interpret.extract_fields', actor: 'SOA Agent', risk: 'LOW', status: 'done', output: 'Lab 201 · AC unit · SAFETY tag' },
      { n: 3, title: 'Retrieve maintenance policy evidence', tool: 'evidence.retrieve', actor: 'Evidence Engine', risk: 'LOW', status: 'done', output: 'POL-MAINT §2.5 cited · no conflict' },
      { n: 4, title: 'Classify autonomy risk', tool: 'risk.classify', actor: 'Risk Gate', risk: 'LOW', status: 'done', output: 'LOW → auto-execution permitted' },
      { n: 5, title: 'Create maintenance ticket', tool: 'tools.create_ticket', actor: 'Orchestrator', risk: 'LOW', status: 'done', output: 'Ticket MT-2214 → Facilities Zone B' },
    ],
  },
  {
    id: 'REQ-1043', type: 'certificate', typeLabel: 'Certificate', createdAt: '2025-07-08T10:02:00Z',
    lang: 'en', langLabel: 'English',
    original: 'I need a bonafide certificate for my education loan application at SBI, required by Friday.',
    normalized: 'Bonafide certificate requested for education-loan purpose (SBI). Deadline: Friday.',
    requester: 'Ananya Sahoo', anonymous: false,
    intent: 'certificate.issue', risk: 'HIGH', autonomy: 'AWAITING APPROVAL', status: 'awaiting_approval',
    unit: 'Academic Records', recordId: null, recordLabel: 'Certificate Request',
    approver: 'Dr. R. Mishra · Academic Approver',
    fields: { certificateType: 'Bonafide', purpose: 'Education loan (SBI)', program: 'B.Tech CSE', enrollment: 'Verified · Active', deadline: 'Friday' },
    evidence: [ { policy: 'POL-CERT', ref: '§3.2 · p.4' }, { policy: 'POL-CERT', ref: '§4.1 · p.6' } ],
    conflict: null,
    diff: { action: 'ISSUE_CERTIFICATE', before: 'No certificate on record for purpose "Education loan (SBI)"', after: 'Bonafide certificate issued · purpose recorded · notified to requester' },
    plan: [
      { n: 1, title: 'Normalize request & detect intent', tool: 'interpret.normalize', actor: 'SOA Agent', risk: 'LOW', status: 'done', output: 'en · intent certificate.issue' },
      { n: 2, title: 'Verify enrollment status', tool: 'tools.verify_enrollment', actor: 'Orchestrator', risk: 'LOW', status: 'done', output: 'Active enrollment confirmed' },
      { n: 3, title: 'Retrieve certificate policy evidence', tool: 'evidence.retrieve', actor: 'Evidence Engine', risk: 'LOW', status: 'done', output: 'POL-CERT §3.2 requires named approver' },
      { n: 4, title: 'Issue bonafide certificate', tool: 'tools.issue_certificate', actor: 'Dr. R. Mishra', risk: 'HIGH', status: 'blocked', output: 'Paused — awaiting Academic Approver decision' },
      { n: 5, title: 'Notify requester & write audit event', tool: 'tools.notify', actor: 'Orchestrator', risk: 'LOW', status: 'pending', output: '—' },
    ],
  },
  {
    id: 'REQ-1044', type: 'lab_booking', typeLabel: 'Lab Booking', createdAt: '2025-07-08T11:20:00Z',
    lang: 'en', langLabel: 'English',
    original: 'Book Physics Lab 3 tonight at 9pm for my project demo, it is exam week so it should be allowed.',
    normalized: 'Lab booking requested: Physics Lab 3, 21:00 (outside working hours), justification: examination week.',
    requester: 'Ananya Sahoo', anonymous: false,
    intent: 'lab.book', risk: 'ABSTAINED', autonomy: 'ABSTAINED', status: 'abstained',
    unit: 'Laboratory Coordinator', recordId: null, recordLabel: 'Lab Booking',
    fields: { lab: 'Physics Lab 3', slot: '21:00 – 23:00', date: 'Today', context: 'Examination week' },
    evidence: [ { policy: 'POL-LAB', ref: '§5.1 · p.7' }, { policy: 'POL-EMRG', ref: '§1.2 · p.1' } ],
    conflict: { code: 'CONFLICT_DETECTED', a: { policy: 'POL-LAB', ref: '§5.1 · p.7', stance: 'Prohibits student bookings 18:00–08:00' }, b: { policy: 'POL-EMRG', ref: '§1.2 · p.1', stance: 'Permits supervised access at any hour during exam weeks' }, routedTo: 'Laboratory Coordinator' },
    plan: [
      { n: 1, title: 'Normalize request & detect intent', tool: 'interpret.normalize', actor: 'SOA Agent', risk: 'LOW', status: 'done', output: 'en · intent lab.book' },
      { n: 2, title: 'Check slot availability', tool: 'tools.check_availability', actor: 'Orchestrator', risk: 'LOW', status: 'done', output: 'Physics Lab 3 free at 21:00' },
      { n: 3, title: 'Retrieve booking policy evidence', tool: 'evidence.retrieve', actor: 'Evidence Engine', risk: 'LOW', status: 'done', output: '2 passages retrieved · contradiction found' },
      { n: 4, title: 'Resolve policy conflict', tool: 'risk.conflict_check', actor: 'Risk Gate', risk: 'HIGH', status: 'abstained', output: 'CONFLICT_DETECTED → abstain, route to human' },
      { n: 5, title: 'Create booking', tool: 'tools.create_booking', actor: 'Orchestrator', risk: 'MEDIUM', status: 'cancelled', output: 'Not executed — abstention' },
    ],
  },
  {
    id: 'REQ-1045', type: 'grievance', typeLabel: 'Grievance', createdAt: '2025-07-08T13:45:00Z',
    lang: 'en', langLabel: 'English',
    original: '[Anonymous] Repeated ragging incidents in Hostel Block D common room after 10pm. I am afraid to report openly.',
    normalized: 'Anonymous grievance: repeated ragging incidents, Hostel Block D common room, after 22:00. Complainant fears retaliation.',
    requester: 'CASE-KOEL-7', anonymous: true, pseudonym: 'CASE-KOEL-7',
    intent: 'grievance.file', risk: 'HIGH', autonomy: 'HUMAN TRIAGE', status: 'in_triage',
    unit: 'Student Welfare · Anti-Ragging Cell', recordId: 'GRV-0931', recordLabel: 'Grievance Case',
    urgency: 'CRITICAL',
    fields: { location: 'Hostel Block D, common room', pattern: 'Repeated, after 22:00', category: 'Ragging / harassment', urgency: 'Critical' },
    evidence: [ { policy: 'POL-GRV', ref: '§6.3 · p.9' }, { policy: 'POL-GRV', ref: '§7.1 · p.11' } ],
    conflict: null,
    plan: [
      { n: 1, title: 'Accept anonymous submission', tool: 'interpret.normalize', actor: 'SOA Agent', risk: 'LOW', status: 'done', output: 'Identity moved to escrow vault' },
      { n: 2, title: 'Create pseudonymous case file', tool: 'tools.create_grievance', actor: 'Orchestrator', risk: 'MEDIUM', status: 'done', output: 'GRV-0931 · pseudonym CASE-KOEL-7' },
      { n: 3, title: 'Classify urgency', tool: 'risk.classify', actor: 'Risk Gate', risk: 'HIGH', status: 'done', output: 'CRITICAL → human triage within 2h (POL-GRV §7.1)' },
      { n: 4, title: 'Route to Anti-Ragging Cell', tool: 'tools.route_case', actor: 'Orchestrator', risk: 'LOW', status: 'done', output: 'Escalated · operator sees pseudonym only' },
      { n: 5, title: 'Human triage decision', tool: 'human.triage', actor: 'Student Welfare Officer', risk: 'HIGH', status: 'active', output: 'In progress' },
    ],
  },
  {
    id: 'REQ-1046', type: 'lab_booking', typeLabel: 'Lab Booking', createdAt: '2025-07-08T15:05:00Z',
    lang: 'od', langLabel: 'Odia',
    original: 'ଆସନ୍ତାକାଲି ସକାଳ ୧୦ଟାରେ କେମିଷ୍ଟ୍ରି ଲାବ୍ ୨ ବୁକ୍ କରନ୍ତୁ।',
    normalized: 'Book Chemistry Lab 2 tomorrow at 10:00 (within working hours), standard equipment.',
    requester: 'Ananya Sahoo', anonymous: false,
    intent: 'lab.book', risk: 'MEDIUM', autonomy: 'AUTO-DRAFT', status: 'completed',
    unit: 'Laboratory Services', recordId: 'LAB-BKG-0507', recordLabel: 'Lab Booking Draft',
    fields: { lab: 'Chemistry Lab 2', slot: '10:00 – 12:00', date: 'Tomorrow', equipment: 'Standard' },
    evidence: [ { policy: 'POL-LAB', ref: '§2.2 · p.2' } ],
    conflict: null,
    plan: [
      { n: 1, title: 'Detect language & normalize', tool: 'interpret.normalize', actor: 'SOA Agent', risk: 'LOW', status: 'done', output: 'od → en · intent lab.book' },
      { n: 2, title: 'Check slot availability', tool: 'tools.check_availability', actor: 'Orchestrator', risk: 'LOW', status: 'done', output: 'Slot free · working hours' },
      { n: 3, title: 'Retrieve booking policy evidence', tool: 'evidence.retrieve', actor: 'Evidence Engine', risk: 'LOW', status: 'done', output: 'POL-LAB §2.2 permits auto-draft' },
      { n: 4, title: 'Create draft booking', tool: 'tools.create_booking', actor: 'Orchestrator', risk: 'MEDIUM', status: 'done', output: 'LAB-BKG-0507 created' },
    ],
  },
];

// Seed audit payloads — hashes are chained at runtime by AppContext
export const SEED_AUDIT = [
  { id: 'EVT-0001', requestId: 'REQ-1042', ts: '2025-07-08T09:12:04Z', actor: 'SOA Agent', role: 'system', action: 'interpret.normalize', summary: 'Hindi request normalized to English · intent maintenance.report', policyRefs: [], approval: null },
  { id: 'EVT-0002', requestId: 'REQ-1042', ts: '2025-07-08T09:12:09Z', actor: 'Risk Gate', role: 'system', action: 'risk.classify', summary: 'Classified LOW · auto-execution permitted', policyRefs: ['POL-MAINT §2.5'], approval: null },
  { id: 'EVT-0003', requestId: 'REQ-1042', ts: '2025-07-08T09:12:15Z', actor: 'Orchestrator', role: 'system', action: 'tools.create_ticket', summary: 'Maintenance ticket MT-2214 created → Facilities Zone B', policyRefs: ['POL-MAINT §2.5'], approval: null },
  { id: 'EVT-0004', requestId: 'REQ-1043', ts: '2025-07-08T10:02:11Z', actor: 'SOA Agent', role: 'system', action: 'interpret.normalize', summary: 'Certificate request parsed · purpose education loan', policyRefs: [], approval: null },
  { id: 'EVT-0005', requestId: 'REQ-1043', ts: '2025-07-08T10:02:18Z', actor: 'Risk Gate', role: 'system', action: 'risk.classify', summary: 'Classified HIGH · paused for Academic Approver', policyRefs: ['POL-CERT §3.2'], approval: 'PENDING' },
  { id: 'EVT-0006', requestId: 'REQ-1044', ts: '2025-07-08T11:20:22Z', actor: 'Evidence Engine', role: 'system', action: 'evidence.retrieve', summary: 'Two contradictory passages retrieved (POL-LAB vs POL-EMRG)', policyRefs: ['POL-LAB §5.1', 'POL-EMRG §1.2'], approval: null },
  { id: 'EVT-0007', requestId: 'REQ-1044', ts: '2025-07-08T11:20:27Z', actor: 'Risk Gate', role: 'system', action: 'risk.conflict_check', summary: 'CONFLICT_DETECTED → abstained · routed to Laboratory Coordinator', policyRefs: ['POL-LAB §5.1', 'POL-EMRG §1.2'], approval: null },
  { id: 'EVT-0008', requestId: 'REQ-1045', ts: '2025-07-08T13:45:30Z', actor: 'Orchestrator', role: 'system', action: 'tools.create_grievance', summary: 'Pseudonymous case GRV-0931 created · identity escrowed', policyRefs: ['POL-GRV §6.3'], approval: null },
  { id: 'EVT-0009', requestId: 'REQ-1045', ts: '2025-07-08T13:45:36Z', actor: 'Orchestrator', role: 'system', action: 'tools.route_case', summary: 'CRITICAL urgency → Anti-Ragging Cell · human triage required', policyRefs: ['POL-GRV §7.1'], approval: null },
  { id: 'EVT-0010', requestId: 'REQ-1046', ts: '2025-07-08T15:05:12Z', actor: 'Orchestrator', role: 'system', action: 'tools.create_booking', summary: 'Draft booking LAB-BKG-0507 created (working hours)', policyRefs: ['POL-LAB §2.2'], approval: null },
];

export const JUDGE_SCENARIOS = [
  { t: '0:00 – 0:45', title: 'Hindi voice → safety maintenance', desc: 'Speak (or simulate) a Hindi request about AC water leaking in Lab 201. Watch live transcript, language detection, normalization and the safety policy citation.', route: '/intake', cta: 'Open Intake', sample: 'hi' },
  { t: '0:45 – 1:30', title: 'LOW-risk auto execution', desc: 'The maintenance flow classifies LOW risk, auto-creates ticket MT-2214, routes to Facilities Zone B and writes a hash-chained audit event.', route: '/requests/REQ-1042', cta: 'Open Plan Canvas', sample: null },
  { t: '1:30 – 2:20', title: 'HIGH-risk certificate pauses', desc: 'A bonafide certificate reaches a consequential step. The plan pauses at step 4 with a named approver, policy excerpt and a requested-action diff.', route: '/requests/REQ-1043', cta: 'View Paused Plan', sample: null },
  { t: '2:20 – 3:10', title: 'Named human approves', desc: 'Switch role to Approver, record a reasoned decision, and watch the certificate request ID persist with a linked audit event.', route: '/approvals', cta: 'Open Approvals', sample: null },
  { t: '3:10 – 4:00', title: 'Anonymous critical grievance', desc: 'Identity goes to a restricted escrow vault; operators see only pseudonym CASE-KOEL-7. Critical urgency forces human triage.', route: '/grievances', cta: 'Open Grievances', sample: null },
  { t: '4:00 – 4:40', title: 'Policy conflict → abstention', desc: 'Two contradictory lab-access passages trigger CONFLICT_DETECTED. SOA abstains instead of guessing and routes to the Laboratory Coordinator.', route: '/requests/REQ-1044', cta: 'View Abstention', sample: null },
  { t: '4:40 – 5:00', title: 'Verify, replay & compensate', desc: 'Verify the tamper-evident hash chain, replay a request read-only, and roll back via a compensating event — history is never rewritten.', route: '/audit', cta: 'Open Audit Ledger', sample: null },
];

export const VOICE_SAMPLES = {
  hi: { label: 'Hindi', text: 'लैब 201 में AC से पानी लीक हो रहा है, छात्र फिसल सकते हैं।' },
  en: { label: 'English', text: 'I need a bonafide certificate for my education loan application at SBI, required by Friday.' },
  od: { label: 'Odia', text: 'ଆସନ୍ତାକାଲି ସକାଳ ୧୦ଟାରେ କେମିଷ୍ଟ୍ରି ଲାବ୍ ୨ ବୁକ୍ କରନ୍ତୁ।' },
};

export const CHART_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'];
export const CHART_AUTO =   [96, 82, 118, 74, 128, 102, 152, 0, 0, 0, 0];
export const CHART_HUMAN =  [44, 58, 39, 66, 52, 71, 63, 0, 0, 0, 0];
