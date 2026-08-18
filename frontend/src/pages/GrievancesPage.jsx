import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { EyeOff, Lock, Unlock, ShieldAlert, ArrowUpRight, Siren } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { toast } from 'sonner';

export default function GrievancesPage() {
  const { requests, roleId, setRoleId, accessVault, vaultLog, identities } = useApp();
  const navigate = useNavigate();
  const grievances = requests.filter((r) => r.type === 'grievance');
  const [vaultOpen, setVaultOpen] = useState(false);
  const [vaultCase, setVaultCase] = useState(null);
  const [justification, setJustification] = useState('');
  const isAuditor = roleId === 'auditor' || roleId === 'admin';

  const openVault = (g) => { setVaultCase(g); setJustification(''); setVaultOpen(true); };
  const confirmAccess = async () => {
    if (!justification.trim()) { toast('Justification required', { description: 'Vault access must be logged with a reason (POL-GRV §6.3).' }); return; }
    try {
      await accessVault(vaultCase.id, justification.trim());
      toast('Vault access logged', { description: 'An audit event was written for this access.' });
    } catch (e) {
      toast('Vault access denied', { description: e.response?.data?.detail || 'Auditor role required.' });
    }
  };

  const roleView = {
    student: 'As the requester you see your own case status only.',
    requester: 'As the requester you see your own case status only.',
    operator: 'As a unit operator you see pseudonymous case files — identity is never revealed to you.',
    approver: 'Approvers see case metadata needed for escalation decisions, never complainant identity.',
    auditor: 'As the institutional auditor you may unlock the identity vault — every access is justified and logged.',
    admin: 'Administrators may unlock the identity vault — every access is justified and logged.',
  };

  return (
    <div className="max-w-[1000px] mx-auto animate-fade-up">
      <div className="mt-6 mb-6">
        <h1 className="text-5xl font-light tracking-tight">Grievances</h1>
        <p className="text-[13px] text-[#8a8578] mt-3">Anonymous by design. Identity lives in a restricted escrow vault; operators work with pseudonyms.</p>
      </div>

      <div className="bg-[#DCE7F5] rounded-3xl p-4 mb-5 flex items-center gap-3" data-testid="role-view-banner">
        <ShieldAlert size={17} className="text-[#2c4a72] shrink-0" />
        <p className="text-[13px] text-[#2c4a72] font-medium">{roleView[roleId] || roleView.student}</p>
      </div>

      {!isAuditor && (
        <div className="bg-[#F5D34B]/30 border border-[#F5D34B] rounded-3xl p-5 mb-5 flex flex-wrap items-center justify-between gap-3" data-testid="auditor-gate-banner">
          <p className="flex items-center gap-2 text-[13px] font-semibold"><ShieldAlert size={16} /> Identity vault unlocks require the Institutional Auditor.</p>
          <button onClick={() => setRoleId('auditor')} data-testid="switch-to-auditor-btn" className="bg-[#151515] text-white rounded-full px-5 py-2.5 text-[12px] font-semibold hover:bg-[#262626] transition-colors">Switch to K. Das</button>
        </div>
      )}

      <div className="space-y-3">
        {grievances.map((g) => (
          <div key={g.id} className="bg-[#FBF9F4] rounded-3xl p-5 shadow-sm" data-testid={`grievance-card-${g.id}`}>
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <span className="w-10 h-10 rounded-full bg-[#151515] text-[#F5D34B] flex items-center justify-center"><EyeOff size={15} /></span>
              <div className="flex-1 min-w-[180px]">
                <p className="text-[14px] font-bold">{g.recordId} · {g.anonymous ? g.pseudonym : g.requester}</p>
                <p className="text-[11px] text-[#8a8578]">{g.unit} · filed {new Date(g.createdAt).toLocaleString()}</p>
              </div>
              {g.urgency === 'CRITICAL' && <span className="flex items-center gap-1.5 text-[10px] font-bold bg-[#F2D5D2] text-[#8a2f27] rounded-full px-3 py-1.5"><Siren size={11} /> CRITICAL · human triage ≤ 2h</span>}
              <span className="text-[10px] font-bold bg-[#DCE7F5] text-[#2c4a72] rounded-full px-3 py-1.5">{g.status === 'in_triage' ? 'IN TRIAGE' : g.status.toUpperCase()}</span>
            </div>
            <p className="text-[13px] text-[#5a5648] leading-relaxed bg-white rounded-2xl p-4">{g.normalized}</p>

            <div className="flex flex-wrap items-center gap-3 mt-4">
              {/* Identity vault */}
              {g.anonymous && (
                isAuditor ? (
                  <button onClick={() => openVault(g)} data-testid={`vault-open-btn-${g.id}`} className="flex items-center gap-2 bg-[#151515] text-white rounded-full px-5 py-2.5 text-[12px] font-semibold hover:bg-[#262626] transition-colors">
                    <Unlock size={13} /> Access identity vault
                  </button>
                ) : (
                  <span className="flex items-center gap-2 bg-[#e9e4d8] text-[#8a8578] rounded-full px-5 py-2.5 text-[12px] font-semibold cursor-not-allowed" data-testid={`vault-locked-${g.id}`}>
                    <Lock size={13} /> Identity vault · auditor only
                  </span>
                )
              )}
              <button onClick={() => navigate(`/requests/${g.id}`)} className="flex items-center gap-1.5 text-[12px] font-semibold underline underline-offset-4 hover:text-[#5a4a08] ml-auto">Plan & audit trail <ArrowUpRight size={13} /></button>
            </div>
          </div>
        ))}
        {grievances.length === 0 && (
          <div className="bg-[#FBF9F4] rounded-3xl p-10 text-center shadow-sm">
            <p className="text-[14px] font-semibold">No grievances filed</p>
            <button onClick={() => navigate('/intake')} className="mt-4 bg-[#151515] text-white rounded-full px-5 py-2.5 text-[12px] font-semibold">File from Intake</button>
          </div>
        )}
      </div>

      {/* Access log */}
      {vaultLog.length > 0 && (
        <div className="mt-8 bg-[#151515] text-white rounded-3xl p-5">
          <h3 className="text-[14px] font-semibold mb-3">Vault access log — every unlock is audited</h3>
          <div className="space-y-2">
            {vaultLog.map((v, i) => (
              <div key={i} className="bg-white/5 rounded-xl p-3 text-[12px]">
                <span className="text-[#F5D34B] font-bold">{v.by}</span> ({v.role}) accessed <span className="font-bold">{v.caseId}</span> · “{v.justification}” · {new Date(v.at).toLocaleTimeString()}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Vault dialog */}
      <Dialog open={vaultOpen} onOpenChange={setVaultOpen}>
        <DialogContent className="rounded-3xl bg-[#FBF9F4] border-none max-w-md">
          <DialogHeader>
            <DialogTitle className="font-semibold">Identity Escrow Vault</DialogTitle>
            <DialogDescription className="text-[12px]">POL-GRV §6.3 — access requires a logged justification and writes an audit event.</DialogDescription>
          </DialogHeader>
          <textarea value={justification} onChange={(e) => setJustification(e.target.value)} data-testid="vault-justification" placeholder="Justification for accessing complainant identity…"
            className="w-full bg-white rounded-2xl p-3.5 text-[13px] outline-none focus:ring-2 focus:ring-[#F5D34B] resize-none min-h-[72px]" />
          {identities[vaultCase?.id] ? (
            <div className="bg-[#151515] text-white rounded-2xl p-4" data-testid="vault-identity">
              <p className="text-[10px] uppercase tracking-widest text-[#F5D34B] mb-1">Escrowed identity · restricted</p>
              <p className="text-[14px] font-bold">{identities[vaultCase.id].name} · {identities[vaultCase.id].reg}</p>
              <p className="text-[11px] text-white/50">{identities[vaultCase.id].detail}</p>
            </div>
          ) : (
            <button onClick={confirmAccess} data-testid="vault-confirm-btn" className="bg-[#151515] text-white rounded-full px-5 py-3 text-[13px] font-semibold hover:bg-[#262626] transition-colors">
              Log justification & unlock
            </button>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
