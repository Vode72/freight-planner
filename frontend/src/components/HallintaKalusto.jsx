import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import CarrierList from "./CarrierList";

const API = "http://127.0.0.1:5000/api";
const THERMO_TYPES = ["Umpikaappi", "Umpikaappi 2-koneinen"];
const TRUCK_STATUSES = ["Vapaa", "Ajossa", "Huollossa"];
const MAINT_TYPES = ["INSPECTION", "REFRIGERATION", "OTHER"];
const MAINT_TYPE_LABEL = { INSPECTION: "Katsastus", REFRIGERATION: "Kylmäkonehuolto", OTHER: "Muu huolto" };

// ── Huolto-status ────────────────────────────────────────────────────────────
function dueBadge(dueDateStr) {
  if (!dueDateStr) return { label: "—", color: "#475569", bg: "transparent" };
  const due = new Date(dueDateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.round((due - today) / 86400000);
  if (diffDays < 0)  return { label: "🔴 Erääntynyt",  color: "#ef4444", bg: "#ef444420" };
  if (diffDays < 30) return { label: `🟠 ${diffDays} pv`, color: "#f97316", bg: "#f9731620" };
  if (diffDays < 90) return { label: `🟡 ${diffDays} pv`, color: "#eab308", bg: "#eab30820" };
  return { label: `✅ ${diffDays} pv`, color: "#22c55e", bg: "#22c55e20" };
}

function DueBadge({ date }) {
  const b = dueBadge(date);
  return (
    <span style={{
      background: b.bg, color: b.color, borderRadius: "999px",
      padding: "2px 10px", fontSize: "12px", fontWeight: "600", whiteSpace: "nowrap"
    }}>
      {b.label}
    </span>
  );
}

// ── Tyyliapu ─────────────────────────────────────────────────────────────────
const inp = {
  background: "#0f172a", border: "1px solid #334155", borderRadius: "6px",
  color: "#f1f5f9", padding: "7px 11px", fontSize: "13px", width: "100%", boxSizing: "border-box"
};
const th = {
  color: "#64748b", fontSize: "12px", fontWeight: "600", textTransform: "uppercase",
  letterSpacing: "0.5px", padding: "10px 14px", textAlign: "left", whiteSpace: "nowrap"
};
const td = { padding: "10px 14px", color: "#cbd5e1", fontSize: "13px", borderBottom: "1px solid #1e293b" };
const btn = (bg = "#f97316", col = "#fff") => ({
  background: bg, color: col, border: "none", borderRadius: "6px",
  padding: "7px 14px", cursor: "pointer", fontSize: "13px", fontWeight: "600"
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

// ── VetäjätTab ────────────────────────────────────────────────────────────────
function VetajatTab() {
  const [carriers, setCarriers] = useState([]);
  const [trucks, setTrucks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, tRes] = await Promise.all([
        fetch(`${API}/carriers`), fetch(`${API}/trucks`)
      ]);
      setCarriers(await cRes.json());
      setTrucks(await tRes.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const carrierMap = useMemo(() => Object.fromEntries(carriers.map(c => [c.id, c])), [carriers]);

  const handleStatusChange = async (truck, newStatus) => {
    setUpdatingId(truck.id);
    await fetch(`${API}/trucks/${truck.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...truck, status: newStatus })
    });
    setTrucks(ts => ts.map(t => t.id === truck.id ? { ...t, status: newStatus } : t));
    setUpdatingId(null);
  };

  if (loading) return <div style={{ color: "#64748b", padding: "32px", textAlign: "center" }}>Ladataan...</div>;

  const STATUS_COLOR = { Vapaa: "#22c55e", Ajossa: "#f97316", Huollossa: "#64748b" };

  return (
    <div>
      <div style={{ color: "#64748b", fontSize: "13px", marginBottom: "16px" }}>
        {trucks.length} vetäjää · {carriers.length} yhtiötä
      </div>
      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #334155" }}>
              {["Rekka", "Yhtiö", "Status", ""].map(h => <th key={h} style={th}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {trucks.map(truck => {
              const carrier = carrierMap[truck.carrier_id];
              return (
                <tr key={truck.id}>
                  <td style={{ ...td, color: "#f97316", fontWeight: "700" }}>{truck.plate_number}</td>
                  <td style={td}>
                    <div style={{ color: "#f1f5f9" }}>{carrier?.name || "—"}</div>
                    <div style={{ color: "#64748b", fontSize: "11px" }}>{carrier?.city} {carrier?.country}</div>
                  </td>
                  <td style={td}>
                    <span style={{
                      background: (STATUS_COLOR[truck.status] || "#475569") + "33",
                      color: STATUS_COLOR[truck.status] || "#94a3b8",
                      border: `1px solid ${(STATUS_COLOR[truck.status] || "#475569")}66`,
                      borderRadius: "999px", padding: "3px 12px", fontSize: "12px", fontWeight: "600"
                    }}>{truck.status}</span>
                  </td>
                  <td style={td}>
                    <select
                      value={truck.status}
                      disabled={updatingId === truck.id}
                      onChange={e => handleStatusChange(truck, e.target.value)}
                      style={{ ...inp, width: "auto", fontSize: "12px", padding: "4px 8px" }}
                    >
                      {TRUCK_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── TrailerMaintenance (laajennettu paneeli) ──────────────────────────────────
function MaintenancePanel({ trailer, onUpdated }) {
  const [history, setHistory] = useState([]);
  const [loadingH, setLoadingH] = useState(true);
  const [form, setForm] = useState({
    maintenance_type: "INSPECTION", date: "", next_due: "", notes: ""
  });
  const [saving, setSaving] = useState(false);

  const fetchHistory = useCallback(async () => {
    setLoadingH(true);
    const res = await fetch(`${API}/trailers/${trailer.id}/maintenance`);
    setHistory(await res.json());
    setLoadingH(false);
  }, [trailer.id]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  const handleSave = async () => {
    if (!form.date) { alert("Päivämäärä on pakollinen"); return; }
    setSaving(true);
    await fetch(`${API}/trailers/${trailer.id}/maintenance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form)
    });
    setSaving(false);
    setForm({ maintenance_type: "INSPECTION", date: "", next_due: "", notes: "" });
    fetchHistory();
    onUpdated();
  };

  const handleDelete = async (mid) => {
    if (!window.confirm("Poistetaanko merkintä?")) return;
    await fetch(`${API}/maintenance/${mid}`, { method: "DELETE" });
    fetchHistory();
  };

  const isThermo = THERMO_TYPES.includes(trailer.trailer_type);

  return (
    <div style={{ background: "#0b1221", borderTop: "1px solid #1e293b", padding: "16px 20px" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        {/* Historia */}
        <div>
          <div style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "700", textTransform: "uppercase",
            letterSpacing: "0.5px", marginBottom: "10px" }}>Huoltohistoria</div>
          {loadingH ? (
            <div style={{ color: "#475569", fontSize: "13px" }}>Ladataan...</div>
          ) : history.length === 0 ? (
            <div style={{ color: "#475569", fontSize: "13px" }}>Ei merkintöjä</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {history.map(h => (
                <div key={h.id} style={{
                  background: "#1e293b", borderRadius: "6px", padding: "8px 12px",
                  display: "flex", gap: "10px", alignItems: "flex-start"
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <span style={{ background: "#334155", borderRadius: "4px", padding: "1px 7px",
                        fontSize: "11px", color: "#94a3b8", fontWeight: "600" }}>
                        {MAINT_TYPE_LABEL[h.maintenance_type] || h.maintenance_type}
                      </span>
                      <span style={{ color: "#f1f5f9", fontSize: "13px", fontWeight: "600" }}>{h.date}</span>
                    </div>
                    {h.next_due && <div style={{ color: "#64748b", fontSize: "11px", marginTop: "2px" }}>
                      Seuraava: {h.next_due}
                    </div>}
                    {h.notes && <div style={{ color: "#94a3b8", fontSize: "12px" }}>{h.notes}</div>}
                  </div>
                  <button onClick={() => handleDelete(h.id)} style={{
                    background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "14px"
                  }}>✕</button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Uusi merkintä */}
        <div>
          <div style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "700", textTransform: "uppercase",
            letterSpacing: "0.5px", marginBottom: "10px" }}>+ Uusi huoltomerkintä</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div>
              <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "4px" }}>Tyyppi</div>
              <select style={inp} value={form.maintenance_type}
                onChange={e => setForm(f => ({ ...f, maintenance_type: e.target.value }))}>
                {(isThermo ? MAINT_TYPES : ["INSPECTION", "OTHER"]).map(t =>
                  <option key={t} value={t}>{MAINT_TYPE_LABEL[t]}</option>
                )}
              </select>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              <div>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "4px" }}>Päivämäärä *</div>
                <input style={inp} type="date" value={form.date}
                  onChange={e => setForm(f => ({ ...f, date: e.target.value }))} />
              </div>
              <div>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "4px" }}>Seuraava due</div>
                <input style={inp} type="date" value={form.next_due}
                  onChange={e => setForm(f => ({ ...f, next_due: e.target.value }))} />
              </div>
            </div>
            <div>
              <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "4px" }}>Muistiinpanot</div>
              <input style={inp} value={form.notes} placeholder="vapaaehtoinen"
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
            <button onClick={handleSave} disabled={saving} style={btn()}>
              {saving ? "Tallennetaan..." : "💾 Tallenna merkintä"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── TrailerTab ────────────────────────────────────────────────────────────────
function TrailerTab() {
  const navigate = useNavigate();
  const [trailers, setTrailers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [expandedId, setExpandedId] = useState(null);

  const fetchTrailers = useCallback(async () => {
    setLoading(true);
    const res = await fetch(`${API}/trailers`);
    setTrailers(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => { fetchTrailers(); }, [fetchTrailers]);

  const trailerTypes = useMemo(() => [...new Set(trailers.map(t => t.trailer_type))].sort(), [trailers]);

  const filtered = useMemo(() => {
    let r = [...trailers];
    if (typeFilter !== "all") r = r.filter(t => t.trailer_type === typeFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      r = r.filter(t =>
        (t.plate_number || "").toLowerCase().includes(q) ||
        (t.identifier || "").toLowerCase().includes(q) ||
        (t.trailer_type || "").toLowerCase().includes(q)
      );
    }
    return r;
  }, [trailers, search, typeFilter]);

  const STATUS_COLOR = { Vapaa: "#22c55e", Käytössä: "#f97316", Huollossa: "#64748b" };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div style={{ color: "#64748b", fontSize: "13px" }}>{filtered.length} / {trailers.length} traileria</div>
        <button style={btn()} onClick={() => navigate("/trailers/new")}>+ Uusi traileri</button>
      </div>

      {/* Suodattimet */}
      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px",
        padding: "12px 16px", marginBottom: "16px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
        <input type="text" placeholder="🔍 Hae..." value={search} onChange={e => setSearch(e.target.value)}
          style={{ ...inp, flex: 1, minWidth: "200px" }} />
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={{ ...inp, width: "auto" }}>
          <option value="all">Kaikki tyypit</option>
          {trailerTypes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "10px", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "32px", textAlign: "center", color: "#94a3b8" }}>Ladataan...</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155" }}>
                <th style={th}>Rekisteri</th>
                <th style={th}>Tunniste</th>
                <th style={th}>Tyyppi</th>
                <th style={th}>Status</th>
                <th style={th}>Katsastus</th>
                <th style={th}>Kylmäkone</th>
                <th style={{ ...th, width: "80px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(t => {
                const isExpanded = expandedId === t.id;
                const isThermo = THERMO_TYPES.includes(t.trailer_type);
                return (
                  <React.Fragment key={t.id}>
                    <tr style={{ background: isExpanded ? "rgba(249,115,22,0.05)" : "transparent",
                      cursor: "pointer" }}
                      onClick={() => setExpandedId(isExpanded ? null : t.id)}>
                      <td style={{ ...td, color: "#f97316", fontWeight: "700" }}>
                        <span style={{ marginRight: "6px", color: "#475569", fontSize: "11px" }}>
                          {isExpanded ? "▼" : "▶"}
                        </span>
                        {t.plate_number}
                      </td>
                      <td style={{ ...td, color: "#94a3b8" }}>{t.identifier || "—"}</td>
                      <td style={td}>
                        <span style={{ background: "#334155", color: "#cbd5e1", borderRadius: "4px",
                          padding: "2px 8px", fontSize: "12px", fontWeight: "500" }}>
                          {t.trailer_type}
                        </span>
                      </td>
                      <td style={td}>
                        <span style={{
                          background: (STATUS_COLOR[t.status] || "#475569") + "33",
                          color: STATUS_COLOR[t.status] || "#94a3b8",
                          borderRadius: "999px", padding: "2px 10px", fontSize: "12px", fontWeight: "600"
                        }}>{t.status}</span>
                      </td>
                      <td style={td}>
                        <DueBadge date={t.inspection_due} />
                        {t.inspection_due && (
                          <div style={{ color: "#475569", fontSize: "11px", marginTop: "2px" }}>{t.inspection_due}</div>
                        )}
                      </td>
                      <td style={td}>
                        {isThermo ? (
                          <>
                            <DueBadge date={t.refrigeration_service_due} />
                            {t.refrigeration_service_due && (
                              <div style={{ color: "#475569", fontSize: "11px", marginTop: "2px" }}>{t.refrigeration_service_due}</div>
                            )}
                          </>
                        ) : (
                          <span style={{ color: "#334155", fontSize: "12px" }}>—</span>
                        )}
                      </td>
                      <td style={td} onClick={e => e.stopPropagation()}>
                        <button onClick={() => navigate(`/trailers/${t.id}/edit`)}
                          style={{ background: "#334155", border: "none", color: "#94a3b8",
                            borderRadius: "4px", padding: "4px 8px", cursor: "pointer", fontSize: "12px" }}>
                          ✏️
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={7} style={{ padding: 0 }}>
                          <MaintenancePanel trailer={t} onUpdated={fetchTrailers} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ── Pääkomponentti ────────────────────────────────────────────────────────────
const TABS = [
  { key: "kuljetusyhtiöt", label: "🏢 Kuljetusyhtiöt" },
  { key: "trailerit",      label: "🚐 Trailerit" },
  { key: "vetäjät",        label: "👤 Vetäjät" },
];

export default function HallintaKalusto() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") || "trailerit";

  const setTab = (key) => setSearchParams({ tab: key });

  return (
    <div style={{ maxWidth: "1400px" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ color: "#f1f5f9", fontSize: "24px", fontWeight: "700", margin: "0 0 4px" }}>
          🚛 Kalusto & Kumppanit
        </h1>
        <p style={{ color: "#64748b", margin: 0, fontSize: "14px" }}>
          Kuljetusyhtiöt, trailerit ja vetäjät — hallintanäkymä
        </p>
      </div>

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {tab === "kuljetusyhtiöt" && <CarrierList />}
      {tab === "trailerit"      && <TrailerTab />}
      {tab === "vetäjät"        && <VetajatTab />}
    </div>
  );
}
