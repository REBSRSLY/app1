import React, { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from "recharts";
import { LayoutGrid, Users, Swords, GitCompareArrows, ChevronRight, TrendingDown, AlertTriangle } from "lucide-react";

// ---------------------------------------------------------------------------
// Real season data (Vero Volley Milano, A1 Femminile, 23/24)
// ---------------------------------------------------------------------------

const tqrTrend = [
  { m: "Set", tqr: 15.2 },
  { m: "Ott", tqr: 14.6 },
  { m: "Nov", tqr: 14.3 },
  { m: "Dic", tqr: 14.1 },
  { m: "Gen", tqr: 13.8 },
  { m: "Feb", tqr: 13.4 },
  { m: "Mar", tqr: 13.3 },
  { m: "Apr", tqr: 13.3 },
  { m: "Mag", tqr: 13.4 },
];

const fondamentali = [
  { label: "Battuta", sub: "Ace", value: 6 },
  { label: "Ricezione", sub: "Eccellente", value: 24 },
  { label: "Attacco", sub: "Punto", value: 44 },
  { label: "Muro", sub: "Punto", value: 18 },
  { label: "Difesa", sub: "Eccellente", value: 15 },
  { label: "Free ball", sub: "Eccellente", value: 62 },
  { label: "Alzata", sub: "Eccellente", value: 93 },
];

function tqrStatus(v) {
  if (v <= 12.5) return { color: "var(--point)", label: "attenzione" };
  if (v <= 14.5) return { color: "var(--amber)", label: "regolare" };
  return { color: "var(--good)", label: "ottimo" };
}

const rotation = [
  { pos: "P1", role: "Palleggio", name: "Orro", code: "TS3H", tqr: 12.4, tag: "Capitano" },
  { pos: "P2", role: "Opposto", name: "Egonu", code: "3GS4", tqr: 11.2 },
  { pos: "P3", role: "Centro", name: "Folie", code: "8EZC", tqr: 14.6, alt: { name: "Heyrman", code: "Z4SY", tqr: 16.7, note: "rientro da infortunio" } },
  { pos: "P4", role: "Banda", name: "Sylla", code: "09RI", tqr: 13.7 },
  { pos: "P5", role: "Banda", name: "Cazaute", code: "62DH", tqr: 15.5, alt: { name: "Daalderop", code: "II9W", tqr: 13.4 } },
  { pos: "P6", role: "Centro", name: "Rettke", code: "XPN2", tqr: 14.1 },
];

const libero = { role: "Libero", name: "Castillo", code: "W0GU", tqr: 13.8 };

const panchina = [
  { role: "Opposto", name: "Malual", code: "P4T5", tqr: 16.1 },
  { role: "Centro", name: "Candi", code: "NEMC", tqr: 13.3 },
  { role: "Palleggio", name: "Prandi", code: "LC8Z", tqr: 13.8 },
  { role: "Banda", name: "Bajema", code: "1L4C", tqr: 12.3 },
  { role: "Libero", name: "Parrocchiale", code: "M9TM", tqr: 13.9 },
  { role: "Libero", name: "Pusic", code: "BWR1", tqr: 13.7 },
];

const navItems = [
  { icon: LayoutGrid, label: "Panoramica", active: true },
  { icon: Users, label: "Atlete" },
  { icon: Swords, label: "Partite" },
  { icon: GitCompareArrows, label: "Confronti" },
];

// ---------------------------------------------------------------------------

function PlayerChip({ name, code, tqr, tag, small }) {
  const s = tqrStatus(tqr);
  return (
    <div className={`chip ${small ? "chip-sm" : ""}`}>
      <span className="chip-dot" style={{ background: s.color }} />
      <div className="chip-text">
        <div className="chip-name">{name}{tag && <span className="chip-tag">{tag}</span>}</div>
        <div className="chip-meta">{code} · TQR {tqr}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [hoverPos, setHoverPos] = useState(null);
  const first = tqrTrend[0].tqr;
  const last = tqrTrend[tqrTrend.length - 1].tqr;
  const delta = (last - first).toFixed(1);

  return (
    <div className="app">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Teko:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        :root {
          --bg: #0c1424;
          --surface: #131e33;
          --surface-2: #182545;
          --line: rgba(237,238,242,0.08);
          --ink: #edeef2;
          --muted: #7c8aa3;
          --point: #e8483a;
          --amber: #f2a93b;
          --good: #4fb477;
          --court: #16213a;
        }
        * { box-sizing: border-box; }
        .app {
          background:
            radial-gradient(1200px 500px at 85% -10%, rgba(232,72,58,0.08), transparent),
            var(--bg);
          color: var(--ink);
          font-family: 'Inter', sans-serif;
          min-height: 100%;
          display: grid;
          grid-template-columns: 76px 1fr;
          font-size: 14px;
        }
        .num { font-family: 'Teko', sans-serif; font-weight: 600; letter-spacing: 0.01em; }
        .mono { font-family: 'IBM Plex Mono', monospace; }

        /* sidebar */
        .sidebar {
          background: var(--surface);
          border-right: 1px solid var(--line);
          display: flex; flex-direction: column; align-items: center;
          padding: 20px 0; gap: 6px;
        }
        .sb-logo {
          width: 34px; height: 34px; border-radius: 8px;
          background: linear-gradient(145deg, var(--point), #a82c22);
          display:flex; align-items:center; justify-content:center;
          font-family:'Teko'; font-weight:700; font-size:18px; margin-bottom: 28px;
        }
        .sb-item {
          width: 48px; height: 48px; border-radius: 10px;
          display:flex; align-items:center; justify-content:center;
          color: var(--muted); cursor: default; position:relative;
        }
        .sb-item.active { background: var(--surface-2); color: var(--ink); }
        .sb-item.active::before {
          content:''; position:absolute; left:-20px; width:3px; height:20px;
          background: var(--point); border-radius: 2px;
        }
        .sb-item span {
          position:absolute; left:60px; font-size:10px; text-transform:uppercase;
          letter-spacing:0.08em; color: var(--muted); white-space:nowrap;
          opacity:0; pointer-events:none;
        }

        /* main */
        .main { padding: 28px 36px 60px; max-width: 1320px; }
        .header { display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 26px; }
        .eyebrow { color: var(--muted); font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 6px; }
        .title { font-family:'Teko'; font-weight:600; font-size: 40px; line-height:1; letter-spacing: 0.01em; }
        .title span { color: var(--point); }
        .header-right { text-align:right; }
        .header-right .num { font-size: 30px; color: var(--point); }
        .header-right .lbl { color: var(--muted); font-size: 11px; text-transform:uppercase; letter-spacing:0.08em; }

        /* KPI row */
        .kpi-row { display:grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }
        .kpi {
          background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
          padding: 16px 18px; position:relative; overflow:hidden;
        }
        .kpi::after {
          content:''; position:absolute; right:-30px; top:-30px; width:90px; height:90px;
          border-radius: 50%; background: radial-gradient(circle, rgba(232,72,58,0.10), transparent 70%);
        }
        .kpi .lbl { color: var(--muted); font-size: 11px; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px; }
        .kpi .val { font-family:'Teko'; font-size: 38px; line-height:1; }
        .kpi .sub { color: var(--muted); font-size: 12px; margin-top:4px; }
        .kpi .val.point { color: var(--point); }
        .kpi .val.good { color: var(--good); }
        .kpi .val.amber { color: var(--amber); }

        /* grid layout */
        .grid { display:grid; grid-template-columns: 1.15fr 0.85fr; gap: 16px; margin-bottom: 16px; }
        .card {
          background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 20px;
        }
        .card-head { display:flex; justify-content:space-between; align-items:center; margin-bottom: 14px; }
        .card-title { font-size: 13px; font-weight: 600; }
        .card-title small { display:block; color: var(--muted); font-weight:400; font-size:11px; margin-top:2px; }
        .link { color: var(--muted); font-size: 12px; display:flex; align-items:center; gap:2px; }

        .alert {
          display:flex; gap:10px; align-items:flex-start;
          background: rgba(242,169,59,0.08); border: 1px solid rgba(242,169,59,0.25);
          border-radius: 10px; padding: 10px 12px; margin-top: 14px; font-size: 12.5px; color: var(--ink);
        }
        .alert svg { color: var(--amber); flex-shrink:0; margin-top:1px; }
        .alert b { color: var(--amber); }

        /* court / rotation */
        .court {
          position: relative; aspect-ratio: 16/10; border-radius: 10px;
          background:
            repeating-linear-gradient(0deg, rgba(255,255,255,0.02) 0px, rgba(255,255,255,0.02) 1px, transparent 1px, transparent 40px),
            repeating-linear-gradient(90deg, rgba(255,255,255,0.02) 0px, rgba(255,255,255,0.02) 1px, transparent 1px, transparent 40px),
            var(--court);
          border: 1px solid var(--line);
          padding: 18px;
          display: grid; grid-template-columns: repeat(3,1fr); grid-template-rows: repeat(2,1fr);
          gap: 10px;
        }
        .court::before {
          content:''; position:absolute; left:50%; top:8%; bottom:8%; width:2px;
          background: rgba(237,238,242,0.18);
        }
        .slot {
          border: 1px dashed rgba(237,238,242,0.14); border-radius: 8px;
          display:flex; flex-direction:column; justify-content:flex-end; padding: 8px;
          position: relative; transition: border-color 0.15s;
        }
        .slot:hover { border-color: rgba(237,238,242,0.35); }
        .slot .pos-tag {
          position:absolute; top:6px; left:8px; font-family:'Teko'; font-size:16px; color: var(--muted);
        }
        .slot .role { font-size: 9.5px; color: var(--muted); text-transform:uppercase; letter-spacing:0.06em; }
        .slot .name { font-weight: 600; font-size: 13.5px; display:flex; align-items:center; gap:5px; }
        .slot .dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
        .slot .alt { font-size: 10.5px; color: var(--muted); margin-top: 3px; }

        /* roster list */
        .chip {
          display:flex; align-items:center; gap:10px; padding: 8px 6px;
          border-bottom: 1px solid var(--line);
        }
        .chip:last-child { border-bottom:none; }
        .chip-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink:0; }
        .chip-name { font-size: 13px; font-weight: 500; display:flex; align-items:center; gap:6px;}
        .chip-tag {
          font-size: 9px; text-transform:uppercase; letter-spacing:0.05em; color: var(--point);
          border: 1px solid rgba(232,72,58,0.4); border-radius: 4px; padding: 1px 5px;
        }
        .chip-meta { font-size: 11px; color: var(--muted); font-family:'IBM Plex Mono'; }
        .chip-sm .chip-name { font-size: 12.5px; }

        .section-label {
          font-size: 10.5px; text-transform:uppercase; letter-spacing:0.1em; color: var(--muted);
          margin: 14px 0 4px; padding-top: 10px; border-top: 1px solid var(--line);
        }

        .bar-row { display:flex; align-items:center; gap: 10px; padding: 7px 0; }
        .bar-label { width: 90px; font-size: 12px; color: var(--ink); flex-shrink:0; }
        .bar-sub { width: 68px; font-size: 10.5px; color: var(--muted); flex-shrink:0; }
        .bar-track { flex:1; height: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow:hidden; }
        .bar-fill { height: 100%; border-radius: 4px; }
        .bar-val { width: 34px; text-align:right; font-family:'IBM Plex Mono'; font-size: 11.5px; color: var(--muted); }

        .legend { display:flex; gap: 14px; margin-top: 10px; }
        .legend-item { display:flex; align-items:center; gap:5px; font-size:10.5px; color: var(--muted); }
        .legend-dot { width:7px; height:7px; border-radius:50%; }
      `}</style>

      <aside className="sidebar">
        <div className="sb-logo">VM</div>
        {navItems.map((it) => (
          <div key={it.label} className={`sb-item ${it.active ? "active" : ""}`}>
            <it.icon size={18} strokeWidth={1.8} />
          </div>
        ))}
      </aside>

      <main className="main">
        <div className="header">
          <div>
            <div className="eyebrow">Vero Volley Milano · Serie A1 Femminile</div>
            <div className="title">Panoramica <span>Stagione 23/24</span></div>
          </div>
          <div className="header-right">
            <div className="num">44</div>
            <div className="lbl">set giocati</div>
          </div>
        </div>

        <div className="kpi-row">
          <div className="kpi">
            <div className="lbl">Attacco — punto</div>
            <div className="val good">44%</div>
            <div className="sub">2.177 su 4.978 palloni attaccati</div>
          </div>
          <div className="kpi">
            <div className="lbl">Ricezione — eccellente</div>
            <div className="val">24%</div>
            <div className="sub">744 su 3.069 ricezioni · errore 6%</div>
          </div>
          <div className="kpi">
            <div className="lbl">Muro — punto</div>
            <div className="val">18%</div>
            <div className="sub">511 su 2.791 chiusure a rete</div>
          </div>
          <div className="kpi">
            <div className="lbl">TQR medio squadra</div>
            <div className="val point">13.4</div>
            <div className="sub"><TrendingDown size={11} style={{display:'inline', verticalAlign:'-1px'}} /> {delta} da inizio stagione (15.2)</div>
          </div>
        </div>

        <div className="grid">
          <div className="card">
            <div className="card-head">
              <div className="card-title">Qualità del recupero — squadra<small>Media mensile TQR, questionario wellness giornaliero</small></div>
              <div className="link">Dettaglio <ChevronRight size={13} /></div>
            </div>
            <ResponsiveContainer width="100%" height={190}>
              <LineChart data={tqrTrend} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="m" stroke="var(--muted)" tick={{ fontSize: 11, fill: "var(--muted)" }} axisLine={false} tickLine={false} />
                <YAxis domain={[11, 16]} stroke="var(--muted)" tick={{ fontSize: 11, fill: "var(--muted)" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 12 }} labelStyle={{ color: "var(--ink)" }} />
                <Line type="monotone" dataKey="tqr" stroke="var(--point)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--point)" }} />
              </LineChart>
            </ResponsiveContainer>
            <div className="alert">
              <AlertTriangle size={15} />
              <div><b>Recupero in calo</b> da settembre a marzo, poi stabile. Le atlete con TQR più basso in questo momento sono <b>Egonu (11.2)</b>, <b>Orro (12.4)</b> e <b>Bajema (12.3)</b> — da monitorare in vista del carico partite.</div>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <div className="card-title">Efficacia per fondamentale<small>% esiti positivi sul totale stagione, per fondamentale</small></div>
              <div className="link">Tutte le partite <ChevronRight size={13} /></div>
            </div>
            {fondamentali.map((f) => (
              <div className="bar-row" key={f.label}>
                <div className="bar-label">{f.label}</div>
                <div className="bar-sub">{f.sub}</div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${f.value}%`, background: f.value >= 40 ? "var(--good)" : f.value >= 15 ? "var(--amber)" : "var(--point)" }} />
                </div>
                <div className="bar-val">{f.value}%</div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid">
          <div className="card">
            <div className="card-head">
              <div className="card-title">Sestetto titolare<small>Rotazione P1→P6 con indicatore di recupero (TQR)</small></div>
              <div className="link">Modifica formazione <ChevronRight size={13} /></div>
            </div>
            <div className="court">
              {rotation.map((p) => {
                const s = tqrStatus(p.tqr);
                return (
                  <div key={p.pos} className="slot" onMouseEnter={() => setHoverPos(p.pos)} onMouseLeave={() => setHoverPos(null)}>
                    <span className="pos-tag">{p.pos}</span>
                    <div className="role">{p.role}</div>
                    <div className="name"><span className="dot" style={{ background: s.color }} />{p.name}{p.tag && <span className="chip-tag" style={{marginLeft:2}}>{p.tag}</span>}</div>
                    {p.alt && (
                      <div className="alt">↔ {p.alt.name} (TQR {p.alt.tqr}{p.alt.note ? `, ${p.alt.note}` : ""})</div>
                    )}
                  </div>
                );
              })}
              <div className="slot" style={{ gridColumn: "1 / -1", flexDirection:"row", alignItems:"center", justifyContent:"space-between" }}>
                <div>
                  <span className="pos-tag" style={{ position:"static", marginRight: 8 }}>L</span>
                  <span className="role" style={{ display:"inline" }}>{libero.role} — </span>
                  <span className="name" style={{ display:"inline" }}>{libero.name}</span>
                </div>
                <span className="chip-meta">{libero.code} · TQR {libero.tqr}</span>
              </div>
            </div>
            <div className="legend">
              <div className="legend-item"><span className="legend-dot" style={{ background: "var(--good)" }} /> recupero ottimo</div>
              <div className="legend-item"><span className="legend-dot" style={{ background: "var(--amber)" }} /> regolare</div>
              <div className="legend-item"><span className="legend-dot" style={{ background: "var(--point)" }} /> attenzione</div>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <div className="card-title">Rosa completa<small>15 atlete · A1 Femminile</small></div>
              <div className="link">Vedi tutte <ChevronRight size={13} /></div>
            </div>
            <div className="section-label" style={{marginTop:0, paddingTop:0, borderTop:'none'}}>Titolari</div>
            {rotation.map((p) => <PlayerChip key={p.code} name={p.name} code={p.code} tqr={p.tqr} tag={p.tag} small />)}
            <PlayerChip name={libero.name} code={libero.code} tqr={libero.tqr} small />
            <div className="section-label">Panchina</div>
            {panchina.map((p) => <PlayerChip key={p.code} name={p.name} code={p.code} tqr={p.tqr} small />)}
          </div>
        </div>
      </main>
    </div>
  );
}
