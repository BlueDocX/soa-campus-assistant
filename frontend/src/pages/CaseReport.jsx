import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Printer, ShieldCheck, Fingerprint } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { POLICIES } from '../mock/mock';

const riskCls = { LOW: 'bg-[#E4F2CF] text-[#3d5a1e]', MEDIUM: 'bg-[#F5D34B]/60 text-[#5a4a08]', HIGH: 'bg-[#151515] text-white', ABSTAINED: 'bg-[#EAD9CB] text-[#7a4a22]' };

export default function CaseReport() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { requests, audit, loaded } = useApp();
  const req = requests.find((r) => r.id === id);
  if (!loaded) return null;
  if (!req) return <div className="max-w-[800px] mx-auto mt-10 text-center text-[#8a8578]">Request not found. <Link className="underline" to="/requests">Back</Link></div>;
  const events = audit.filter((e) => e.requestId === req.id);

  return (
    <div className="max-w-[820px] mx-auto animate-fade-up">
      {/* Toolbar (hidden in print) */}
      <div className="print-hide flex items-center justify-between mt-4 mb-4">
        <button onClick={() => navigate(`/requests/${req.id}`)} data-testid="report-back-btn" className="flex items-center gap-2 text-[13px] text-[#8a8578] hover:text-[#151515] transition-colors"><ArrowLeft size={15} /> Back to request</button>
        <button onClick={() => window.print()} data-testid="print-btn" className="flex items-center gap-2 bg-[#151515] text-white rounded-full px-6 py-3 text-[13px] font-semibold hover:bg-[#262626] transition-colors">
          <Printer size={15} /> Print report
        </button>
      </div>

      {/* Report sheet */}
      <div className="report-sheet bg-white rounded-3xl shadow-sm p-8 md:p-10 mb-10" data-testid="report-sheet">
        {/* Header */}
        <div className="flex items-start justify-between border-b-2 border-[#151515] pb-5 mb-6">
          <div>
            <p className="flex items-center gap-2 text-lg font-bold tracking-tight"><img src="/soa-logo.webp" alt="SOA logo" className="w-8 h-8 rounded-full object-contain" /> SOA</p>
            <p className="text-[11px] text-[#8a8578] mt-0.5">Governed Service Report · Human-in-the-Loop Agentic AI</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold">{req.id}</p>
            <p className="text-[11px] text-[#8a8578]">Generated {new Date().toLocaleString()}</p>
          </div>
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            ['Type', req.typeLabel], ['Language', req.langLabel],
            ['Risk', req.risk], ['Autonomy', req.autonomy],
            ['Unit', req.unit], ['Requester', req.anonymous ? `${req.pseudonym || 'Anonymous'} (escrowed)` : req.requester],
            ['SOA ID', req.anonymous ? '— (anonymous)' : (req.soaId || '—')],
            ['Record ID', req.recordId || '—'], ['Filed', new Date(req.createdAt).toLocaleString()],
          ].map(([k, v]) => (
            <div key={k} className="border border-[#151515]/10 rounded-xl p-3">
              <p className="text-[9px] uppercase tracking-widest text-[#8a8578]">{k}</p>
              <p className="text-[12px] font-bold mt-0.5">{k === 'Risk' ? <span className={`px-2 py-0.5 rounded-full text-[10px] ${riskCls[v] || ''}`}>{v}</span> : v}</p>
            </div>
          ))}
        </div>

        {/* Request text */}
        <div className="mb-6">
          <p className="text-[10px] uppercase tracking-widest font-bold text-[#8a8578] mb-1.5">Original request · {req.langLabel}</p>
          <p className="text-[13px] leading-relaxed border-l-4 border-[#F5D34B] pl-3">{req.original}</p>
          <p className="text-[10px] uppercase tracking-widest font-bold text-[#8a8578] mb-1.5 mt-4">Normalized · English</p>
          <p className="text-[13px] leading-relaxed text-[#5a5648]">{req.normalized}</p>
        </div>

        {/* Conflict */}
        {req.conflict && (
          <div className="border-2 border-[#7a4a22]/30 rounded-2xl p-4 mb-6">
            <p className="text-[12px] font-bold text-[#7a4a22] mb-2">{req.conflict.code} — abstained instead of guessing</p>
            {[req.conflict.a, req.conflict.b].map((c, i) => {
              const pol = POLICIES.find((p) => p.id === c.policy);
              return <p key={i} className="text-[11px] text-[#5a5648] mb-1"><span className="font-bold">{pol?.title} {c.ref}:</span> “{c.stance}”</p>;
            })}
            <p className="text-[11px] mt-1.5">Routed to: <strong>{req.conflict.routedTo}</strong></p>
          </div>
        )}

        {/* Plan table */}
        <p className="text-[10px] uppercase tracking-widest font-bold text-[#8a8578] mb-2">Governed plan</p>
        <table className="w-full mb-6 text-[11px]">
          <thead>
            <tr className="border-b border-[#151515]/15 text-left text-[#8a8578]">
              <th className="py-1.5 pr-2 font-semibold w-6">#</th><th className="py-1.5 pr-2 font-semibold">Step</th><th className="py-1.5 pr-2 font-semibold">Tool · Actor</th><th className="py-1.5 pr-2 font-semibold w-16">Risk</th><th className="py-1.5 font-semibold w-20">Status</th>
            </tr>
          </thead>
          <tbody>
            {req.plan.map((s) => (
              <tr key={s.n} className="border-b border-[#151515]/5 align-top">
                <td className="py-2 pr-2 font-bold">{s.n}</td>
                <td className="py-2 pr-2"><span className="font-semibold">{s.title}</span><br /><span className="text-[#8a8578]">{s.output}</span></td>
                <td className="py-2 pr-2 text-[#5a5648]">{s.tool}<br />{s.actor}</td>
                <td className="py-2 pr-2">{s.risk}</td>
                <td className="py-2 font-semibold uppercase">{s.status}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Evidence */}
        {req.evidence?.length > 0 && (
          <div className="mb-6">
            <p className="text-[10px] uppercase tracking-widest font-bold text-[#8a8578] mb-2">Evidence citations</p>
            {req.evidence.map((ev, i) => {
              const pol = POLICIES.find((p) => p.id === ev.policy);
              const sec = pol?.sections.find((s) => s.ref === ev.ref) || pol?.sections[0];
              return (
                <div key={i} className="mb-2.5">
                  <p className="text-[11px] font-bold">{pol?.title} <span className="font-medium text-[#8a8578]">{pol?.version} · {ev.ref} · hash {pol?.hash}</span></p>
                  <p className="text-[11px] text-[#5a5648] leading-relaxed">“{sec?.text}”</p>
                </div>
              );
            })}
          </div>
        )}

        {/* Decision */}
        {req.decision && (
          <div className="border border-[#151515]/15 rounded-2xl p-4 mb-6">
            <p className="text-[10px] uppercase tracking-widest font-bold text-[#8a8578] mb-1">Human decision</p>
            <p className="text-[12px]"><strong>{req.decision.decision}</strong> by {req.decision.by} · {new Date(req.decision.at).toLocaleString()}</p>
            <p className="text-[11px] text-[#5a5648] mt-1">Reason: “{req.decision.reason || '—'}”</p>
          </div>
        )}

        {/* Audit trail */}
        <p className="text-[10px] uppercase tracking-widest font-bold text-[#8a8578] mb-2">Hash-chained audit trail ({events.length} events)</p>
        <div className="space-y-1.5 mb-6">
          {events.map((e) => (
            <div key={e.id} className="flex items-baseline gap-2 text-[10px] border-b border-[#151515]/5 pb-1.5">
              <span className="font-bold shrink-0">{e.id}</span>
              <span className="text-[#5a5648] flex-1">{e.action} — {e.summary}</span>
              <span className="font-mono text-[#8a8578] shrink-0">{e.hash?.slice(0, 12)}…</span>
            </div>
          ))}
        </div>

        <p className="flex items-center gap-1.5 text-[10px] text-[#8a8578] border-t border-[#151515]/10 pt-4">
          <Fingerprint size={11} /> Every event above is SHA-256 chained to its predecessor — any mutation is detectable. SOAIDEATHON-S1.
        </p>
      </div>
    </div>
  );
}
