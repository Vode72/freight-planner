import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useToast } from "../hooks/useToast";

const API = "http://127.0.0.1:5000/api";

// ── Tyylit ────────────────────────────────────────────────────────────────────
const inp = {
  background: "#0f172a", border: "1px solid #334155", borderRadius: "6px",
  color: "#f1f5f9", padding: "9px 13px", fontSize: "14px", width: "100%", boxSizing: "border-box",
  outline: "none"
};
const inpDisabled = {
  ...inp, color: "#64748b", cursor: "default", borderColor: "#1e293b"
};
const btn = (bg = "#f97316", col = "#fff", extra = {}) => ({
  background: bg, color: col, border: "none", borderRadius: "6px",
  padding: "9px 18px", cursor: "pointer", fontSize: "13px", fontWeight: "600",
  display: "inline-flex", alignItems: "center", gap: "6px", ...extra
});
const card = {
  background: "#1e293b", borderRadius: "12px", padding: "24px",
  border: "1px solid #334155", marginBottom: "20px"
};
const label = {
  display: "block", color: "#94a3b8", fontSize: "11px", fontWeight: "700",
  textTransform: "uppercase", letterSpacing: "0.6px", marginBottom: "6px"
};

// ── TabBar ────────────────────────────────────────────────────────────────────
function TabBar({ tabs, active, onChange }) {
  return (
    <div style={{ display: "flex", gap: "4px", borderBottom: "1px solid #334155", marginBottom: "28px" }}>
      {tabs.map(t => (
        <button key={t.key} onClick={() => onChange(t.key)} style={{
          background: "none", border: "none", cursor: "pointer",
          padding: "12px 20px", fontSize: "14px", fontWeight: "600",
          color: active === t.key ? "#f97316" : "#64748b",
          borderBottom: active === t.key ? "2px solid #f97316" : "2px solid transparent",
          transition: "all 0.15s"
        }}>{t.label}</button>
      ))}
    </div>
  );
}

// ── OmaYritysTab ──────────────────────────────────────────────────────────────
const COMPANY_FIELDS = [
  { key: "forwarder_name",        label: "Yrityksen nimi",  placeholder: "Demo Freight Oy" },
  { key: "forwarder_address",     label: "Osoite",          placeholder: "Logistiikkakatu 1, 00100 Helsinki" },
  { key: "forwarder_phone",       label: "Puhelin",         placeholder: "+358 9 1234567" },
  { key: "forwarder_email",       label: "Sähköposti",      placeholder: "info@yritys.fi" },
  { key: "forwarder_business_id", label: "Y-tunnus",        placeholder: "1234567-8" },
  { key: "forwarder_vat",         label: "ALV-numero",      placeholder: "FI12345678" },
];

