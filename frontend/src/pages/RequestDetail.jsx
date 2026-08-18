import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, CircleCheck, CircleDashed, CirclePause, CircleX, CircleAlert, FileText, Fingerprint, GitBranch, Landmark, TriangleAlert, Ticket, Mic, MessageCircle, SendHorizonal, Loader2 } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { POLICIES } from '../mock/mock';
import { toast } from 'sonner';

const STEP_ICON = {
  done: [CircleCheck, 'text-[#6a8f2f]', 'bg-[#E4F2CF]'],
  active: [CircleDashed, 'text-[#2c4a72] animate-spin-slow', 'bg-[#DCE7F5]'],
  blocked: [CirclePause, 'text-[#5a4a08]', 'bg-[#F5D34B]'],
  pending: [CircleDashed, 'text-[#b5b0a3]', 'bg-[#efece3]'],
  abstained: [CircleAlert, 'text-[#7a4a22]', 'bg-[#EAD9CB]'],
  cancelled: [CircleX, 'text-[#8a2f27]', 'bg-[#F2D5D2]'],
};

const riskCls = { LOW: 'bg-[#E4F2CF] text-[#3d5a1e]', MEDIUM: 'bg-[#F5D34B]/60 text-[#5a4a08]', HIGH: 'bg-[#151515] text-white', ABSTAINED: 'bg-[#EAD9CB] text-[#7a4a22]' };

