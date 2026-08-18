import React, { useState } from 'react';

// ---- Line chart (Crextio hiring-statistics style) ----
export function LineChart({ months, seriesA, seriesB, height = 190 }) {
  const [hover, setHover] = useState(6);
  const W = 640, H = height, padL = 34, padB = 24, padT = 14;
  const max = 200;
  const visible = months.length;
  const x = (i) => padL + (i * (W - padL - 10)) / (visible - 1);
  const y = (v) => padT + (H - padT - padB) * (1 - v / max);
  const path = (arr) => arr.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(v)}`).join(' ');
  const gridVals = [50, 100, 150, 200];

  return (
    <div className="relative w-full">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" onMouseLeave={() => setHover(6)}>
        {gridVals.map((g) => (
          <g key={g}>
            <text x={0} y={y(g) + 4} fontSize="11" fill="#a49f92">{g}</text>
            <line x1={padL} y1={y(g)} x2={W - 10} y2={y(g)} stroke="#151515" strokeOpacity="0.05" />
          </g>
        ))}
        {months.map((m, i) => (
          <text key={m} x={x(i)} y={H - 4} fontSize="11" fill={i === hover ? '#151515' : '#a49f92'} textAnchor="middle" fontWeight={i === hover ? 700 : 400}>{m}</text>
        ))}
        <path d={path(seriesB)} fill="none" stroke="#151515" strokeWidth="1.6" strokeDasharray="4 4" strokeLinecap="round" />
        <path d={path(seriesA)} fill="none" stroke="#F5D34B" strokeWidth="2.2" strokeLinecap="round" />
        {/* hover indicator */}
        <line x1={x(hover)} y1={padT} x2={x(hover)} y2={H - padB} stroke="#151515" strokeWidth="1" strokeOpacity="0.35" />
        <circle cx={x(hover)} cy={y(seriesA[hover])} r="4.5" fill="#151515" stroke="#fff" strokeWidth="2" />
        {months.map((m, i) => (
          <rect key={i} x={x(i) - 25} y={0} width="50" height={H} fill="transparent" onMouseEnter={() => setHover(i)} />
        ))}
      </svg>
      <div className="absolute pointer-events-none bg-[#151515] text-white text-[11px] font-medium px-3 py-1.5 rounded-full flex items-center gap-1.5 shadow-lg"
        style={{ left: `${((padL + (hover * (W - padL - 10)) / (visible - 1)) / W) * 100}%`, top: 0, transform: 'translateX(-50%)' }}>
        <span className="w-1.5 h-1.5 rounded-full bg-[#F5D34B]" /> Auto {seriesA[hover]}
      </div>
    </div>
  );
}

// ---- Donut (employee composition style) ----
export function Donut({ pctA = 70, total = 345, size = 150 }) {
  const r = 56, C = 2 * Math.PI * r;
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg viewBox="0 0 140 140" className="w-full h-full -rotate-90">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#151515" strokeWidth="10" strokeDasharray={`${C * (1 - pctA / 100) - 6} ${C - (C * (1 - pctA / 100) - 6)}`} strokeDashoffset={-C * (pctA / 100) - 3} strokeLinecap="round" />
        <circle cx="70" cy="70" r={r} fill="none" stroke="#F5D34B" strokeWidth="10" strokeDasharray={`${C * (pctA / 100) - 6} ${C - (C * (pctA / 100) - 6)}`} strokeDashoffset="-3" strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-semibold tracking-tight">{total}</span>
        <span className="text-[11px] text-[#8a8578]">Total</span>
      </div>
    </div>
  );
}

// ---- Dot grid (attendance-report style) ----
export function DotGrid({ rows = 4, cols = 12, activePct = 0.62 }) {
  const dots = [];
  const seedActive = (i) => ((i * 2654435761) % 100) / 100 < activePct;
  for (let i = 0; i < rows * cols; i++) dots.push(seedActive(i));
  return (
    <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0,1fr))` }}>
      {dots.map((on, i) => (
        <span key={i} className={`w-2.5 h-2.5 rounded-full transition-colors ${on ? 'bg-[#F5D34B]' : 'bg-white/15'}`} />
      ))}
    </div>
  );
}

// ---- Progress pill row (Crextio interviews/hired bar) ----
export function ProgressPills({ items }) {
  return (
    <div className="flex items-end gap-2 w-full">
      {items.map((it) => (
        <div key={it.label} style={{ width: `${Math.max(it.pct, 9)}%` }} className="min-w-[72px] group">
          <p className="text-[11px] text-[#8a8578] mb-1.5 whitespace-nowrap">{it.label}</p>
          <div className={`rounded-full h-10 flex items-center px-4 text-[12px] font-semibold transition-transform group-hover:scale-[1.02] ${it.variant === 'black' ? 'bg-[#151515] text-white' : it.variant === 'yellow' ? 'bg-[#F5D34B] text-[#151515]' : it.variant === 'hatch' ? 'hatch-bg text-[#151515] border border-[#151515]/15' : 'bg-transparent border border-[#151515]/25 text-[#151515]'}`}>
            {it.pct}%
          </div>
        </div>
      ))}
    </div>
  );
}