function OmaYritysTab({ settings, onSaved }) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const init = {};
    COMPANY_FIELDS.forEach(f => { init[f.key] = settings[f.key] || ""; });
    setForm(init);
  }, [settings]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      if (res.ok) {
        toast.success("Asetukset tallennettu");
        setEditing(false);
        onSaved();
      } else {
        toast.error("Tallennus epäonnistui");
      }
    } catch {
      toast.error("Yhteysvirhe");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    const reset = {};
    COMPANY_FIELDS.forEach(f => { reset[f.key] = settings[f.key] || ""; });
    setForm(reset);
    setEditing(false);
  };

  // Esikatselu-kortin tiedot suoraan asetuksista (live kun muokataan)
  const preview = editing ? form : settings;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: "24px", alignItems: "start" }}>
      {/* Lomake */}
      <div style={card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <h3 style={{ color: "#f1f5f9", margin: "0 0 4px", fontSize: "16px", fontWeight: "700" }}>
              Yrityksen tiedot
            </h3>
            <p style={{ color: "#64748b", margin: 0, fontSize: "13px" }}>
              Nämä tiedot tulostuvat Transport Order- ja CMR-dokumenteille
            </p>
          </div>
          {!editing && (
            <button onClick={() => setEditing(true)} style={btn("#334155", "#cbd5e1")}>
              ✏️ Muokkaa
            </button>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 20px" }}>
          {COMPANY_FIELDS.map(f => (
            <div key={f.key} style={{ marginBottom: "16px" }}>
              <label style={label}>{f.label}</label>
              {editing ? (
                <input
                  style={inp}
                  value={form[f.key] || ""}
                  placeholder={f.placeholder}
                  onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                />
              ) : (
                <div style={{
                  padding: "9px 13px", background: "#0f172a", borderRadius: "6px",
                  border: "1px solid #1e293b", color: settings[f.key] ? "#f1f5f9" : "#334155",
                  fontSize: "14px", minHeight: "38px"
                }}>
                  {settings[f.key] || <span style={{ color: "#334155", fontStyle: "italic" }}>—</span>}
                </div>
              )}
            </div>
          ))}
        </div>

        {editing && (
          <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "8px",
            paddingTop: "16px", borderTop: "1px solid #334155" }}>
            <button onClick={handleCancel} style={btn("#334155", "#94a3b8")}>Peruuta</button>
            <button onClick={handleSave} disabled={saving} style={btn()}>
              {saving ? "Tallennetaan..." : "💾 Tallenna muutokset"}
            </button>
          </div>
        )}
      </div>

      {/* Esikatselu */}
      <div>
        <div style={card}>
          <div style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", textTransform: "uppercase",
            letterSpacing: "0.6px", marginBottom: "14px" }}>Esikatselu — dokumenteissa</div>
          <div style={{
            background: "#0f172a", borderRadius: "8px", padding: "18px 20px",
            border: "1px solid #334155", fontFamily: "monospace", fontSize: "13px",
            lineHeight: "1.8"
          }}>
            <div style={{ color: "#f97316", fontWeight: "700", fontSize: "14px" }}>
              {preview.forwarder_name || <span style={{ color: "#334155" }}>Yrityksen nimi</span>}
            </div>
            <div style={{ color: "#cbd5e1" }}>
              {preview.forwarder_address || <span style={{ color: "#334155" }}>Osoite</span>}
            </div>
            <div style={{ color: "#94a3b8" }}>
              {preview.forwarder_phone || <span style={{ color: "#334155" }}>Puhelin</span>}
            </div>
            <div style={{ color: "#94a3b8" }}>
              {preview.forwarder_email || <span style={{ color: "#334155" }}>Sähköposti</span>}
            </div>
            <div style={{ borderTop: "1px solid #1e293b", marginTop: "10px", paddingTop: "10px" }}>
              <span style={{ color: "#64748b" }}>Y: </span>
              <span style={{ color: "#cbd5e1" }}>
                {preview.forwarder_business_id || <span style={{ color: "#334155" }}>—</span>}
              </span>
            </div>
            <div>
              <span style={{ color: "#64748b" }}>ALV: </span>
              <span style={{ color: "#cbd5e1" }}>
                {preview.forwarder_vat || <span style={{ color: "#334155" }}>—</span>}
              </span>
            </div>
          </div>
          {editing && (
            <div style={{ marginTop: "10px", padding: "8px 12px", background: "#0f2a1a",
              borderRadius: "6px", border: "1px solid #22c55e33",
              color: "#22c55e", fontSize: "12px" }}>
              ✏️ Esikatselu päivittyy muutostesi mukaan
            </div>
          )}
        </div>

        {/* Tila-kortti */}
        <div style={{ ...card, padding: "16px 20px" }}>
          <div style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", textTransform: "uppercase",
            letterSpacing: "0.6px", marginBottom: "12px" }}>Tietokanta</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {COMPANY_FIELDS.map(f => (
              <div key={f.key} style={{ display: "flex", justifyContent: "space-between",
                alignItems: "center", fontSize: "12px" }}>
                <span style={{ color: "#64748b" }}>{f.label}</span>
                {settings[f.key] ? (
                  <span style={{ color: "#22c55e", fontSize: "11px" }}>✅</span>
                ) : (
                  <span style={{ color: "#475569", fontSize: "11px" }}>—</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── IlmoituksetTab ────────────────────────────────────────────────────────────
const ALERT_FIELDS = [
  {
    enabledKey: "alert_inspection_enabled",
    valueKey:   "alert_inspection_days",
    label:      "Katsastus-hälytys",
    desc:       "Hälytys ennen katsastuksen erääntymistä",
    unit:       "päivää ennen",
    icon:       "🔧",
    defaultVal: "30",
  },
  {
    enabledKey: "alert_refrigeration_enabled",
    valueKey:   "alert_refrigeration_days",
    label:      "Kylmäkonehuolto-hälytys",
    desc:       "Hälytys ennen huollon erääntymistä",
    unit:       "päivää ennen",
    icon:       "❄️",
    defaultVal: "30",
  },
  {
    enabledKey: "alert_load_enabled",
    valueKey:   "alert_load_pct",
    label:      "Täyttöaste-varoitus",
    desc:       "Varoitus kun keikan täyttöaste ylittää rajan",
    unit:       "% täyttöaste",
    icon:       "📦",
    defaultVal: "90",
  },
  {
    enabledKey: "alert_late_enabled",
    valueKey:   "alert_late_hours",
    label:      "Myöhästymis-hälytys",
    desc:       "Hälytys kun keikka myöhässä aikataulusta",
    unit:       "tuntia myöhässä",
    icon:       "⏰",
    defaultVal: "2",
  },
];

function IlmoituksetTab({ settings, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const init = {};
    ALERT_FIELDS.forEach(f => {
      init[f.enabledKey] = settings[f.enabledKey] ?? "1";
      init[f.valueKey]   = settings[f.valueKey]   ?? f.defaultVal;
    });
    setForm(init);
  }, [settings]);

  const toggle = (key) => setForm(p => ({ ...p, [key]: p[key] === "1" ? "0" : "1" }));
  const setVal = (key, v) => setForm(p => ({ ...p, [key]: v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      if (res.ok) { toast.success("Ilmoitusasetukset tallennettu"); onSaved(); }
      else toast.error("Tallennus epäonnistui");
    } catch { toast.error("Yhteysvirhe"); }
    finally { setSaving(false); }
  };

  return (
    <div style={{ maxWidth: "680px" }}>
      <div style={card}>
        <h3 style={{ color: "#f1f5f9", margin: "0 0 6px", fontSize: "16px", fontWeight: "700" }}>
          Hälytyskynnykset
        </h3>
        <p style={{ color: "#64748b", margin: "0 0 24px", fontSize: "13px" }}>
          Määritä milloin Dashboard näyttää varoituksia ja hälytyksiä
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {ALERT_FIELDS.map(f => {
            const enabled = form[f.enabledKey] === "1";
            return (
              <div key={f.enabledKey} style={{
                background: "#0f172a", borderRadius: "10px", padding: "16px 18px",
                border: `1px solid ${enabled ? "#f9731633" : "#1e293b"}`,
                opacity: enabled ? 1 : 0.55, transition: "all 0.2s"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  {/* Toggle */}
                  <button
                    onClick={() => toggle(f.enabledKey)}
                    style={{
                      width: "40px", height: "22px", borderRadius: "999px", border: "none",
                      background: enabled ? "#f97316" : "#334155",
                      position: "relative", cursor: "pointer", flexShrink: 0,
                      transition: "background 0.2s"
                    }}
                  >
                    <div style={{
                      position: "absolute", top: "3px",
                      left: enabled ? "21px" : "3px",
                      width: "16px", height: "16px", borderRadius: "50%",
                      background: "#fff", transition: "left 0.2s"
                    }} />
                  </button>

                  {/* Ikoni + teksti */}
                  <div style={{ flex: 1 }}>
                    <div style={{ color: "#f1f5f9", fontSize: "14px", fontWeight: "600" }}>
                      {f.icon} {f.label}
                    </div>
                    <div style={{ color: "#64748b", fontSize: "12px", marginTop: "2px" }}>{f.desc}</div>
                  </div>

                  {/* Arvo */}
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <input
                      type="number"
                      min="1"
                      max="365"
                      value={form[f.valueKey] || ""}
                      disabled={!enabled}
                      onChange={e => setVal(f.valueKey, e.target.value)}
                      style={{
                        ...(enabled ? inp : inpDisabled),
                        width: "70px", textAlign: "right", fontFamily: "monospace",
                        fontSize: "15px", fontWeight: "700",
                        color: enabled ? "#f97316" : "#475569"
                      }}
                    />
                    <span style={{ color: "#64748b", fontSize: "12px", whiteSpace: "nowrap" }}>
                      {f.unit}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: "20px", paddingTop: "16px", borderTop: "1px solid #334155",
          display: "flex", justifyContent: "flex-end" }}>
          <button onClick={handleSave} disabled={saving} style={btn()}>
            {saving ? "Tallennetaan..." : "💾 Tallenna"}
          </button>
        </div>
      </div>

      {/* Yhteenveto */}
      <div style={{ ...card, padding: "16px 20px" }}>
        <div style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", textTransform: "uppercase",
          letterSpacing: "0.6px", marginBottom: "12px" }}>Aktiiviset hälytykset</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {ALERT_FIELDS.map(f => {
            const enabled = form[f.enabledKey] === "1";
            const val = form[f.valueKey];
            return enabled ? (
              <span key={f.enabledKey} style={{
                background: "#f9731620", color: "#f97316",
                border: "1px solid #f9731644", borderRadius: "999px",
                padding: "4px 12px", fontSize: "12px", fontWeight: "600"
              }}>
                {f.icon} {f.label}: {val} {f.unit}
              </span>
            ) : (
              <span key={f.enabledKey} style={{
                background: "#33415520", color: "#475569",
                border: "1px solid #33415544", borderRadius: "999px",
                padding: "4px 12px", fontSize: "12px"
              }}>
                {f.icon} {f.label}: pois
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Pääkomponentti ────────────────────────────────────────────────────────────
const TABS = [
  { key: "yritys",        label: "🏢 Oma yritys" },
  { key: "ilmoitukset",   label: "🔔 Ilmoitukset" },
];

export default function HallintaAsetukset() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") || "yritys";
  const setTab = (key) => setSearchParams({ tab: key });

  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchSettings = useCallback(async () => {
    const res = await fetch(`${API}/settings`);
    setSettings(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  return (
    <div style={{ maxWidth: "1200px" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ color: "#f1f5f9", fontSize: "24px", fontWeight: "700", margin: "0 0 4px" }}>
          ⚙️ Asetukset
        </h1>
        <p style={{ color: "#64748b", margin: 0, fontSize: "14px" }}>
          Yritystiedot, hälytysten kynnysarvot ja muut järjestelmäasetukset
        </p>
      </div>

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {loading ? (
        <div style={{ color: "#64748b", padding: "48px", textAlign: "center" }}>Ladataan...</div>
      ) : (
        <>
          {tab === "yritys"      && <OmaYritysTab      settings={settings} onSaved={fetchSettings} />}
          {tab === "ilmoitukset" && <IlmoituksetTab    settings={settings} onSaved={fetchSettings} />}
        </>
      )}
    </div>
  );
}
