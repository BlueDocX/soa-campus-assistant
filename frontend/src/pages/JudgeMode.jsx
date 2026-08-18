import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Clock3, ArrowUpRight, Quote } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { JUDGE_SCENARIOS } from '../mock/mock';

export default function JudgeMode() {
  const navigate = useNavigate();
  const { resetDemo } = useApp();

  return (
    <div className="max-w-[1000px] mx-auto animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4 mt-6 mb-6">
        <div>
          <h1 className="text-5xl font-light tracking-tight">Judge Mode</h1>
          <p className="text-[13px] text-[#8a8578] mt-3">A deterministic five-minute tour. Reset anytime and repeat — no flaky APIs, no waiting.</p>
        </div>
        <button onClick={resetDemo} data-testid="judge-reset-btn" className="bg-white border border-[#151515]/15 rounded-full px-5 py-3 text-[13px] font-semibold hover:bg-[#e9e4d8] transition-colors">Reset all scenarios</button>
      </div>

      {/* Pitch card */}
      <div className="bg-[#151515] text-white rounded-3xl p-6 md:p-8 mb-6">
        <Quote size={22} className="text-[#F5D34B] mb-3" />
        <p className="text-xl md:text-2xl font-light leading-relaxed">
          “Most assistants try to answer. <span className="text-[#F5D34B] font-medium">SOA knows when it is safe to act, when a human must decide, and when the correct answer is to abstain.</span>”
        </p>
        <p className="text-[12px] text-white/50 mt-4">SOAIDEATHON-S1 · Human-in-the-Loop Agentic AI for Autonomous Institutional Service Delivery</p>
      </div>

      {/* Timeline */}
      <div className="relative">
        <span className="absolute left-[27px] top-4 bottom-4 w-px bg-[#151515]/10 hidden sm:block" />
        <div className="space-y-3">
          {JUDGE_SCENARIOS.map((s, i) => (
            <div key={i} className="relative flex flex-col sm:flex-row gap-4 bg-[#FBF9F4] rounded-3xl p-5 shadow-sm hover:shadow-md transition-shadow" data-testid={`judge-scenario-${i}`}>
              <span className="z-10 w-14 h-14 rounded-full bg-[#F5D34B] flex items-center justify-center text-[15px] font-bold shrink-0">{i + 1}</span>
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="flex items-center gap-1 text-[10px] font-bold bg-white rounded-full px-2.5 py-1"><Clock3 size={10} /> {s.t}</span>
                  <h3 className="text-[15px] font-bold">{s.title}</h3>
                </div>
                <p className="text-[13px] text-[#5a5648] leading-relaxed">{s.desc}</p>
              </div>
              <button onClick={() => navigate(s.route)} data-testid={`judge-run-${i}`}
                className="self-start sm:self-center flex items-center gap-2 bg-[#151515] text-white rounded-full px-5 py-3 text-[12px] font-semibold hover:bg-[#262626] transition-colors whitespace-nowrap">
                <Play size={13} /> {s.cta}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Acceptance checklist */}
      <div className="mt-8 bg-[#F5EFC9] rounded-3xl p-6">
        <h3 className="text-lg font-semibold mb-4">Acceptance checklist</h3>
        <div className="grid sm:grid-cols-2 gap-2.5">
          {[
            ['Maintenance request', 'Persisted ticket with backend-generated ID'],
            ['High-risk certificate', 'Cannot complete without a named approver'],
            ['Anonymous grievance', 'Operators never see the identity vault'],
            ['Policy conflict', 'Abstains, shows both passages, routes to human'],
            ['Missing field', 'Asks a focused follow-up instead of guessing'],
            ['Audit mutation', 'Every tool action writes a hash-linked event'],
            ['Tamper test', 'Verification identifies the first broken event'],
            ['Rollback', 'Compensating event; original history intact'],
          ].map(([t, d]) => (
            <div key={t} className="bg-white/70 rounded-2xl p-3.5 flex items-start gap-2.5">
              <ArrowUpRight size={14} className="mt-0.5 text-[#5a4a08] shrink-0" />
              <p className="text-[12px]"><span className="font-bold">{t}:</span> <span className="text-[#5a5648]">{d}</span></p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
