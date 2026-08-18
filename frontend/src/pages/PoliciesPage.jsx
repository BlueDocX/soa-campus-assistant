import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Landmark, Fingerprint, TriangleAlert, CalendarDays, Building2, Lock } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PoliciesPage() {
  const [policies, setPolicies] = useState([]);
  const [openId, setOpenId] = useState('POL-LAB');
  useEffect(() => { axios.get(`${API}/policies`).then((r) => setPolicies(r.data)).catch(() => {}); }, []);

  return (
    <div className="max-w-[1000px] mx-auto animate-fade-up">
      <div className="mt-6 mb-6">
        <h1 className="text-5xl font-light tracking-tight">Evidence Corpus</h1>
        <p className="text-[13px] text-[#8a8578] mt-3">Verified corpus only — SOA never answers beyond these documents. One intentional contradiction is seeded for the conflict demo.</p>
      </div>

      <div className="space-y-3">
        {policies.map((p) => {
          const open = openId === p.id;
          const conflicted = p.id === 'POL-EMRG' || p.id === 'POL-LAB';
          return (
            <div key={p.id} className={`rounded-3xl shadow-sm overflow-hidden transition-all ${open ? 'bg-[#FBF9F4]' : 'bg-[#FBF9F4]/70 hover:bg-[#FBF9F4]'}`}>
              <button onClick={() => setOpenId(open ? null : p.id)} data-testid={`policy-${p.id}`} className="w-full flex flex-wrap items-center gap-3 p-5 text-left">
                <span className={`rounded-2xl p-3 ${open ? 'bg-[#F5D34B]' : 'bg-white'}`}><Landmark size={17} /></span>
                <div className="flex-1 min-w-[200px]">
                  <p className="text-[14px] font-bold">{p.title} <span className="text-[11px] font-medium text-[#8a8578]">{p.version}</span></p>
                  <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-[#8a8578] mt-0.5">
                    <span className="flex items-center gap-1"><Building2 size={11} /> {p.unit}</span>
                    <span className="flex items-center gap-1"><CalendarDays size={11} /> effective {p.effective}</span>
                    <span className="flex items-center gap-1"><Lock size={11} /> {p.accessClass}</span>
                  </div>
                </div>
                {conflicted && <span className="flex items-center gap-1.5 text-[10px] font-bold bg-[#EAD9CB] text-[#7a4a22] rounded-full px-3 py-1.5"><TriangleAlert size={11} /> CONFLICT PAIR</span>}
                {p.newer && <span className="text-[10px] font-bold bg-[#151515] text-[#F5D34B] rounded-full px-3 py-1.5">NEWER</span>}
                <span className="text-[11px] font-medium bg-white rounded-full px-3 py-1.5">{p.id}</span>
              </button>
              {open && (
                <div className="px-5 pb-5 space-y-2.5">
                  {p.sections.map((s) => (
                    <div key={s.ref} className="bg-white rounded-2xl p-4">
                      <p className="text-[11px] font-bold text-[#8a8578] mb-1">{s.ref}</p>
                      <p className="text-[13px] leading-relaxed">“{s.text}”</p>
                    </div>
                  ))}
                  <p className="flex items-center gap-1.5 text-[10px] text-[#8a8578] pt-1"><Fingerprint size={11} /> source hash {p.hash} · chunks embedded for retrieval</p>
                  {p.conflictsWith && (
                    <div className="bg-[#EAD9CB] rounded-2xl p-4">
                      <p className="flex items-center gap-2 text-[12px] font-bold text-[#7a4a22]"><TriangleAlert size={13} /> Contradicts {p.conflictsWith.policy} {p.conflictsWith.ref} — requests touching both passages trigger CONFLICT_DETECTED and abstention.</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
