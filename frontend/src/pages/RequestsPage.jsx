import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, Mic } from 'lucide-react';
import { useApp } from '../context/AppContext';

const riskCls = { LOW: 'bg-[#E4F2CF] text-[#3d5a1e]', MEDIUM: 'bg-[#F5D34B]/60 text-[#5a4a08]', HIGH: 'bg-[#151515] text-white', ABSTAINED: 'bg-[#EAD9CB] text-[#7a4a22]' };
const statusMap = {
  completed: ['Completed', 'bg-[#E4F2CF] text-[#3d5a1e]'],
  awaiting_approval: ['Awaiting approval', 'bg-[#F5D34B]/60 text-[#5a4a08]'],
  abstained: ['Abstained', 'bg-[#EAD9CB] text-[#7a4a22]'],
  in_triage: ['Human triage', 'bg-[#DCE7F5] text-[#2c4a72]'],
  needs_info: ['Needs info', 'bg-[#e9e4d8] text-[#5a5648]'],
  rejected: ['Rejected', 'bg-[#F2D5D2] text-[#8a2f27]'],
};

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'maintenance', label: 'Maintenance' },
  { id: 'certificate', label: 'Certificates' },
  { id: 'lab_booking', label: 'Lab Bookings' },
  { id: 'grievance', label: 'Grievances' },
];

export default function RequestsPage() {
  const { requests } = useApp();
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState('all');

  const list = requests.filter((r) => (filter === 'all' || r.type === filter) && (q === '' || `${r.id} ${r.normalized} ${r.typeLabel} ${r.unit}`.toLowerCase().includes(q.toLowerCase())));

  return (
    <div className="max-w-[1160px] mx-auto animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4 mt-6 mb-6">
        <div>
          <h1 className="text-5xl font-light tracking-tight">Requests</h1>
          <p className="text-[13px] text-[#8a8578] mt-3">{requests.length} service requests · every one traceable to evidence and audit events</p>
        </div>
        <button onClick={() => navigate('/intake')} data-testid="new-request-btn" className="flex items-center gap-2 bg-[#151515] text-white rounded-full px-5 py-3 text-[13px] font-semibold hover:bg-[#262626] transition-colors">
          <Plus size={15} /> New request
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="flex items-center gap-2 bg-white rounded-full px-4 py-2.5 flex-1 min-w-[200px] max-w-[320px] shadow-sm">
          <Search size={14} className="text-[#8a8578]" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search requests" data-testid="requests-search" className="bg-transparent outline-none text-[13px] w-full placeholder:text-[#b5b0a3]" />
        </div>
        <div className="flex gap-1 bg-white rounded-full p-1 shadow-sm overflow-x-auto no-scrollbar">
          {FILTERS.map((f) => (
            <button key={f.id} onClick={() => setFilter(f.id)} data-testid={`filter-${f.id}`}
              className={`whitespace-nowrap px-4 py-2 rounded-full text-[12px] font-medium transition-colors ${filter === f.id ? 'bg-[#151515] text-white' : 'text-[#4c483d] hover:bg-[#F1EDE3]'}`}>{f.label}</button>
          ))}
        </div>
      </div>

      <div className="bg-[#FBF9F4] rounded-3xl p-4 md:p-5 shadow-sm">
        <div className="hidden md:grid grid-cols-12 text-[11px] text-[#8a8578] px-3 pb-3">
          <span className="col-span-4">Request</span><span className="col-span-3">Unit</span><span className="col-span-1">Risk</span><span className="col-span-2">Record</span><span className="col-span-2">Status</span>
        </div>
        <div className="space-y-1.5">
          {list.map((r) => (
            <button key={r.id} onClick={() => navigate(`/requests/${r.id}`)} data-testid={`request-row-${r.id}`}
              className="w-full grid grid-cols-2 md:grid-cols-12 items-center gap-2 bg-white rounded-2xl p-3.5 text-left hover:-translate-y-0.5 hover:shadow-md transition-all">
              <div className="col-span-2 md:col-span-4 flex items-center gap-3">
                <span className="w-9 h-9 rounded-full bg-[#151515] text-[#F5D34B] flex items-center justify-center text-[10px] font-bold shrink-0">{r.anonymous ? '••' : (r.requester || 'S')[0]}</span>
                <div className="min-w-0">
                  <p className="text-[13px] font-bold flex items-center gap-1.5">{r.typeLabel} <span className="text-[10px] font-medium text-[#8a8578]">{r.id}</span> {r.viaVoice && <Mic size={11} className="text-[#8a8578]" />}</p>
                  <p className="text-[11px] text-[#8a8578] truncate">{r.normalized}</p>
                </div>
              </div>
              <span className="hidden md:block col-span-3 text-[12px] text-[#5a5648]">{r.unit}</span>
              <span className="col-span-1"><span className={`text-[9px] font-bold px-2 py-1 rounded-full ${riskCls[r.risk]}`}>{r.risk}</span></span>
              <span className="hidden md:block col-span-2 text-[12px] font-semibold">{r.recordId || '—'}</span>
              <span className="col-span-1 md:col-span-2">{(() => { const [l, c] = statusMap[r.status] || [r.status, '']; return <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${c}`}>{l}</span>; })()}</span>
            </button>
          ))}
          {list.length === 0 && <p className="text-center text-[13px] text-[#8a8578] py-8">No requests match.</p>}
        </div>
      </div>
    </div>
  );
}
