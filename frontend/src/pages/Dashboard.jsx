import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, ArrowDownRight, Inbox, UserCheck, ScrollText, Search, TrendingUp, ShieldAlert, Mic } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { LineChart, Donut, DotGrid, ProgressPills } from '../components/Charts';
import { CHART_MONTHS, CHART_AUTO, CHART_HUMAN } from '../mock/mock';

const RiskPill = ({ risk }) => {
  const map = {
    LOW: 'bg-[#E4F2CF] text-[#3d5a1e]', MEDIUM: 'bg-[#F5D34B]/60 text-[#5a4a08]', HIGH: 'bg-[#151515] text-white', ABSTAINED: 'bg-[#EAD9CB] text-[#7a4a22]',
  };
  return <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${map[risk] || 'bg-[#e9e4d8]'}`}>{risk}</span>;
};

const StatusPill = ({ status }) => {
  const map = {
    completed: ['Completed', 'bg-[#E4F2CF] text-[#3d5a1e]'],
    awaiting_approval: ['Awaiting approval', 'bg-[#F5D34B]/60 text-[#5a4a08]'],
    abstained: ['Abstained', 'bg-[#EAD9CB] text-[#7a4a22]'],
    in_triage: ['Human triage', 'bg-[#DCE7F5] text-[#2c4a72]'],
    needs_info: ['Needs info', 'bg-[#e9e4d8] text-[#5a5648]'],
    rejected: ['Rejected', 'bg-[#F2D5D2] text-[#8a2f27]'],
  };
  const [label, cls] = map[status] || [status, 'bg-[#e9e4d8]'];
  return <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${label ? cls : ''}`}>{label}</span>;
};

