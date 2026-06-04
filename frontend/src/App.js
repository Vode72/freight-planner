import React, { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, NavLink, Outlet, useNavigate } from "react-router-dom";
import Login from "./components/Login";
import OrderList from "./components/OrderList";
import OrderForm from "./components/OrderForm";
import TripList from "./components/TripList";
import TripForm from "./components/TripForm";
import TripDetail from "./components/TripDetail";
import CostCalculator from "./components/CostCalculator";
import AddToTripModal from "./components/AddToTripModal";
import CustomerList from "./components/CustomerList";
import CustomerForm from "./components/CustomerForm";
import Dashboard from "./components/Dashboard";
import CarrierList from "./components/CarrierList";
import CarrierForm from "./components/CarrierForm";
import TrailerList from "./components/TrailerList";
import TrailerForm from "./components/TrailerForm";
import FuelRateManager from "./components/FuelRateManager";
import CostsDashboard from "./components/CostsDashboard";
import CountryRestrictionsPage from "./components/CountryRestrictionsPage";
import HallintaKalusto from "./components/HallintaKalusto";
import HallintaHinnoittelu from "./components/HallintaHinnoittelu";
import HallintaAsetukset from "./components/HallintaAsetukset";
import DriverPage from "./components/DriverPage";
import { ToastProvider } from './context/ToastContext';
import ToastContainer from './components/ToastContainer';

// ── Sidebar-nappi NavLinkillä ────────────────────────────────────────────────
function SidebarLink({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      style={({ isActive }) => ({
        display: "flex",
        alignItems: "center",
        gap: "12px",
        width: "100%",
        background: isActive ? "rgba(249,115,22,0.15)" : "transparent",
        color: isActive ? "#f97316" : "#94a3b8",
        borderLeft: isActive ? "3px solid #f97316" : "3px solid transparent",
        padding: "12px 20px",
        fontWeight: isActive ? "600" : "500",
        fontSize: "14px",
        textDecoration: "none",
        whiteSpace: "nowrap",
        overflow: "hidden",
        transition: "all 0.15s",
        boxSizing: "border-box"
      })}
    >
      <span style={{ fontSize: "16px", flexShrink: 0 }}>{icon}</span>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{label}</span>
    </NavLink>
  );
}

function SectionHeader({ label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "16px 16px 8px" }}>
      <div style={{
        color: "#f97316", fontSize: "11px", fontWeight: "700",
        textTransform: "uppercase", letterSpacing: "1.5px", whiteSpace: "nowrap"
      }}>{label}</div>
      <div style={{ flex: 1, height: "1px", borderTop: "1px solid #2d4a38" }} />
    </div>
  );
}

