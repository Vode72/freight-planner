import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import FuelRateManager from "./FuelRateManager";
import CountryRestrictionsPage from "./CountryRestrictionsPage";

const API = "http://127.0.0.1:5000/api";

// ── Tyyliapu ─────────────────────────────────────────────────────────────────
const inp = {
  background: "#0f172a", border: "1px solid #334155", borderRadius: "6px",
  color: "#f1f5f9", padding: "8px 12px", fontSize: "13px", width: "100%", boxSizing: "border-box"
};
const th = {
  color: "#64748b", fontSize: "12px", fontWeight: "600", textTransform: "uppercase",
  letterSpacing: "0.5px", padding: "10px 14px", textAlign: "left", whiteSpace: "nowrap"
};
const td = { padding: "11px 14px", color: "#cbd5e1", fontSize: "13px", borderBottom: "1px solid #1e293b" };
const card = { background: "#1e293b", borderRadius: "12px", padding: "24px", border: "1px solid #334155", marginBottom: "20px" };
const btn = (bg = "#f97316", col = "#fff") => ({
  background: bg, color: col, border: "none", borderRadius: "6px",
  padding: "8px 16px", cursor: "pointer", fontSize: "13px", fontWeight: "600"
});

// ── TabBar ────────────────────────────────────────────────────────────────────
function TabBar({ tabs, active, onChange }) {
  return (
    <div style={{ display: "flex", gap: "4px", borderBottom: "1px solid #334155", marginBottom: "24px" }}>
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

// ── Voimassa-badge ────────────────────────────────────────────────────────────
function ValidBadge({ validFrom, validTo }) {
  const today = new Date().toISOString().slice(0, 10);
  let label, color, bg;
  if (validFrom > today) {
    label = "Tuleva"; color = "#60a5fa"; bg = "#60a5fa20";
  } else if (validTo && validTo < today) {
    label = "Vanhentunut"; color = "#64748b"; bg = "#33415520";
  } else {
    label = "✅ Aktiivinen"; color = "#22c55e"; bg = "#22c55e20";
  }
  return (
    <span style={{ background: bg, color, border: `1px solid ${color}44`,
      borderRadius: "999px", padding: "2px 10px", fontSize: "12px", fontWeight: "600" }}>
      {label}
    </span>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function Modal({ title, onClose, children }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
      <div style={{ background: "#1e293b", borderRadius: "12px", padding: "28px",
        minWidth: "420px", maxWidth: "520px", width: "90%", border: "1px solid #334155" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <h3 style={{ color: "#f1f5f9", margin: 0, fontSize: "16px" }}>{title}</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#64748b",
            cursor: "pointer", fontSize: "20px" }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: "14px" }}>
      <label style={{ display: "block", color: "#94a3b8", fontSize: "11px", fontWeight: "700",
        marginBottom: "5px", textTransform: "uppercase", letterSpacing: "0.5px" }}>{label}</label>
      {children}
    </div>
  );
}

// ── KilometritTab ─────────────────────────────────────────────────────────────
function KilometritTab() {
  const [rates, setRates] = useState([]);
  const [current, setCurrent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // null | {id?, valid_from, valid_to, domestic_rate, continent_rate, notes}

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const today = new Date().toISOString().slice(0, 10);
    const [rRes, cRes] = await Promise.all([
      fetch(`${API}/km-rates`),
      fetch(`${API}/km-rates/current?date=${today}`)
    ]);
    setRates(await rRes.json());
    setCurrent(cRes.ok ? await cRes.json() : null);
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const openNew = () => setModal({ valid_from: "", valid_to: "", domestic_rate: "", continent_rate: "", notes: "" });
  const openEdit = (r) => setModal({ ...r, valid_to: r.valid_to || "" });

  const handleSave = async () => {
    const payload = { ...modal, valid_to: modal.valid_to || null };
    const url = modal.id ? `${API}/km-rates/${modal.id}` : `${API}/km-rates`;
    const method = modal.id ? "PUT" : "POST";
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (res.ok) { setModal(null); fetchAll(); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Poistetaanko hinnasto?")) return;
    await fetch(`${API}/km-rates/${id}`, { method: "DELETE" });
    fetchAll();
  };

  const set = (k, v) => setModal(m => ({ ...m, [k]: v }));

  if (loading) return <div style={{ color: "#64748b", padding: "32px", textAlign: "center" }}>Ladataan...</div>;

  return (
    <div>
      {/* Aktiivinen hinnasto */}
      {current && (
        <div style={{ ...card, background: "#0f2a1a", border: "1px solid #22c55e44" }}>
          <div style={{ display: "flex", gap: "32px", alignItems: "center" }}>
            <div>
              <div style={{ color: "#22c55e", fontSize: "11px", fontWeight: "700",
                textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "4px" }}>Voimassa oleva hinnasto</div>
              <div style={{ color: "#f1f5f9", fontSize: "15px", fontWeight: "600" }}>
                🏠 Kotimaa: <span style={{ color: "#f97316" }}>{current.domestic_rate} €/km</span>
                &nbsp;&nbsp;·&nbsp;&nbsp;
                🌍 Manner: <span style={{ color: "#f97316" }}>{current.continent_rate} €/km</span>
              </div>
              <div style={{ color: "#64748b", fontSize: "12px", marginTop: "4px" }}>
                Alkaen {current.valid_from} {current.valid_to ? `· Asti ${current.valid_to}` : "· Toistaiseksi"}
              </div>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "16px" }}>
        <button style={btn()} onClick={openNew}>➕ Lisää hinnasto</button>
      </div>

      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #334155" }}>
              {["Voimassa alkaen", "Voimassa asti", "Kotimaa €/km", "Manner €/km", "Muistiinpanot", "Status", ""].map(h => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rates.length === 0 ? (
              <tr><td colSpan={7} style={{ ...td, textAlign: "center", color: "#475569", padding: "32px" }}>Ei hinnastoja</td></tr>
            ) : rates.map(r => (
              <tr key={r.id} style={{ background: current?.id === r.id ? "rgba(34,197,94,0.05)" : "transparent" }}>
                <td style={{ ...td, color: "#f1f5f9", fontWeight: "600" }}>{r.valid_from}</td>
                <td style={td}>{r.valid_to || "—"}</td>
                <td style={{ ...td, fontFamily: "monospace", color: "#f97316", fontWeight: "700" }}>{r.domestic_rate} €</td>
                <td style={{ ...td, fontFamily: "monospace", color: "#f97316", fontWeight: "700" }}>{r.continent_rate} €</td>
                <td style={{ ...td, color: "#64748b", fontSize: "12px" }}>{r.notes || "—"}</td>
                <td style={td}><ValidBadge validFrom={r.valid_from} validTo={r.valid_to} /></td>
                <td style={td}>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button onClick={() => openEdit(r)} style={{ background: "#334155", border: "none",
                      color: "#94a3b8", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", fontSize: "12px" }}>✏️</button>
                    <button onClick={() => handleDelete(r.id)} style={{ background: "#ef444422", border: "none",
                      color: "#ef4444", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", fontSize: "12px" }}>🗑️</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal title={modal.id ? "Muokkaa hinnastoa" : "Lisää hinnasto"} onClose={() => setModal(null)}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
            <Field label="Voimassa alkaen">
              <input style={inp} type="date" value={modal.valid_from} onChange={e => set("valid_from", e.target.value)} />
            </Field>
            <Field label="Voimassa asti (tyhjä = toistaiseksi)">
              <input style={inp} type="date" value={modal.valid_to} onChange={e => set("valid_to", e.target.value)} />
            </Field>
            <Field label="Kotimaa €/km">
              <input style={inp} type="number" step="0.01" value={modal.domestic_rate}
                onChange={e => set("domestic_rate", e.target.value)} />
            </Field>
            <Field label="Manner €/km">
              <input style={inp} type="number" step="0.01" value={modal.continent_rate}
                onChange={e => set("continent_rate", e.target.value)} />
            </Field>
          </div>
          <Field label="Muistiinpanot">
            <input style={inp} value={modal.notes || ""} onChange={e => set("notes", e.target.value)} />
          </Field>
          <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "8px" }}>
            <button onClick={() => setModal(null)} style={btn("#334155")}>Peruuta</button>
            <button onClick={handleSave} style={btn()}>Tallenna</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── LautatTab ─────────────────────────────────────────────────────────────────
function LautatTab() {
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const res = await fetch(`${API}/ferry-rates-db`);
    setRates(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const openNew = () => setModal({ route: "", price: "", valid_from: "2026-01-01", valid_to: "", notes: "" });
  const openEdit = (r) => setModal({ ...r, valid_to: r.valid_to || "", price: String(r.price) });

  const handleSave = async () => {
    const payload = { ...modal, price: parseFloat(modal.price), valid_to: modal.valid_to || null };
    const url = modal.id ? `${API}/ferry-rates-db/${modal.id}` : `${API}/ferry-rates-db`;
    const method = modal.id ? "PUT" : "POST";
    const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (res.ok) { setModal(null); fetchAll(); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Poistetaanko reitti?")) return;
    await fetch(`${API}/ferry-rates-db/${id}`, { method: "DELETE" });
    fetchAll();
  };

  const set = (k, v) => setModal(m => ({ ...m, [k]: v }));

  if (loading) return <div style={{ color: "#64748b", padding: "32px", textAlign: "center" }}>Ladataan...</div>;

  return (
    <div>
      <div style={{ background: "#0f1f3a", border: "1px solid #334155", borderRadius: "8px",
        padding: "12px 16px", marginBottom: "16px", color: "#64748b", fontSize: "13px" }}>
        ℹ️ Lauttahinnat hallitaan tässä. Nämä näkyvät katelaskinissa ja kustannusraportissa.
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "16px" }}>
        <button style={btn()} onClick={openNew}>➕ Lisää reitti</button>
      </div>

      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #334155" }}>
              {["Reitti", "Hinta €", "Voimassa alkaen", "Voimassa asti", "Status", ""].map(h => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rates.length === 0 ? (
              <tr><td colSpan={6} style={{ ...td, textAlign: "center", color: "#475569", padding: "32px" }}>Ei reittejä</td></tr>
            ) : rates.map(r => (
              <tr key={r.id}>
                <td style={{ ...td, color: "#f1f5f9", fontWeight: "600" }}>{r.route}</td>
                <td style={{ ...td, fontFamily: "monospace", color: "#f97316", fontWeight: "700" }}>{r.price} €</td>
                <td style={td}>{r.valid_from}</td>
                <td style={td}>{r.valid_to || "—"}</td>
                <td style={td}><ValidBadge validFrom={r.valid_from} validTo={r.valid_to} /></td>
                <td style={td}>
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button onClick={() => openEdit(r)} style={{ background: "#334155", border: "none",
                      color: "#94a3b8", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", fontSize: "12px" }}>✏️</button>
                    <button onClick={() => handleDelete(r.id)} style={{ background: "#ef444422", border: "none",
                      color: "#ef4444", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", fontSize: "12px" }}>🗑️</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modal && (
        <Modal title={modal.id ? "Muokkaa reittiä" : "Lisää lauttareitti"} onClose={() => setModal(null)}>
          <Field label="Reitti">
            <input style={inp} value={modal.route} placeholder="esim. Helsinki - Travemünde"
              onChange={e => set("route", e.target.value)} />
          </Field>
          <Field label="Hinta €">
            <input style={inp} type="number" step="10" value={modal.price}
              onChange={e => set("price", e.target.value)} />
          </Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
            <Field label="Voimassa alkaen">
              <input style={inp} type="date" value={modal.valid_from} onChange={e => set("valid_from", e.target.value)} />
            </Field>
            <Field label="Voimassa asti (tyhjä = toistaiseksi)">
              <input style={inp} type="date" value={modal.valid_to} onChange={e => set("valid_to", e.target.value)} />
            </Field>
          </div>
          <Field label="Muistiinpanot">
            <input style={inp} value={modal.notes || ""} onChange={e => set("notes", e.target.value)} />
          </Field>
          <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "8px" }}>
            <button onClick={() => setModal(null)} style={btn("#334155")}>Peruuta</button>
            <button onClick={handleSave} style={btn()}>Tallenna</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Pääkomponentti ────────────────────────────────────────────────────────────
const TABS = [
  { key: "polttoaine",    label: "⛽ Polttoaine" },
  { key: "kilometrit",    label: "🛣️ Kilometrit" },
  { key: "lautat",        label: "⛴️ Lautat" },
  { key: "maarajoitukset", label: "🌍 Maarajoitukset" },
];

export default function HallintaHinnoittelu() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") || "polttoaine";
  const setTab = (key) => setSearchParams({ tab: key });

  return (
    <div style={{ maxWidth: "1400px" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ color: "#f1f5f9", fontSize: "24px", fontWeight: "700", margin: "0 0 4px" }}>
          💼 Hinnoittelu
        </h1>
        <p style={{ color: "#64748b", margin: 0, fontSize: "14px" }}>
          Polttoaine, kilometrit, lautat ja maarajoitukset
        </p>
      </div>

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {tab === "polttoaine"    && <FuelRateManager />}
      {tab === "kilometrit"    && <KilometritTab />}
      {tab === "lautat"        && <LautatTab />}
      {tab === "maarajoitukset" && <CountryRestrictionsPage />}
    </div>
  );
}