export default function Dashboard() {
  const { role, requests, audit, stats } = useApp();
  const navigate = useNavigate();
  const completed = requests.filter((r) => r.status === 'completed').length;
  const pending = requests.filter((r) => r.status === 'awaiting_approval').length;
  const abstained = requests.filter((r) => r.status === 'abstained' || r.status === 'needs_info').length;
  const total = requests.length;

  return (
    <div className="max-w-[1320px] mx-auto animate-fade-up">
      {/* Hero row */}
      <div className="flex flex-col xl:flex-row xl:items-end gap-8 mt-6 mb-8">
        <div className="flex-1">
          <h1 className="text-5xl md:text-6xl font-light tracking-tight text-[#151515]" data-testid="dashboard-greeting">Hello {role.first}</h1>
          <p className="text-[13px] text-[#8a8578] mt-3 max-w-md">Multilingual requests become evidence-backed, risk-aware workflows. Act when safe · ask a human when consequential · abstain instead of guessing.</p>
        </div>
        <div className="flex items-center gap-8 md:gap-12">
          {[{ icon: Inbox, n: total, label: 'Requests' }, { icon: UserCheck, n: pending, label: 'Awaiting human' }, { icon: ScrollText, n: audit.length, label: 'Audit events' }].map((s) => (
            <div key={s.label} className="flex items-start gap-2">
              <s.icon size={16} className="mt-2 text-[#8a8578]" strokeWidth={1.6} />
              <div>
                <p className="text-5xl md:text-6xl font-light tracking-tight" data-testid={`stat-${s.label.toLowerCase().replace(' ', '-')}`}>{s.n}</p>
                <p className="text-[11px] text-[#8a8578] mt-0.5">{s.label}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Progress pills */}
      <div className="mb-6">
        <ProgressPills items={[
          { label: 'Auto-resolved', pct: stats?.progress?.autoResolved ?? 0, variant: 'black' },
          { label: 'Human approved', pct: stats?.progress?.humanApproved ?? 0, variant: 'yellow' },
          { label: 'Abstained', pct: stats?.progress?.abstained ?? 0, variant: 'hatch' },
          { label: 'Escalated', pct: stats?.progress?.escalated ?? 0, variant: 'outline' },
        ]} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Queue timeline */}
        <div className="lg:col-span-3 bg-[#FBF9F4] rounded-3xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Live Queue</h3>
            <button onClick={() => navigate('/requests')} data-testid="queue-expand-btn" className="bg-white rounded-full p-2 hover:bg-[#F5D34B] transition-colors"><ArrowUpRight size={14} /></button>
          </div>
          <div className="space-y-2.5 relative">
            {requests.slice(0, 5).map((r, i) => (
              <button key={r.id} onClick={() => navigate(`/requests/${r.id}`)} data-testid={`queue-item-${r.id}`}
                className={`w-full text-left rounded-2xl p-3.5 transition-all hover:-translate-y-0.5 ${i === 0 ? 'bg-[#151515] text-white' : 'bg-white'}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] font-semibold">{r.typeLabel}</span>
                  <span className={`text-[10px] ${i === 0 ? 'text-white/50' : 'text-[#8a8578]'}`}>{r.id}</span>
                </div>
                <p className={`text-[11px] leading-snug line-clamp-2 ${i === 0 ? 'text-white/70' : 'text-[#8a8578]'}`}>{r.normalized}</p>
                <div className="mt-2"><StatusPill status={r.status} /></div>
              </button>
            ))}
          </div>
        </div>

        {/* Requests table */}
        <div className="lg:col-span-6 bg-[#FBF9F4] rounded-3xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4 gap-3">
            <h3 className="text-lg font-semibold">Requests</h3>
            <div className="flex items-center gap-2 bg-white rounded-full px-4 py-2 flex-1 max-w-[220px]">
              <Search size={13} className="text-[#8a8578]" />
              <span className="text-[12px] text-[#8a8578]">Search</span>
            </div>
            <button onClick={() => navigate('/requests')} className="bg-white rounded-full p-2 hover:bg-[#F5D34B] transition-colors"><ArrowUpRight size={14} /></button>
          </div>
          <table className="w-full">
            <thead>
              <tr className="text-[11px] text-[#8a8578] text-left">
                <th className="pb-3 font-medium">Request</th><th className="pb-3 font-medium hidden md:table-cell">Unit</th><th className="pb-3 font-medium">Risk</th><th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {requests.slice(0, 5).map((r) => (
                <tr key={r.id} onClick={() => navigate(`/requests/${r.id}`)} className="cursor-pointer hover:bg-white transition-colors group" data-testid={`table-row-${r.id}`}>
                  <td className="py-3 rounded-l-2xl pl-2">
                    <div className="flex items-center gap-2.5">
                      <span className="w-8 h-8 rounded-full bg-[#151515] text-[#F5D34B] flex items-center justify-center text-[10px] font-bold shrink-0">{r.anonymous ? '••' : (r.requester || 'S')[0]}</span>
                      <div>
                        <p className="text-[13px] font-semibold leading-tight">{r.typeLabel}</p>
                        <p className="text-[11px] text-[#8a8578]">{r.id}{r.viaVoice ? ' · voice' : ''}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 text-[12px] text-[#5a5648] hidden md:table-cell">{r.unit}</td>
                  <td className="py-3"><RiskPill risk={r.risk} /></td>
                  <td className="py-3 rounded-r-2xl pr-2"><StatusPill status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Audit black card */}
        <div className="lg:col-span-3 bg-[#151515] text-white rounded-3xl p-5 shadow-md flex flex-col">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-lg font-semibold text-white">Audit Ledger</h3>
            <button onClick={() => navigate('/audit')} data-testid="audit-expand-btn" className="bg-white/10 rounded-full p-2 hover:bg-[#F5D34B] hover:text-[#151515] transition-colors"><ArrowUpRight size={14} /></button>
          </div>
          <div className="flex items-end gap-6 mb-6">
            <div className="flex items-start gap-1">
              <span className="text-5xl font-light">{audit.length}</span>
              <ArrowUpRight size={18} className="text-[#F5D34B] mt-2" />
            </div>
            <div className="flex items-start gap-1">
              <span className="text-5xl font-light">0</span>
              <ArrowDownRight size={18} className="text-white/40 mt-2" />
            </div>
          </div>
          <p className="text-[11px] text-white/50 mb-4">Hash-chained events · zero broken links</p>
          <div className="mt-auto"><DotGrid rows={4} cols={10} activePct={0.62} /></div>
        </div>

        {/* Volume chart */}
        <div className="lg:col-span-8 bg-[#FBF9F4] rounded-3xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
            <h3 className="text-lg font-semibold">Request Volume</h3>
            <div className="flex items-center gap-4 text-[12px]">
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#F5D34B]" /> Auto-executed</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#151515]" /> Human-gated</span>
              <span className="bg-white rounded-full px-3.5 py-1.5 font-medium">2025</span>
            </div>
          </div>
          <LineChart months={stats?.volume?.months || CHART_MONTHS} seriesA={stats?.volume?.auto || CHART_AUTO} seriesB={stats?.volume?.human || CHART_HUMAN} />
        </div>

        {/* Autonomy composition */}
        <div className="lg:col-span-4 bg-[#F5EFC9] rounded-3xl p-5 shadow-sm flex flex-col">
          <h3 className="text-lg font-semibold mb-2">Autonomy Mix</h3>
          <div className="flex-1 flex items-center justify-center"><Donut pctA={stats?.autonomyMix?.auto ?? 70} total={total + 340} size={170} /></div>
          <div className="flex items-center justify-center gap-8 mt-2">
            <span className="flex items-center gap-2 text-2xl font-semibold"><span className="w-2.5 h-2.5 rounded-full bg-[#F5D34B]" />{stats?.autonomyMix?.auto ?? 70}% <TrendingUp size={15} className="text-[#8a8578]" /></span>
            <span className="flex items-center gap-2 text-2xl font-semibold"><span className="w-2.5 h-2.5 rounded-full bg-[#151515]" />{stats?.autonomyMix?.human ?? 30}% <ShieldAlert size={15} className="text-[#8a8578]" /></span>
          </div>
          <p className="text-center text-[11px] text-[#8a8578] mt-2">auto-executed vs human-gated</p>
        </div>
      </div>

      {/* CTA strip */}
      <button onClick={() => navigate('/intake')} data-testid="cta-new-request" className="mt-4 w-full bg-[#151515] text-white rounded-3xl p-6 flex items-center justify-between hover:bg-[#262626] transition-colors group">
        <div className="flex items-center gap-4">
          <span className="bg-[#F5D34B] text-[#151515] rounded-full p-3"><Mic size={18} /></span>
          <div className="text-left">
            <p className="text-lg font-semibold">Start a new request</p>
            <p className="text-[12px] text-white/50">Speak or type in English, Hindi or Odia — your words become an auditable service request</p>
          </div>
        </div>
        <ArrowUpRight size={22} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
      </button>
    </div>
  );
}