export default function RequestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { requests, audit, sendMessage } = useApp();
  const [msgText, setMsgText] = useState('');
  const [sending, setSending] = useState(false);
  const req = requests.find((r) => r.id === id);
  if (!req) return <div className="max-w-[1100px] mx-auto mt-10 text-center text-[#8a8578]">Request not found. <Link className="underline" to="/requests">Back to requests</Link></div>;
  const events = audit.filter((e) => e.requestId === req.id);

  const submitMsg = async () => {
    if (!msgText.trim() || sending) return;
    setSending(true);
    try {
      await sendMessage(req.id, msgText.trim());
      setMsgText('');
    } catch (e) {
      toast('Message failed', { description: 'Backend unreachable — please retry.' });
    }
    setSending(false);
  };

  return (
    <div className="max-w-[1160px] mx-auto animate-fade-up">
      <button onClick={() => navigate(-1)} data-testid="back-btn" className="flex items-center gap-2 text-[13px] text-[#8a8578] hover:text-[#151515] transition-colors mt-4 mb-5"><ArrowLeft size={15} /> Back</button>

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <span className="text-[11px] font-bold bg-white rounded-full px-3 py-1">{req.id}</span>
            <span className={`text-[11px] font-bold rounded-full px-3 py-1 ${riskCls[req.risk]}`}>{req.risk === 'ABSTAINED' ? 'ABSTAINED' : `${req.risk} RISK`}</span>
            <span className="text-[11px] font-semibold bg-[#151515] text-[#F5D34B] rounded-full px-3 py-1">{req.autonomy}</span>
            {req.viaVoice && <span className="text-[11px] bg-white rounded-full px-3 py-1 flex items-center gap-1"><Mic size={11} /> voice</span>}
          </div>
          <h1 className="text-4xl font-light tracking-tight">{req.typeLabel} <span className="text-[#b5b0a3]">· {req.langLabel}</span></h1>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <button onClick={() => navigate(`/requests/${req.id}/report`)} data-testid="open-report-btn"
            className="flex items-center gap-2 bg-[#151515] text-white rounded-full px-5 py-3 text-[13px] font-semibold hover:bg-[#262626] transition-colors">
            <FileText size={15} /> Print report
          </button>
          {req.recordId && (
            <div className="bg-[#F5D34B] rounded-2xl px-5 py-3.5 shadow-sm" data-testid="record-id-badge">
              <p className="text-[10px] font-bold uppercase tracking-widest text-[#5a4a08]">{req.recordLabel} · persisted</p>
              <p className="text-2xl font-bold flex items-center gap-2"><Ticket size={18} /> {req.recordId}</p>
            </div>
          )}
        </div>
      </div>

      {/* Conflict banner */}
      {req.conflict && (
        <div className="bg-[#EAD9CB] border border-[#7a4a22]/20 rounded-3xl p-5 mb-4" data-testid="conflict-banner">
          <p className="flex items-center gap-2 font-bold text-[#7a4a22] mb-3"><TriangleAlert size={17} /> {req.conflict.code} — SOA abstained instead of guessing</p>
          <div className="grid md:grid-cols-2 gap-3">
            {[req.conflict.a, req.conflict.b].map((c, i) => {
              const pol = POLICIES.find((p) => p.id === c.policy);
              return (
                <div key={i} className="bg-white/70 rounded-2xl p-4">
                  <p className="text-[11px] font-bold">{pol?.title} <span className="text-[#8a8578] font-medium">{pol?.version} · {c.ref}</span></p>
                  <p className="text-[12px] text-[#5a5648] mt-1.5">“{c.stance}”</p>
                </div>
              );
            })}
          </div>
          <p className="text-[12px] text-[#7a4a22] mt-3">Routed to a named human: <strong>{req.conflict.routedTo}</strong></p>
        </div>
      )}

      {req.followUp && (
        <div className="bg-[#DCE7F5] rounded-3xl p-5 mb-4" data-testid="followup-banner">
          <p className="text-[13px] font-semibold text-[#2c4a72]">Focused follow-up instead of guessing:</p>
          <p className="text-[14px] mt-1">“{req.followUp}”</p>
        </div>
      )}

      <div className="grid lg:grid-cols-12 gap-4">
        {/* Plan canvas */}
        <div className="lg:col-span-7 bg-[#FBF9F4] rounded-3xl p-6 shadow-sm">
          <h3 className="flex items-center gap-2 text-lg font-semibold mb-5"><GitBranch size={17} /> Plan Canvas</h3>
          <div className="relative">
            <span className="absolute left-[19px] top-3 bottom-3 w-px bg-[#151515]/10" />
            <div className="space-y-3">
              {req.plan.map((s) => {
                const [Icon, iconCls, bgCls] = STEP_ICON[s.status] || STEP_ICON.pending;
                return (
                  <div key={s.n} className="relative flex gap-4" data-testid={`plan-step-${s.n}`}>
                    <span className={`relative z-10 w-10 h-10 rounded-full ${bgCls} flex items-center justify-center shrink-0`}><Icon size={17} className={iconCls} /></span>
                    <div className={`flex-1 rounded-2xl p-4 transition-colors ${s.status === 'blocked' ? 'bg-[#F5D34B]/25 border border-[#F5D34B]' : 'bg-white'}`}>
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <p className="text-[13px] font-bold">{s.n}. {s.title}</p>
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${riskCls[s.risk]}`}>{s.risk}</span>
                      </div>
                      <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1.5 text-[11px] text-[#8a8578]">
                        <span>tool: <code className="text-[#151515]">{s.tool}</code></span>
                        <span>actor: {s.actor}</span>
                      </div>
                      <p className="text-[12px] mt-1.5 text-[#5a5648]">{s.output}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          {req.status === 'awaiting_approval' && (
            <button onClick={() => navigate('/approvals')} data-testid="goto-approvals-btn" className="mt-5 w-full bg-[#151515] text-white rounded-full py-3.5 text-[13px] font-semibold hover:bg-[#262626] transition-colors">
              Awaiting {req.approver} → open Approvals
            </button>
          )}
        </div>

        {/* Right column */}
        <div className="lg:col-span-5 space-y-4">
          {/* Request text */}
          <div className="bg-[#151515] text-white rounded-3xl p-5">
            <p className="text-[10px] uppercase tracking-widest text-white/40 mb-2">Original · {req.langLabel}</p>
            <p className="text-[14px] leading-relaxed">{req.original}</p>
            <div className="h-px bg-white/10 my-4" />
            <p className="text-[10px] uppercase tracking-widest text-[#F5D34B] mb-2">Normalized · English</p>
            <p className="text-[13px] text-white/80 leading-relaxed">{req.normalized}</p>
          </div>

          {/* Extracted fields */}
          {Object.keys(req.fields || {}).length > 0 && (
            <div className="bg-[#FBF9F4] rounded-3xl p-5 shadow-sm">
              <h4 className="flex items-center gap-2 text-[14px] font-semibold mb-3"><FileText size={15} /> Extracted fields</h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(req.fields).map(([k, v]) => (
                  <div key={k} className="bg-white rounded-xl p-3">
                    <p className="text-[10px] uppercase tracking-wide text-[#8a8578]">{k.replace(/([A-Z])/g, ' $1')}</p>
                    <p className="text-[12px] font-semibold mt-0.5">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence */}
          <div className="bg-[#FBF9F4] rounded-3xl p-5 shadow-sm">
            <h4 className="flex items-center gap-2 text-[14px] font-semibold mb-3"><Landmark size={15} /> Evidence citations</h4>
            {req.evidence.length === 0 && <p className="text-[12px] text-[#8a8578]">No evidence required — clarification stage.</p>}
            <div className="space-y-2.5">
              {req.evidence.map((ev, i) => {
                const pol = POLICIES.find((p) => p.id === ev.policy);
                const sec = pol?.sections.find((s) => s.ref === ev.ref) || pol?.sections[0];
                return (
                  <Link to="/policies" key={i} className="block bg-white rounded-2xl p-4 hover:ring-2 hover:ring-[#F5D34B] transition-shadow" data-testid={`evidence-${i}`}>
                    <div className="flex items-center justify-between flex-wrap gap-1">
                      <p className="text-[12px] font-bold">{pol?.title}</p>
                      <span className="text-[10px] bg-[#F1EDE3] rounded-full px-2 py-0.5">{pol?.version} · {ev.ref}</span>
                    </div>
                    <p className="text-[12px] text-[#5a5648] mt-1.5 leading-relaxed">“{sec?.text}”</p>
                    <p className="flex items-center gap-1.5 text-[10px] text-[#8a8578] mt-2"><Fingerprint size={11} /> provenance {pol?.hash}</p>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Case thread */}
          {((req.messages && req.messages.length > 0) || req.status === 'needs_info') && (
            <div className="bg-[#FBF9F4] rounded-3xl p-5 shadow-sm" data-testid="case-thread">
              <h4 className="flex items-center gap-2 text-[14px] font-semibold mb-3"><MessageCircle size={15} /> Case thread</h4>
              <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                {(req.messages || []).map((m) => (
                  <div key={m.id} className={`flex ${m.role === 'agent' ? 'justify-start' : 'justify-end'}`} data-testid={`thread-msg-${m.id}`}>
                    <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[12px] leading-relaxed ${m.role === 'agent' ? 'bg-[#151515] text-white' : 'bg-[#F5D34B]/50'}`}>
                      <p className={`text-[9px] font-bold uppercase tracking-wide mb-0.5 ${m.role === 'agent' ? 'text-[#F5D34B]' : 'text-[#8a8578]'}`}>{m.author}</p>
                      {m.text}
                    </div>
                  </div>
                ))}
                {sending && (
                  <div className="flex justify-start">
                    <div className="bg-[#151515] text-white rounded-2xl px-3.5 py-2.5 text-[12px] flex items-center gap-2">
                      <Loader2 size={12} className="animate-spin text-[#F5D34B]" /> SOA is re-evaluating…
                    </div>
                  </div>
                )}
              </div>
              {req.status === 'needs_info' && (
                <div className="flex items-center gap-2 mt-3">
                  <input value={msgText} onChange={(e) => setMsgText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submitMsg()}
                    data-testid="thread-input" placeholder="Answer the follow-up question…" disabled={sending}
                    className="flex-1 bg-white rounded-full px-4 py-2.5 text-[13px] outline-none focus:ring-2 focus:ring-[#F5D34B] transition-shadow placeholder:text-[#b5b0a3] disabled:opacity-50" />
                  <button onClick={submitMsg} disabled={!msgText.trim() || sending} data-testid="thread-send-btn"
                    className="bg-[#151515] text-white rounded-full p-2.5 hover:bg-[#262626] transition-colors disabled:opacity-40">
                    <SendHorizonal size={15} />
                  </button>
                </div>
              )}
              {req.status !== 'needs_info' && (req.messages || []).length > 0 && (
                <p className="text-[11px] text-[#8a8578] mt-3">Thread resolved — the request was reclassified and the governed plan executed.</p>
              )}
            </div>
          )}

          {/* Audit trail */}
          <div className="bg-[#FBF9F4] rounded-3xl p-5 shadow-sm">
            <h4 className="text-[14px] font-semibold mb-3">Audit events for this request</h4>
            <div className="space-y-2">
              {events.map((e) => (
                <div key={e.id} className="bg-white rounded-xl p-3">
                  <div className="flex justify-between items-center gap-2">
                    <p className="text-[11px] font-bold">{e.action}</p>
                    <code className="text-[9px] text-[#8a8578]">{e.hash?.slice(0, 12)}…</code>
                  </div>
                  <p className="text-[11px] text-[#5a5648] mt-0.5">{e.summary}</p>
                </div>
              ))}
              {events.length === 0 && <p className="text-[12px] text-[#8a8578]">Events appear once actions execute.</p>}
            </div>
            <Link to="/audit" className="block text-center text-[12px] font-semibold mt-3 underline underline-offset-4 hover:text-[#5a4a08]">Open full ledger</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
