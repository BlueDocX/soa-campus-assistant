import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Bell, Settings, ChevronDown, RotateCcw } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuLabel, DropdownMenuSeparator } from './ui/dropdown-menu';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';

const relTime = (ts) => {
  if (!ts) return '';
  const t = new Date(ts).getTime();
  if (Number.isNaN(t)) return '';
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
};

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/intake', label: 'Intake' },
  { to: '/assistant', label: 'Assistant' },
  { to: '/requests', label: 'Requests' },
  { to: '/approvals', label: 'Approvals' },
  { to: '/policies', label: 'Policies' },
  { to: '/grievances', label: 'Grievances' },
  { to: '/audit', label: 'Audit' },
  { to: '/judge', label: 'Judge Mode' },
];

const initials = (name) => name.split(' ').map((w) => w[0]).slice(0, 2).join('');

export default function Layout({ children }) {
  const { role, roleId, setRoleId, roles, requests, audit, resetDemo, fetchAll } = useApp();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [notesOpen, setNotesOpen] = useState(false);
  const pending = requests.filter((r) => r.status === 'awaiting_approval').length;
  const triage = requests.filter((r) => r.status === 'in_triage').length;
  const recentAudit = [...audit].slice().reverse().slice(0, 8);

  return (
    <div className="min-h-screen bg-[#F1EDE3] text-[#151515]" style={{ fontFamily: 'Manrope, sans-serif' }}>
      {/* Header */}
      <header className="print-hide sticky top-0 z-40 px-4 md:px-8 pt-4 pb-2 bg-[#F1EDE3]/90 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')} data-testid="logo-btn" className="flex items-center gap-2 shrink-0 border border-[#151515]/20 rounded-full pl-2.5 pr-4 py-1.5 bg-transparent hover:bg-white/60 transition-colors">
            <img src="/soa-logo.webp" alt="SOA logo" className="w-6 h-6 shrink-0 rounded-full object-contain" />
            <span className="text-base font-medium tracking-tight whitespace-nowrap leading-none">SOA</span>
          </button>

          <nav className="hidden lg:flex items-center gap-1 bg-white rounded-full p-1.5 shadow-sm mx-auto" data-testid="main-nav">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === '/'}
                className={({ isActive }) => `px-4 py-2 rounded-full text-[13px] font-medium transition-colors ${isActive ? 'bg-[#151515] text-white' : 'text-[#4c483d] hover:bg-[#F1EDE3]'}`}
                data-testid={`nav-${n.label.toLowerCase().replace(' ', '-')}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-2 ml-auto lg:ml-0">
            <button onClick={resetDemo} title="Reset demo data" data-testid="reset-demo-btn" className="hidden md:flex items-center gap-1.5 bg-white rounded-full px-3.5 py-2.5 text-[12px] font-medium text-[#4c483d] hover:bg-[#e9e4d8] transition-colors shadow-sm">
              <RotateCcw size={14} /> Reset
            </button>
            <Popover open={notesOpen} onOpenChange={(open) => { setNotesOpen(open); if (open) fetchAll(); }}>
              <PopoverTrigger asChild>
                <button className="relative bg-[#F5D34B] rounded-full p-2.5 hover:brightness-95 transition-all shadow-sm" data-testid="notifications-btn">
                  <Bell size={16} strokeWidth={1.8} />
                  {(pending + triage) > 0 && <span className="absolute -top-0.5 -right-0.5 bg-[#151515] text-white text-[9px] rounded-full w-4 h-4 flex items-center justify-center">{pending + triage}</span>}
                </button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80 rounded-2xl border-[#151515]/10 bg-white p-3">
                <p className="text-sm font-semibold mb-2 px-1">Live ledger</p>
                {(pending + triage) > 0 && (
                  <div className="mb-2 space-y-1">
                    {pending > 0 && <button onClick={() => { setNotesOpen(false); navigate('/approvals'); }} className="w-full text-left text-[13px] p-2.5 rounded-xl hover:bg-[#F1EDE3] transition-colors">{pending} approval{pending > 1 ? 's' : ''} pending · Academic Approver</button>}
                    {triage > 0 && <button onClick={() => { setNotesOpen(false); navigate('/grievances'); }} className="w-full text-left text-[13px] p-2.5 rounded-xl hover:bg-[#F1EDE3] transition-colors">{triage} grievance{triage > 1 ? 's' : ''} in human triage</button>}
                  </div>
                )}
                {recentAudit.length === 0 && <p className="text-[13px] text-[#8a8578] p-2">No ledger events yet.</p>}
                <div className="space-y-1 max-h-80 overflow-y-auto">
                  {recentAudit.map((e) => (
                    <button
                      key={e.id}
                      onClick={() => { if (e.requestId) { setNotesOpen(false); navigate(`/requests/${e.requestId}`); } }}
                      className="w-full text-left p-2.5 rounded-xl hover:bg-[#F1EDE3] transition-colors"
                      data-testid={`notify-evt-${e.id}`}
                    >
                      <span className="flex items-baseline justify-between gap-2">
                        <span className="text-[12px] font-semibold">{e.action}</span>
                        <span className="text-[10px] text-[#8a8578] shrink-0">{relTime(e.ts)}</span>
                      </span>
                      <span className="block text-[12px] text-[#5a5648] mt-0.5 line-clamp-2">{e.summary}</span>
                    </button>
                  ))}
                </div>
              </PopoverContent>
            </Popover>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 bg-white rounded-full pl-1.5 pr-3 py-1.5 hover:bg-[#e9e4d8] transition-colors shadow-sm" data-testid="role-switcher-btn">
                  <span className="w-8 h-8 rounded-full bg-[#151515] text-[#F5D34B] flex items-center justify-center text-[11px] font-bold">{initials(role.name)}</span>
                  <span className="hidden md:block text-left">
                    <span className="block text-[12px] font-semibold leading-tight">{role.name}</span>
                    <span className="block text-[10px] text-[#8a8578] leading-tight">{role.title}</span>
                  </span>
                  <ChevronDown size={14} className="text-[#8a8578]" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 rounded-2xl border-[#151515]/10 bg-white">
                <DropdownMenuLabel className="text-[11px] uppercase tracking-widest text-[#8a8578]">Switch role (demo)</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {roles.map((r) => (
                  <DropdownMenuItem key={r.id} onClick={() => setRoleId(r.id)} data-testid={`role-option-${r.id}`} className={`rounded-xl m-1 cursor-pointer ${r.id === roleId ? 'bg-[#F5D34B]/30' : ''}`}>
                    <span className="w-7 h-7 rounded-full bg-[#151515] text-[#F5D34B] flex items-center justify-center text-[10px] font-bold mr-2">{initials(r.name)}</span>
                    <span>
                      <span className="block text-[13px] font-medium">{r.name}</span>
                      <span className="block text-[11px] text-[#8a8578]">{r.title}</span>
                    </span>
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} data-testid="logout-btn" className="rounded-xl m-1 cursor-pointer text-[#8a2f27]">
                  <span className="text-[13px] font-medium">Sign out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <button className="hidden md:block bg-white rounded-full p-2.5 hover:bg-[#e9e4d8] transition-colors shadow-sm" data-testid="settings-btn">
              <Settings size={16} strokeWidth={1.8} />
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        <nav className="lg:hidden flex gap-1 overflow-x-auto mt-3 bg-white rounded-full p-1.5 shadow-sm no-scrollbar">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'}
              className={({ isActive }) => `whitespace-nowrap px-3.5 py-1.5 rounded-full text-[12px] font-medium transition-colors ${isActive ? 'bg-[#151515] text-white' : 'text-[#4c483d]'}`}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="px-4 md:px-8 pb-16 pt-2">{children}</main>
    </div>
  );
}