// ── Layout — sidebar + main + AddToTripModal ─────────────────────────────────
function Layout({ setIsLoggedIn }) {
  const [addToTripOrder, setAddToTripOrder] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const navigate = useNavigate();

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0f172a", fontFamily: "Arial, sans-serif" }}>
      {/* SIDEBAR */}
      <aside style={{
        width: "240px", background: "#1e293b", borderRight: "1px solid #334155",
        display: "flex", flexDirection: "column", position: "sticky", top: 0, height: "100vh"
      }}>
        <div style={{ padding: "20px 20px 16px 20px", borderBottom: "1px solid #334155" }}>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#f97316" }}>🚛 Freight Planner</div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>TMS demo</div>
        </div>

        <nav style={{ paddingTop: "8px", flex: 1, overflowY: "auto" }}>
          <SectionHeader label="Operatiivinen" />
          <SidebarLink to="/dashboard" icon="📊" label="Dashboard" />
          <SidebarLink to="/trips" icon="🚛" label="Keikkalista" />
          <SidebarLink to="/orders" icon="📦" label="Orderit" />
          <SidebarLink to="/customers" icon="👥" label="Asiakkaat" />

          <SectionHeader label="Hallinta" />
          <SidebarLink to="/hallinta/kalusto" icon="🚛" label="Kalusto & Kumppanit" />
          <SidebarLink to="/hallinta/hinnoittelu" icon="💼" label="Hinnoittelu" />
          <SidebarLink to="/hallinta/asetukset" icon="⚙️" label="Asetukset" />

          <SectionHeader label="Työkalut" />
          <SidebarLink to="/calculator" icon="💰" label="Katelaskin" />
          <SidebarLink to="/costs-dashboard" icon="💸" label="Costs Dashboard" />
        </nav>

        <div style={{ padding: "16px 20px", borderTop: "1px solid #334155" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <div style={{
              width: "32px", height: "32px", borderRadius: "50%", background: "#f97316",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontWeight: "700", fontSize: "13px"
            }}>D</div>
            <div>
              <div style={{ color: "#f1f5f9", fontSize: "13px", fontWeight: "600" }}>demo</div>
              <div style={{ color: "#64748b", fontSize: "11px" }}>Pääkäyttäjä</div>
            </div>
          </div>
          <button
            onClick={() => setIsLoggedIn(false)}
            style={{
              width: "100%", background: "transparent", color: "#94a3b8",
              border: "1px solid #334155", padding: "8px 12px",
              borderRadius: "6px", cursor: "pointer", fontSize: "12px"
            }}
          >
            Kirjaudu ulos
          </button>
        </div>
      </aside>

      {/* MAIN */}
      <main style={{ flex: 1, padding: "32px 40px", overflowX: "hidden" }}>
        <Outlet context={{ setAddToTripOrder, refreshKey }} />
      </main>

      {/* AddToTripModal */}
      {addToTripOrder && (
        <AddToTripModal
          order={addToTripOrder}
          onClose={() => setAddToTripOrder(null)}
          onSuccess={() => {
            setAddToTripOrder(null);
            setRefreshKey(k => k + 1);
          }}
          onCreateNewTrip={() => {
            setAddToTripOrder(null);
            navigate("/trips/new");
          }}
        />
      )}
    </div>
  );
}

// ── App ──────────────────────────────────────────────────────────────────────
function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          {/* Julkinen reitti — ei vaadi kirjautumista */}
          <Route path="/driver/:trip_id" element={<DriverPage />} />

          {/* Kaikki muut: kirjautumislogiikka */}
          <Route path="*" element={
            !isLoggedIn ? (
              <Login onLogin={() => setIsLoggedIn(true)} />
            ) : (
              <Routes>
                <Route path="/" element={<Layout setIsLoggedIn={setIsLoggedIn} />}>
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="dashboard" element={<Dashboard />} />

                  <Route path="trips" element={<TripList />} />
                  <Route path="trips/new" element={<TripForm />} />
                  <Route path="trips/:id">
                    <Route index element={<Navigate to="orders" replace />} />
                    <Route path="edit" element={<TripForm />} />
                    <Route path=":tab" element={<TripDetail />} />
                  </Route>

                  <Route path="orders" element={<OrderList />} />
                  <Route path="orders/new" element={<OrderForm />} />
                  <Route path="orders/:id/edit" element={<OrderForm />} />

                  <Route path="customers" element={<CustomerList />} />
                  <Route path="customers/new" element={<CustomerForm />} />
                  <Route path="customers/:id/edit" element={<CustomerForm />} />

                  <Route path="carriers" element={<CarrierList />} />
                  <Route path="carriers/new" element={<CarrierForm />} />
                  <Route path="carriers/:id/edit" element={<CarrierForm />} />

                  <Route path="trailers" element={<TrailerList />} />
                  <Route path="trailers/new" element={<TrailerForm />} />
                  <Route path="trailers/:id/edit" element={<TrailerForm />} />

                  <Route path="fuel" element={<FuelRateManager />} />
                  <Route path="restrictions" element={<CountryRestrictionsPage />} />
                  <Route path="hallinta/kalusto" element={<HallintaKalusto />} />
                  <Route path="hallinta/hinnoittelu" element={<HallintaHinnoittelu />} />
                  <Route path="hallinta/asetukset" element={<HallintaAsetukset />} />
                  <Route path="calculator" element={<CostCalculator />} />
                  <Route path="costs-dashboard" element={<CostsDashboard />} />
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Route>
              </Routes>
            )
          } />
        </Routes>
      </BrowserRouter>
      <ToastContainer />
    </ToastProvider>
  );
}

export default App;
