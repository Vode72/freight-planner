import React, { useState, useEffect, useCallback } from "react";

const API = "http://127.0.0.1:5000/api";

const COUNTRIES = ["FI","DE","CH","FR","AT","IT","PL","CZ","SK","LU","BE","NL","SE","NO","EE"];

const FLAGS = {
  FI:"🇫🇮", DE:"🇩🇪", CH:"🇨🇭", FR:"🇫🇷", AT:"🇦🇹", IT:"🇮🇹",
  PL:"🇵🇱", CZ:"🇨🇿", SK:"🇸🇰", LU:"🇱🇺", BE:"🇧🇪", NL:"🇳🇱",
  SE:"🇸🇪", NO:"🇳🇴", EE:"🇪🇪"
};

const ROUTE_COUNTRIES = {
  "FI→DE": ["DE"],
  "FI→NL": ["DE","NL"],
  "FI→BE": ["DE","BE"],
  "FI→FR": ["DE","FR"],
  "FI→CH": ["DE","CH"],
  "FI→AT": ["DE","AT"],
  "FI→IT": ["DE","AT","IT"],
  "FI→PL": ["PL"],
  "FI→CZ": ["PL","CZ"],
  "FI→SK": ["PL","SK"],
  "FI→LU": ["DE","LU"],
};

const RESTRICTION_TYPES = ["SUNDAY_BAN","NIGHT_BAN","SUMMER_BAN","WEIGHT_LIMIT"];
const SEVERITIES = ["red","orange","yellow"];
const DAYS = ["all","mon","tue","wed","thu","fri","sat","sun"];

const SEV_COLOR = { red:"#ef4444", orange:"#f97316", yellow:"#eab308" };
const SEV_LABEL = { red:"🔴 Kriittinen", orange:"🟠 Varoitus", yellow:"🟡 Huomio" };
const TYPE_LABEL = {
  SUNDAY_BAN:"Sunnuntaikielto", NIGHT_BAN:"Yöajokielto",
  SUMMER_BAN:"Kesärajoitus", WEIGHT_LIMIT:"Painoraja"
};
const STATUS_COLOR = { ok:"#22c55e", warning:"#f97316", blocked:"#ef4444" };
const STATUS_LABEL = { ok:"✅ OK", warning:"⚠️ Varoitus", blocked:"🚫 Estetty" };

// ── Tyyliapu ─────────────────────────────────────────────────────────────────
const card = { background:"#1e293b", borderRadius:"12px", padding:"24px", border:"1px solid #334155" };
const input = {
  background:"#0f172a", border:"1px solid #334155", borderRadius:"6px",
  color:"#f1f5f9", padding:"8px 12px", fontSize:"14px", width:"100%", boxSizing:"border-box"
};
const btn = (bg="#f97316", col="#fff") => ({
  background:bg, color:col, border:"none", borderRadius:"6px",
  padding:"8px 16px", cursor:"pointer", fontSize:"13px", fontWeight:"600"
});
const th = { color:"#64748b", fontSize:"12px", fontWeight:"600", textTransform:"uppercase",
  letterSpacing:"0.5px", padding:"10px 14px", textAlign:"left", whiteSpace:"nowrap" };
const td = { padding:"10px 14px", color:"#cbd5e1", fontSize:"13px", borderBottom:"1px solid #1e293b" };

// ── Vakavuusbadge ────────────────────────────────────────────────────────────
function SevBadge({ sev }) {
  return (
    <span style={{
      background: SEV_COLOR[sev] + "22", color: SEV_COLOR[sev],
      border:`1px solid ${SEV_COLOR[sev]}44`, borderRadius:"999px",
      padding:"2px 10px", fontSize:"12px", fontWeight:"600", whiteSpace:"nowrap"
    }}>
      {SEV_LABEL[sev] || sev}
    </span>
  );
}

