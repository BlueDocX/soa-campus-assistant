import React, { useState } from 'react';
import { ShieldCheck, LogIn, Loader2, Users } from 'lucide-react';
import { useAuth, DEMO_ROLES, ROLE_META } from '../context/AuthContext';
import { toast } from 'sonner';

export default function Login() {
  const { login, demoLogin } = useAuth();
  const [email, setEmail] = useState('student@soa.edu');
  const [password, setPassword] = useState('Student@123');
  const [busy, setBusy] = useState(false);

  const doLogin = async () => {
    if (busy) return; setBusy(true);
    try { await login(email.trim(), password); }
    catch (e) { toast('Login failed', { description: e.response?.data?.detail || 'Check your credentials.' }); }
    setBusy(false);
  };
  const doDemo = async (role) => {
    if (busy) return; setBusy(true);
    try { await demoLogin(role); }
    catch (e) { toast('Demo login failed', { description: e.response?.data?.detail || 'Try again.' }); }
    setBusy(false);
  };

  return (
    <div className="min-h-screen bg-[#F1EDE3] flex items-center justify-center p-4">
      <div className="w-full max-w-[440px]">
        <div className="mb-6 text-center">
          <h1 className="text-5xl font-light tracking-tight">SOA</h1>
          <p className="text-[13px] text-[#8a8578] mt-2">Human-in-the-Loop Agentic Institutional Services</p>
        </div>
        <div className="bg-white rounded-3xl p-7 shadow-sm">
          <label className="text-[11px] font-semibold uppercase tracking-wide text-[#8a8578]">Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email"
            className="w-full bg-[#FBF9F4] rounded-2xl px-4 py-3 mt-1 mb-4 text-[14px] outline-none focus:ring-2 focus:ring-[#F5D34B]" />
          <label className="text-[11px] font-semibold uppercase tracking-wide text-[#8a8578]">Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password"
            onKeyDown={(e) => e.key === 'Enter' && doLogin()}
            className="w-full bg-[#FBF9F4] rounded-2xl px-4 py-3 mt-1 mb-5 text-[14px] outline-none focus:ring-2 focus:ring-[#F5D34B]" />
          <button onClick={doLogin} disabled={busy} data-testid="login-submit"
            className="w-full flex items-center justify-center gap-2 bg-[#151515] text-white rounded-full py-3.5 text-[14px] font-semibold hover:bg-[#262626] transition-colors disabled:opacity-50">
            {busy ? <Loader2 size={16} className="animate-spin" /> : <LogIn size={16} />} Sign in
          </button>
        </div>

        <div className="bg-[#151515] text-white rounded-3xl p-5 mt-4">
          <p className="flex items-center gap-2 text-[12px] font-semibold mb-3"><Users size={14} className="text-[#F5D34B]" /> Demo Quick Login (issues a real token)</p>
          <div className="flex flex-wrap gap-2">
            {DEMO_ROLES.map((r) => (
              <button key={r} onClick={() => doDemo(r)} disabled={busy} data-testid={`demo-login-${r}`}
                className="bg-white/10 hover:bg-[#F5D34B] hover:text-[#151515] rounded-full px-4 py-2 text-[12px] font-medium capitalize transition-colors disabled:opacity-50">
                {r}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-white/40 mt-3">{ROLE_META.student.title} \u00b7 backend-enforced RBAC</p>
        </div>
        <p className="flex items-center justify-center gap-2 text-[11px] text-[#8a8578] mt-5"><ShieldCheck size={13} /> JWT sessions \u00b7 roles enforced server-side, never from the browser.</p>
      </div>
    </div>
  );
}
