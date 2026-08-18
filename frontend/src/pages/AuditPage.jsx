import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, Link2, History, Undo2, Bug, CheckCircle2, X } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '../components/ui/sheet';
import { toast } from 'sonner';

export default function AuditPage() {
  const { audit, verifyChain, tamperEvent, rollback, resetDemo, requests } = useApp();
  const navigate = useNavigate();
  const [verifyResult, setVerifyResult] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [replayReq, setReplayReq] = useState(null);

  const runVerify = async () => {
    setVerifying(true); setVerifyResult(null);
    try {
      const res = await verifyChain();
      setTimeout(() => { setVerifying(false); setVerifyResult(res); }, 600);
    } catch (e) {
      setVerifying(false);
      toast('Verification failed', { description: 'Backend unreachable.' });
    }
  };

  const runTamper = async () => {
    try {
      await tamperEvent(2);
      toast('Event payload mutated (simulated attack)', { description: 'Run “Verify chain” — the broken link will be identified.' });
      setVerifyResult(null);
    } catch (e) {
      toast('Tamper simulation failed');
    }
  };

  const doRollback = async (evt) => {
    try {
      await rollback(evt);
      toast('Compensating event appended', { description: 'Original history preserved — nothing was deleted or rewritten.' });
    } catch (e) {
      toast('Rollback failed');
    }
  };

  const openReplay = (reqId) => {
    const r = requests.find((q) => q.id === reqId);
    if (r) setReplayReq(r); else toast('No replayable request', { description: 'This event is not linked to a stored request.' });
  };

  return (
    <div className="max-w-[1100px] mx-auto animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4 mt-6 mb-6">
        <div>
          <h1 className="text-5xl font-light tracking-tight">Audit Ledger</h1>
          <p className="text-[13px] text-[#8a8578] mt-3">Append-only, hash-chained events. Rollback creates compensating events — history is never rewritten.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={runVerify} data-testid="verify-chain-btn" className="flex items-center gap-2 bg-[#151515] text-white rounded-full px-5 py-3 text-[13px] font-semibold hover:bg-[#262626] transition-colors">
            <ShieldCheck size={15} /> {verifying ? 'Verifying…' : 'Verify chain'}
          </button>
          <button onClick={runTamper} data-testid="tamper-btn" className="flex items-center gap-2 bg-white border border-[#151515]/15 rounded-full px-5 py-3 text-[13px] font-semibold hover:border-[#8a2f27] hover:text-[#8a2f27] transition-colors">
            <Bug size={15} /> Simulate tamper
          </button>
        </div>
      </div>

      {verifyResult && (
        verifyResult.ok ? (
          <div className="bg-[#E4F2CF] rounded-3xl p-5 mb-5 flex items-center gap-3 animate-fade-up" data-testid="verify-ok">
            <CheckCircle2 size={20} className="text-[#3d5a1e]" />
            <p className="text-[13px] font-semibold text-[#3d5a1e]">Chain valid — {verifyResult.count} events verified, zero broken links. Every hash matches its recomputed value.</p>
          </div>
        ) : (
          <div className="bg-[#F2D5D2] rounded-3xl p-5 mb-5 flex flex-wrap items-center gap-3 animate-fade-up" data-testid="verify-broken">
            <ShieldAlert size={20} className="text-[#8a2f27]" />
            <p className="text-[13px] font-semibold text-[#8a2f27]">Tamper detected — first broken event: {verifyResult.event} (position {verifyResult.brokenAt + 1}). Payload no longer matches its recorded hash.</p>
            <button onClick={resetDemo} data-testid="restore-ledger-btn" className="ml-auto bg-[#151515] text-white rounded-full px-4 py-2 text-[12px] font-semibold">Restore demo ledger</button>
          </div>
        )
      )}

      <div className="bg-[#FBF9F4] rounded-3xl p-4 md:p-5 shadow-sm">
        <div className="space-y-1.5">
          {[...audit].reverse().map((e) => (
            <div key={e.id} className="bg-white rounded-2xl p-4 flex flex-wrap items-center gap-3" data-testid={`audit-event-${e.id}`}>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-bold bg-[#F1EDE3] rounded-full px-2.5 py-0.5">{e.id}</span>
                  <span className="text-[12px] font-bold">{e.action}</span>
                  <button onClick={() => navigate(`/requests/${e.requestId}`)} className="text-[11px] text-[#8a8578] underline underline-offset-2 hover:text-[#151515]">{e.requestId}</button>
                  {e.approval && <span className="text-[9px] font-bold bg-[#F5D34B]/60 rounded-full px-2 py-0.5">{e.approval}</span>}
                </div>
                <p className="text-[12px] text-[#5a5648] mt-1">{e.summary}</p>
                <p className="flex items-center gap-1.5 text-[10px] text-[#8a8578] mt-1.5 font-mono">
                  <Link2 size={10} /> prev {e.prevHash?.slice(0, 10)}… → <span className="text-[#151515] font-bold">{e.hash?.slice(0, 10)}…</span>
                </p>
              </div>
              <div className="flex gap-2 ml-auto">
                <button onClick={() => openReplay(e.requestId)} data-testid={`replay-btn-${e.id}`} title="Replay (read-only)" className="flex items-center gap-1.5 bg-[#F1EDE3] rounded-full px-3.5 py-2 text-[11px] font-semibold hover:bg-[#F5D34B] transition-colors">
                  <History size={12} /> Replay
                </button>
                {e.action.startsWith('tools.') && !e.action.includes('compensate') && (
                  <button onClick={() => doRollback(e)} data-testid={`rollback-btn-${e.id}`} title="Compensating rollback" className="flex items-center gap-1.5 bg-[#F1EDE3] rounded-full px-3.5 py-2 text-[11px] font-semibold hover:bg-[#EAD9CB] transition-colors">
                    <Undo2 size={12} /> Rollback
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Replay sheet */}
      <Sheet open={!!replayReq} onOpenChange={(o) => !o && setReplayReq(null)}>
        <SheetContent className="bg-[#F1EDE3] border-none overflow-y-auto w-full sm:max-w-md">
          {replayReq && (
            <>
              <SheetHeader>
                <SheetTitle className="font-semibold flex items-center gap-2"><History size={17} /> Read-only replay · {replayReq.id}</SheetTitle>
                <SheetDescription className="text-[12px]">Timeline reconstructed from the ledger. Nothing is mutated.</SheetDescription>
              </SheetHeader>
              <div className="mt-5 space-y-3 relative">
                <span className="absolute left-[13px] top-2 bottom-2 w-px bg-[#151515]/15" />
                <div className="relative flex gap-3">
                  <span className="z-10 w-7 h-7 rounded-full bg-[#151515] text-[#F5D34B] flex items-center justify-center text-[9px] font-bold shrink-0">0</span>
                  <div className="bg-white rounded-2xl p-3.5 flex-1">
                    <p className="text-[11px] font-bold">Request received · {replayReq.langLabel}</p>
                    <p className="text-[12px] text-[#5a5648] mt-1">{replayReq.original}</p>
                  </div>
                </div>
                {replayReq.plan.map((s) => (
                  <div key={s.n} className="relative flex gap-3">
                    <span className="z-10 w-7 h-7 rounded-full bg-white border border-[#151515]/15 flex items-center justify-center text-[9px] font-bold shrink-0">{s.n}</span>
                    <div className="bg-white rounded-2xl p-3.5 flex-1">
                      <p className="text-[11px] font-bold">{s.title}</p>
                      <p className="text-[11px] text-[#8a8578] mt-0.5">{s.tool} · {s.actor} · {s.status}</p>
                      <p className="text-[12px] text-[#5a5648] mt-1">{s.output}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
