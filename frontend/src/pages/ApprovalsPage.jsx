import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserCheck, CheckCircle2, XCircle, FileText, Landmark, ShieldAlert } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { POLICIES } from '../mock/mock';
import { toast } from 'sonner';

export default function ApprovalsPage() {
  const { requests, decideApproval, roleId, setRoleId } = useApp();
  const navigate = useNavigate();
  const [reasons, setReasons] = useState({});
  const pending = requests.filter((r) => r.status === 'awaiting_approval');
  const decided = requests.filter((r) => r.decision);
  const isApprover = roleId === 'approver';

  const decide = async (req, decision) => {
    const reason = reasons[req.id] || (decision === 'approve' ? 'Enrollment verified; purpose legitimate per POL-CERT §4.1' : '');
    try {
      await decideApproval(req.id, decision, reason);
      toast(decision === 'approve' ? 'Approved — record persisted & audit event written' : 'Rejected — decision recorded in ledger', {
        description: `${req.id} · decision by Dr. R. Mishra`,
      });
    } catch (e) {
      toast('Decision failed', { description: 'Backend rejected the action — please retry.' });
    }
  };

  return (
    <div className="max-w-[1000px] mx-auto animate-fade-up">
      <div className="mt-6 mb-6">
        <h1 className="text-5xl font-light tracking-tight">Approvals</h1>
        <p className="text-[13px] text-[#8a8578] mt-3">Consequential actions pause here for a named human. Nothing HIGH-risk executes silently.</p>
      </div>

      {!isApprover && (
        <div className="bg-[#F5D34B]/30 border border-[#F5D34B] rounded-3xl p-5 mb-5 flex flex-wrap items-center justify-between gap-3" data-testid="approver-gate-banner">
          <p className="flex items-center gap-2 text-[13px] font-semibold"><ShieldAlert size={16} /> You are viewing as a non-approver role. Decisions require the Academic Approver.</p>
          <button onClick={() => setRoleId('approver')} data-testid="switch-to-approver-btn" className="bg-[#151515] text-white rounded-full px-5 py-2.5 text-[12px] font-semibold hover:bg-[#262626] transition-colors">Switch to Dr. R. Mishra</button>
        </div>
      )}

      {pending.length === 0 && (
        <div className="bg-[#FBF9F4] rounded-3xl p-10 text-center shadow-sm">
          <UserCheck size={28} className="mx-auto text-[#8a8578] mb-3" />
          <p className="text-[14px] font-semibold">No approvals pending</p>
          <p className="text-[12px] text-[#8a8578] mt-1">Submit a certificate request from Intake to create a HIGH-risk approval.</p>
          <button onClick={() => navigate('/intake')} className="mt-4 bg-[#151515] text-white rounded-full px-5 py-2.5 text-[12px] font-semibold hover:bg-[#262626] transition-colors">Open Intake</button>
        </div>
      )}

      <div className="space-y-4">
        {pending.map((req) => {
          const ev = req.evidence[0];
          const pol = POLICIES.find((p) => p.id === ev?.policy);
          const sec = pol?.sections.find((s) => s.ref === ev?.ref) || pol?.sections[0];
          return (
            <div key={req.id} className="bg-[#FBF9F4] rounded-3xl p-6 shadow-sm" data-testid={`approval-card-${req.id}`}>
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-3">
                  <span className="w-10 h-10 rounded-full bg-[#151515] text-[#F5D34B] flex items-center justify-center text-[11px] font-bold">{(req.requester || 'S')[0]}</span>
                  <div>
                    <p className="text-[14px] font-bold">{req.typeLabel} · {req.id}</p>
                    <p className="text-[11px] text-[#8a8578]">Requested by {req.requester} · {req.unit}</p>
                  </div>
                </div>
                <span className="text-[11px] font-bold bg-[#151515] text-white rounded-full px-3 py-1.5">HIGH RISK · step 4 of {req.plan.length}</span>
              </div>

              <div className="grid md:grid-cols-2 gap-3 mb-4">
                <div className="bg-white rounded-2xl p-4">
                  <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-[#8a8578] mb-2"><FileText size={12} /> Requested action diff</p>
                  <p className="text-[12px] bg-[#F2D5D2]/60 rounded-lg px-3 py-2 mb-1.5"><span className="font-bold">−</span> {req.diff?.before}</p>
                  <p className="text-[12px] bg-[#E4F2CF] rounded-lg px-3 py-2"><span className="font-bold">+</span> {req.diff?.after}</p>
                </div>
                <div className="bg-white rounded-2xl p-4">
                  <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-[#8a8578] mb-2"><Landmark size={12} /> Policy evidence</p>
                  <p className="text-[11px] font-bold">{pol?.title} <span className="font-medium text-[#8a8578]">{pol?.version} · {ev?.ref}</span></p>
                  <p className="text-[12px] text-[#5a5648] mt-1.5 leading-relaxed">“{sec?.text}”</p>
                </div>
              </div>

              <textarea value={reasons[req.id] || ''} onChange={(e) => setReasons((r) => ({ ...r, [req.id]: e.target.value }))} data-testid={`approval-reason-${req.id}`}
                placeholder="Decision reason (recorded in the audit ledger)…"
                className="w-full bg-white rounded-2xl p-3.5 text-[13px] outline-none focus:ring-2 focus:ring-[#F5D34B] transition-shadow resize-none min-h-[64px] placeholder:text-[#b5b0a3] mb-4" />

              <div className="flex flex-wrap gap-3">
                <button onClick={() => decide(req, 'approve')} disabled={!isApprover} data-testid={`approve-btn-${req.id}`}
                  className="flex items-center gap-2 bg-[#151515] text-white rounded-full px-6 py-3 text-[13px] font-semibold hover:bg-[#262626] transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                  <CheckCircle2 size={15} /> Approve & execute
                </button>
                <button onClick={() => decide(req, 'reject')} disabled={!isApprover} data-testid={`reject-btn-${req.id}`}
                  className="flex items-center gap-2 bg-white border border-[#151515]/15 rounded-full px-6 py-3 text-[13px] font-semibold hover:border-[#8a2f27] hover:text-[#8a2f27] transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                  <XCircle size={15} /> Reject
                </button>
                <button onClick={() => navigate(`/requests/${req.id}`)} className="ml-auto text-[12px] font-semibold underline underline-offset-4 hover:text-[#5a4a08]">View full plan</button>
              </div>
            </div>
          );
        })}
      </div>

      {decided.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-3">Decision history</h3>
          <div className="space-y-2">
            {decided.map((r) => (
              <button key={r.id} onClick={() => navigate(`/requests/${r.id}`)} data-testid={`decision-row-${r.id}`} className="w-full flex flex-wrap items-center gap-3 bg-[#FBF9F4] rounded-2xl p-4 text-left hover:shadow-md transition-shadow">
                <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${r.decision.decision === 'APPROVED' ? 'bg-[#E4F2CF] text-[#3d5a1e]' : 'bg-[#F2D5D2] text-[#8a2f27]'}`}>{r.decision.decision}</span>
                <span className="text-[13px] font-semibold">{r.typeLabel} · {r.id}</span>
                {r.recordId && <span className="text-[12px] font-bold text-[#5a4a08]">→ {r.recordId}</span>}
                <span className="text-[11px] text-[#8a8578] ml-auto">by {r.decision.by} · “{r.decision.reason || 'no reason recorded'}”</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