// ── Modal-pohja ──────────────────────────────────────────────────────────────
function Modal({ title, onClose, children }) {
  return (
    <div style={{
      position:"fixed", inset:0, background:"rgba(0,0,0,0.7)",
      display:"flex", alignItems:"center", justifyContent:"center", zIndex:1000
    }}>
      <div style={{ background:"#1e293b", borderRadius:"12px", padding:"28px", minWidth:"480px",
        maxWidth:"560px", width:"90%", border:"1px solid #334155", maxHeight:"90vh", overflowY:"auto" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"20px" }}>
          <h3 style={{ color:"#f1f5f9", margin:0, fontSize:"16px" }}>{title}</h3>
          <button onClick={onClose} style={{ background:"none", border:"none", color:"#64748b",
            cursor:"pointer", fontSize:"20px", lineHeight:1 }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ── FormField ─────────────────────────────────────────────────────────────────
function Field({ label, children }) {
  return (
    <div style={{ marginBottom:"14px" }}>
      <label style={{ display:"block", color:"#94a3b8", fontSize:"12px",
        fontWeight:"600", marginBottom:"6px", textTransform:"uppercase", letterSpacing:"0.5px" }}>
        {label}
      </label>
      {children}
    </div>
  );
}

// ── RestrictionModal ─────────────────────────────────────────────────────────
function RestrictionModal({ rule, onClose, onSaved }) {
  const empty = {
    country_code:"DE", restriction_type:"SUNDAY_BAN", day_of_week:"sun",
    date_from:"", date_to:"", time_from:"00:00", time_to:"22:00",
    min_weight_t:7.5, description:"", severity:"orange", exemptions:""
  };
  const [form, setForm] = useState(rule ? {...rule} : empty);
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setForm(f => ({...f, [k]: v}));

  const handleSave = async () => {
    setSaving(true);
    const payload = {...form,
      date_from: form.date_from || null,
      date_to: form.date_to || null,
      exemptions: form.exemptions || null,
    };
    const url = rule ? `${API}/country-restrictions/${rule.id}` : `${API}/country-restrictions`;
    const method = rule ? "PUT" : "POST";
    const res = await fetch(url, { method, headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
    setSaving(false);
    if (res.ok) onSaved();
    else alert("Tallennus epäonnistui");
  };

  return (
    <Modal title={rule ? "Muokkaa sääntöä" : "Lisää sääntö"} onClose={onClose}>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"0 16px" }}>
        <Field label="Maa">
          <select style={input} value={form.country_code} onChange={e=>set("country_code",e.target.value)}>
            {COUNTRIES.map(c=><option key={c} value={c}>{FLAGS[c]||""} {c}</option>)}
          </select>
        </Field>
        <Field label="Tyyppi">
          <select style={input} value={form.restriction_type} onChange={e=>set("restriction_type",e.target.value)}>
            {RESTRICTION_TYPES.map(t=><option key={t} value={t}>{TYPE_LABEL[t]||t}</option>)}
          </select>
        </Field>
        <Field label="Viikonpäivä">
          <select style={input} value={form.day_of_week||""} onChange={e=>set("day_of_week",e.target.value||null)}>
            <option value="">—</option>
            {DAYS.map(d=><option key={d} value={d}>{d}</option>)}
          </select>
        </Field>
        <Field label="Vakavuus">
          <select style={input} value={form.severity} onChange={e=>set("severity",e.target.value)}>
            {SEVERITIES.map(s=><option key={s} value={s}>{SEV_LABEL[s]}</option>)}
          </select>
        </Field>
        <Field label="Aikajakso alkaa (kk-pv)">
          <input style={input} placeholder="esim. 07-01" value={form.date_from||""} onChange={e=>set("date_from",e.target.value)} />
        </Field>
        <Field label="Aikajakso päättyy (kk-pv)">
          <input style={input} placeholder="esim. 08-31" value={form.date_to||""} onChange={e=>set("date_to",e.target.value)} />
        </Field>
        <Field label="Kello alkaen">
          <input style={input} type="time" value={form.time_from||""} onChange={e=>set("time_from",e.target.value)} />
        </Field>
        <Field label="Kello asti">
          <input style={input} type="time" value={form.time_to||""} onChange={e=>set("time_to",e.target.value)} />
        </Field>
        <Field label="Min. paino (t)">
          <input style={input} type="number" step="0.5" value={form.min_weight_t} onChange={e=>set("min_weight_t",parseFloat(e.target.value))} />
        </Field>
      </div>
      <Field label="Kuvaus">
        <input style={input} value={form.description||""} onChange={e=>set("description",e.target.value)} />
      </Field>
      <Field label="Poikkeukset">
        <input style={input} value={form.exemptions||""} onChange={e=>set("exemptions",e.target.value)} />
      </Field>
      <div style={{ display:"flex", gap:"10px", justifyContent:"flex-end", marginTop:"8px" }}>
        <button onClick={onClose} style={btn("#334155")}>Peruuta</button>
        <button onClick={handleSave} disabled={saving} style={btn()}>
          {saving ? "Tallennetaan..." : "Tallenna"}
        </button>
      </div>
    </Modal>
  );
}

// ── TerminalModal ─────────────────────────────────────────────────────────────
function TerminalModal({ terminal, onClose, onSaved }) {
  const empty = { name:"", country_code:"FI", city:"", address:"", contact_person:"", phone:"", has_tail_lift:1, notes:"" };
  const [form, setForm] = useState(terminal ? {...terminal} : empty);
  const [saving, setSaving] = useState(false);

  const set = (k,v) => setForm(f=>({...f,[k]:v}));

  const handleSave = async () => {
    setSaving(true);
    const url = terminal ? `${API}/terminals/${terminal.id}` : `${API}/terminals`;
    const method = terminal ? "PUT" : "POST";
    const res = await fetch(url, { method, headers:{"Content-Type":"application/json"}, body:JSON.stringify(form) });
    setSaving(false);
    if (res.ok) onSaved();
    else alert("Tallennus epäonnistui");
  };

  return (
    <Modal title={terminal ? "Muokkaa terminaalia" : "Lisää terminaali"} onClose={onClose}>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"0 16px" }}>
        <div style={{ gridColumn:"1/-1" }}>
          <Field label="Nimi">
            <input style={input} value={form.name} onChange={e=>set("name",e.target.value)} />
          </Field>
        </div>
        <Field label="Maa">
          <select style={input} value={form.country_code} onChange={e=>set("country_code",e.target.value)}>
            {COUNTRIES.map(c=><option key={c} value={c}>{FLAGS[c]||""} {c}</option>)}
          </select>
        </Field>
        <Field label="Kaupunki">
          <input style={input} value={form.city} onChange={e=>set("city",e.target.value)} />
        </Field>
        <div style={{ gridColumn:"1/-1" }}>
          <Field label="Osoite">
            <input style={input} value={form.address||""} onChange={e=>set("address",e.target.value)} />
          </Field>
        </div>
        <Field label="Yhteyshenkilö">
          <input style={input} value={form.contact_person||""} onChange={e=>set("contact_person",e.target.value)} />
        </Field>
        <Field label="Puhelin">
          <input style={input} value={form.phone||""} onChange={e=>set("phone",e.target.value)} />
        </Field>
      </div>
      <Field label="Perälauta">
        <label style={{ display:"flex", alignItems:"center", gap:"8px", color:"#cbd5e1", cursor:"pointer" }}>
          <input type="checkbox" checked={!!form.has_tail_lift} onChange={e=>set("has_tail_lift",e.target.checked?1:0)} />
          Terminaalissa perälauta
        </label>
      </Field>
      <Field label="Muistiinpanot">
        <input style={input} value={form.notes||""} onChange={e=>set("notes",e.target.value)} />
      </Field>
      <div style={{ display:"flex", gap:"10px", justifyContent:"flex-end", marginTop:"8px" }}>
        <button onClick={onClose} style={btn("#334155")}>Peruuta</button>
        <button onClick={handleSave} disabled={saving} style={btn()}>
          {saving ? "Tallennetaan..." : "Tallenna"}
        </button>
      </div>
    </Modal>
  );
}

// ── Pääkomponentti ────────────────────────────────────────────────────────────
export default function CountryRestrictionsPage() {
  const [restrictions, setRestrictions] = useState([]);
  const [terminals, setTerminals] = useState([]);
  const [filterCC, setFilterCC] = useState("Kaikki");
  const [editRule, setEditRule] = useState(null);
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [editTerminal, setEditTerminal] = useState(null);
  const [showTerminalModal, setShowTerminalModal] = useState(false);

  // Reittitarkistus
  const [checkForm, setCheckForm] = useState({
    origin:"FI", dest:"DE",
    departure:"", arrival:"", weight_t:24.0
  });
  const [checkResult, setCheckResult] = useState(null);
  const [checking, setChecking] = useState(false);

  const fetchAll = useCallback(async () => {
    const [r, t] = await Promise.all([
      fetch(`${API}/country-restrictions`).then(r=>r.json()),
      fetch(`${API}/terminals`).then(r=>r.json()),
    ]);
    setRestrictions(r);
    setTerminals(t);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // --- Filtered restrictions ---
  const filteredRules = filterCC === "Kaikki"
    ? restrictions
    : restrictions.filter(r => r.country_code === filterCC);

  // --- Route check logic ---
  const routeKey = `${checkForm.origin}→${checkForm.dest}`;
  const autoCountries = ROUTE_COUNTRIES[routeKey] || (
    checkForm.origin !== checkForm.dest ? [checkForm.dest] : []
  );

  const handleCheck = async () => {
    if (!checkForm.departure || !checkForm.arrival) {
      alert("Syötä lähtö- ja saapumisaika");
      return;
    }
    setChecking(true);
    const res = await fetch(`${API}/check-restrictions`, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({
        countries: autoCountries,
        departure: checkForm.departure,
        arrival: checkForm.arrival,
        weight_t: checkForm.weight_t
      })
    });
    const data = await res.json();
    setCheckResult(data);
    setChecking(false);
  };

  const handleDeleteRule = async (id) => {
    if (!window.confirm("Poistetaanko sääntö?")) return;
    await fetch(`${API}/country-restrictions/${id}`, { method:"DELETE" });
    fetchAll();
  };

  const handleDeleteTerminal = async (id) => {
    if (!window.confirm("Poistetaanko terminaali?")) return;
    await fetch(`${API}/terminals/${id}`, { method:"DELETE" });
    fetchAll();
  };

  const FILTER_CCS = ["Kaikki", ...Array.from(new Set(restrictions.map(r=>r.country_code))).sort()];

  return (
    <div style={{ maxWidth:"1400px" }}>
      {/* Header */}
      <div style={{ marginBottom:"28px" }}>
        <h1 style={{ color:"#f1f5f9", fontSize:"24px", fontWeight:"700", margin:"0 0 6px" }}>
          🌍 Maarajoitukset & ajokiellot
        </h1>
        <p style={{ color:"#64748b", margin:0, fontSize:"14px" }}>
          Ajorajoitukset maakohtaisesti, reittitarkistus ja terminaalihakemisto
        </p>
      </div>

      {/* ── OSIO A: Sääntölista ── */}
      <div style={{...card, marginBottom:"24px"}}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"18px" }}>
          <h2 style={{ color:"#f1f5f9", fontSize:"16px", fontWeight:"700", margin:0 }}>
            📋 Ajokiellot ja rajoitukset
          </h2>
          <button style={btn()} onClick={() => { setEditRule(null); setShowRuleModal(true); }}>
            ➕ Lisää sääntö
          </button>
        </div>

        {/* Maasuodatin */}
        <div style={{ display:"flex", flexWrap:"wrap", gap:"6px", marginBottom:"18px" }}>
          {FILTER_CCS.map(cc => (
            <button key={cc} onClick={() => setFilterCC(cc)} style={{
              background: filterCC===cc ? "#f97316" : "#0f172a",
              color: filterCC===cc ? "#fff" : "#94a3b8",
              border: `1px solid ${filterCC===cc ? "#f97316" : "#334155"}`,
              borderRadius:"6px", padding:"5px 12px", cursor:"pointer", fontSize:"13px", fontWeight:"600"
            }}>
              {cc !== "Kaikki" ? (FLAGS[cc]||"") + " " : ""}{cc}
            </button>
          ))}
        </div>

        {/* Taulukko */}
        <div style={{ overflowX:"auto" }}>
          <table style={{ width:"100%", borderCollapse:"collapse" }}>
            <thead>
              <tr style={{ borderBottom:"1px solid #334155" }}>
                {["Lippu","Maa","Tyyppi","Päivä","Aika","Paino","Kuvaus","Vakavuus",""].map(h=>(
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRules.length === 0 ? (
                <tr><td colSpan={9} style={{...td, textAlign:"center", color:"#475569", padding:"32px"}}>
                  Ei sääntöjä
                </td></tr>
              ) : filteredRules.map(r => (
                <tr key={r.id} style={{ background:"transparent" }}>
                  <td style={td}>{FLAGS[r.country_code]||"🏳"}</td>
                  <td style={{...td, fontWeight:"600", color:"#f1f5f9"}}>{r.country_code}</td>
                  <td style={td}>
                    <span style={{ background:"#0f172a", borderRadius:"4px", padding:"2px 8px", fontSize:"12px" }}>
                      {TYPE_LABEL[r.restriction_type]||r.restriction_type}
                    </span>
                  </td>
                  <td style={td}>{r.day_of_week || "—"}</td>
                  <td style={td}>
                    {r.restriction_type==="WEIGHT_LIMIT" ? "—" : (r.time_from && r.time_to ? `${r.time_from}–${r.time_to}` : "—")}
                    {(r.date_from || r.date_to) && (
                      <div style={{ color:"#64748b", fontSize:"11px" }}>{r.date_from}–{r.date_to}</div>
                    )}
                  </td>
                  <td style={td}>≥ {r.min_weight_t} t</td>
                  <td style={{...td, maxWidth:"220px"}}>
                    <div style={{ overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}
                      title={r.description}>{r.description}</div>
                    {r.exemptions && <div style={{ color:"#64748b", fontSize:"11px" }}>⚡ {r.exemptions}</div>}
                  </td>
                  <td style={td}><SevBadge sev={r.severity} /></td>
                  <td style={td}>
                    <div style={{ display:"flex", gap:"6px" }}>
                      <button onClick={() => { setEditRule(r); setShowRuleModal(true); }}
                        style={{ background:"#334155", border:"none", color:"#94a3b8",
                          borderRadius:"4px", padding:"4px 8px", cursor:"pointer", fontSize:"12px" }}>
                        ✏️
                      </button>
                      <button onClick={() => handleDeleteRule(r.id)}
                        style={{ background:"#ef444422", border:"none", color:"#ef4444",
                          borderRadius:"4px", padding:"4px 8px", cursor:"pointer", fontSize:"12px" }}>
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── OSIO B: Reittitarkistus ── */}
      <div style={{...card, marginBottom:"24px"}}>
        <h2 style={{ color:"#f1f5f9", fontSize:"16px", fontWeight:"700", margin:"0 0 18px" }}>
          🔍 Tarkista reitti
        </h2>

        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(160px, 1fr))", gap:"14px", marginBottom:"16px" }}>
          <div>
            <label style={{ color:"#94a3b8", fontSize:"12px", fontWeight:"600",
              textTransform:"uppercase", letterSpacing:"0.5px", display:"block", marginBottom:"6px" }}>
              Lähtömaa
            </label>
            <select style={input} value={checkForm.origin}
              onChange={e=>setCheckForm(f=>({...f, origin:e.target.value}))}>
              {COUNTRIES.map(c=><option key={c} value={c}>{FLAGS[c]||""} {c}</option>)}
            </select>
          </div>
          <div>
            <label style={{ color:"#94a3b8", fontSize:"12px", fontWeight:"600",
              textTransform:"uppercase", letterSpacing:"0.5px", display:"block", marginBottom:"6px" }}>
              Kohdemaa
            </label>
            <select style={input} value={checkForm.dest}
              onChange={e=>setCheckForm(f=>({...f, dest:e.target.value}))}>
              {COUNTRIES.map(c=><option key={c} value={c}>{FLAGS[c]||""} {c}</option>)}
            </select>
          </div>
          <div>
            <label style={{ color:"#94a3b8", fontSize:"12px", fontWeight:"600",
              textTransform:"uppercase", letterSpacing:"0.5px", display:"block", marginBottom:"6px" }}>
              Lähtö (pvm + klo)
            </label>
            <input style={input} type="datetime-local" value={checkForm.departure}
              onChange={e=>setCheckForm(f=>({...f, departure:e.target.value}))} />
          </div>
          <div>
            <label style={{ color:"#94a3b8", fontSize:"12px", fontWeight:"600",
              textTransform:"uppercase", letterSpacing:"0.5px", display:"block", marginBottom:"6px" }}>
              Saapuminen (pvm + klo)
            </label>
            <input style={input} type="datetime-local" value={checkForm.arrival}
              onChange={e=>setCheckForm(f=>({...f, arrival:e.target.value}))} />
          </div>
          <div>
            <label style={{ color:"#94a3b8", fontSize:"12px", fontWeight:"600",
              textTransform:"uppercase", letterSpacing:"0.5px", display:"block", marginBottom:"6px" }}>
              Ajoneuvopaino (t)
            </label>
            <input style={input} type="number" step="0.5" min="3.5" max="80"
              value={checkForm.weight_t}
              onChange={e=>setCheckForm(f=>({...f, weight_t:parseFloat(e.target.value)}))} />
          </div>
        </div>

        {/* Välimaat */}
        {autoCountries.length > 0 && (
          <div style={{ marginBottom:"16px", padding:"10px 14px", background:"#0f172a",
            borderRadius:"8px", border:"1px solid #334155" }}>
            <span style={{ color:"#64748b", fontSize:"12px" }}>Tarkistettavat välimaat: </span>
            {autoCountries.map(cc => (
              <span key={cc} style={{ marginLeft:"6px", color:"#94a3b8", fontSize:"13px", fontWeight:"600" }}>
                {FLAGS[cc]||""} {cc}
              </span>
            ))}
          </div>
        )}

        <button onClick={handleCheck} disabled={checking || autoCountries.length===0}
          style={{...btn(), opacity: autoCountries.length===0 ? 0.5 : 1 }}>
          {checking ? "Tarkistetaan..." : "Tarkista rajoitukset"}
        </button>

        {/* Tulos */}
        {checkResult && (
          <div style={{ marginTop:"20px" }}>
            <div style={{
              display:"inline-flex", alignItems:"center", gap:"10px",
              background: STATUS_COLOR[checkResult.overall] + "22",
              border:`1px solid ${STATUS_COLOR[checkResult.overall]}44`,
              borderRadius:"8px", padding:"10px 18px", marginBottom:"16px"
            }}>
              <span style={{ fontSize:"18px" }}>{STATUS_LABEL[checkResult.overall]}</span>
              <span style={{ color: STATUS_COLOR[checkResult.overall], fontSize:"14px", fontWeight:"700" }}>
                {checkResult.overall.toUpperCase()}
              </span>
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(280px, 1fr))", gap:"12px" }}>
              {Object.entries(checkResult.by_country).map(([cc, info]) => (
                <div key={cc} style={{
                  background:"#0f172a", borderRadius:"8px", padding:"16px",
                  border:`2px solid ${STATUS_COLOR[info.status]}44`
                }}>
                  <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"12px" }}>
                    <span style={{ fontSize:"22px" }}>{FLAGS[cc]||"🏳"}</span>
                    <span style={{ color:"#f1f5f9", fontWeight:"700", fontSize:"15px" }}>{cc}</span>
                    <span style={{
                      marginLeft:"auto", background: STATUS_COLOR[info.status]+"22",
                      color: STATUS_COLOR[info.status], border:`1px solid ${STATUS_COLOR[info.status]}44`,
                      borderRadius:"999px", padding:"2px 10px", fontSize:"12px", fontWeight:"600"
                    }}>
                      {STATUS_LABEL[info.status]}
                    </span>
                  </div>
                  {info.violations.length === 0 ? (
                    <p style={{ color:"#22c55e", fontSize:"13px", margin:0 }}>Ei rajoituksia</p>
                  ) : (
                    <ul style={{ margin:0, padding:"0 0 0 16px" }}>
                      {info.violations.map((v, i) => (
                        <li key={i} style={{ marginBottom:"8px" }}>
                          <div style={{ color: SEV_COLOR[v.severity]||"#f97316", fontSize:"13px", fontWeight:"600" }}>
                            {TYPE_LABEL[v.type]||v.type}
                          </div>
                          <div style={{ color:"#94a3b8", fontSize:"12px" }}>{v.description}</div>
                          <div style={{ color:"#64748b", fontSize:"12px" }}>{v.detail}</div>
                          {v.exemptions && (
                            <div style={{ color:"#eab308", fontSize:"11px" }}>⚡ {v.exemptions}</div>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── OSIO C: Terminaalilista ── */}
      <div style={card}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"18px" }}>
          <h2 style={{ color:"#f1f5f9", fontSize:"16px", fontWeight:"700", margin:0 }}>
            🏭 Terminaalit
          </h2>
          <button style={btn()} onClick={() => { setEditTerminal(null); setShowTerminalModal(true); }}>
            ➕ Lisää terminaali
          </button>
        </div>

        <div style={{ overflowX:"auto" }}>
          <table style={{ width:"100%", borderCollapse:"collapse" }}>
            <thead>
              <tr style={{ borderBottom:"1px solid #334155" }}>
                {["Maa","Nimi","Kaupunki","Osoite","Perälauta",""].map(h=>(
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {terminals.length === 0 ? (
                <tr><td colSpan={6} style={{...td, textAlign:"center", color:"#475569", padding:"32px"}}>
                  Ei terminaaleja
                </td></tr>
              ) : terminals.map(t => (
                <tr key={t.id}>
                  <td style={td}>
                    <span style={{ fontWeight:"600" }}>{FLAGS[t.country_code]||"🏳"} {t.country_code}</span>
                  </td>
                  <td style={{...td, color:"#f1f5f9", fontWeight:"600"}}>{t.name}</td>
                  <td style={td}>{t.city}</td>
                  <td style={{...td, color:"#64748b", fontSize:"12px"}}>{t.address||"—"}</td>
                  <td style={td}>
                    {t.has_tail_lift ? (
                      <span style={{ color:"#22c55e", fontSize:"12px", fontWeight:"600" }}>✅ Kyllä</span>
                    ) : (
                      <span style={{ color:"#ef4444", fontSize:"12px" }}>✗ Ei</span>
                    )}
                  </td>
                  <td style={td}>
                    <div style={{ display:"flex", gap:"6px" }}>
                      <button onClick={() => { setEditTerminal(t); setShowTerminalModal(true); }}
                        style={{ background:"#334155", border:"none", color:"#94a3b8",
                          borderRadius:"4px", padding:"4px 8px", cursor:"pointer", fontSize:"12px" }}>
                        ✏️
                      </button>
                      <button onClick={() => handleDeleteTerminal(t.id)}
                        style={{ background:"#ef444422", border:"none", color:"#ef4444",
                          borderRadius:"4px", padding:"4px 8px", cursor:"pointer", fontSize:"12px" }}>
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modalit */}
      {showRuleModal && (
        <RestrictionModal
          rule={editRule}
          onClose={() => { setShowRuleModal(false); setEditRule(null); }}
          onSaved={() => { setShowRuleModal(false); setEditRule(null); fetchAll(); }}
        />
      )}
      {showTerminalModal && (
        <TerminalModal
          terminal={editTerminal}
          onClose={() => { setShowTerminalModal(false); setEditTerminal(null); }}
          onSaved={() => { setShowTerminalModal(false); setEditTerminal(null); fetchAll(); }}
        />
      )}
    </div>
  );
}
