import React, { useState } from "react";
import Login from "./components/Login";
import OrderList from "./components/OrderList";
import OrderForm from "./components/OrderForm";
import TripList from "./components/TripList";
import TripForm from "./components/TripForm";
import TripDetail from "./components/TripDetail";
import CostCalculator from "./components/CostCalculator";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentView, setCurrentView] = useState("trips");
  const [orderView, setOrderView] = useState("list");
  const [tripView, setTripView] = useState("list");
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [selectedTripId, setSelectedTripId] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  if (!isLoggedIn) {
    return <Login onLogin={() => setIsLoggedIn(true)} />;
  }

  const sidebarItem = (view, icon, label) => (
    <button
      onClick={() => {
        setCurrentView(view);
        setOrderView("list");
        setTripView("list");
      }}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        width: "100%",
        background: currentView === view ? "rgba(249,115,22,0.15)" : "transparent",
        color: currentView === view ? "#f97316" : "#94a3b8",
        border: "none",
        borderLeft: currentView === view ? "3px solid #f97316" : "3px solid transparent",
        padding: "12px 20px",
        cursor: "pointer",
        fontWeight: currentView === view ? "600" : "500",
        fontSize: "14px",
        textAlign: "left",
        transition: "all 0.15s"
      }}
    >
      <span style={{ fontSize: "18px" }}>{icon}</span>
      {label}
    </button>
  );

  return (
    <div style={{
      display: "flex",
      minHeight: "100vh",
      background: "#0f172a",
      fontFamily: "Arial, sans-serif"
    }}>
      {/* SIDEBAR */}
      <aside style={{
        width: "240px",
        background: "#1e293b",
        borderRight: "1px solid #334155",
        display: "flex",
        flexDirection: "column",
        position: "sticky",
        top: 0,
        height: "100vh"
      }}>
        <div style={{
          padding: "20px 20px 16px 20px",
          borderBottom: "1px solid #334155"
        }}>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#f97316" }}>
            🚛 Freight Planner
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
            TMS demo
          </div>
        </div>

        <nav style={{ paddingTop: "12px", flex: 1 }}>
          <div style={{
            padding: "8px 20px",
            color: "#475569",
            fontSize: "10px",
            fontWeight: "700",
            textTransform: "uppercase",
            letterSpacing: "1px"
          }}>
            Operatiivinen
          </div>
          {sidebarItem("trips", "🚚", "Trips")}
          {sidebarItem("orders", "📦", "Orderit")}

          <div style={{
            padding: "16px 20px 8px",
            color: "#475569",
            fontSize: "10px",
            fontWeight: "700",
            textTransform: "uppercase",
            letterSpacing: "1px"
          }}>
            Työkalut
          </div>
          {sidebarItem("calculator", "💰", "Kustannuslaskin")}
        </nav>

        <div style={{
          padding: "16px 20px",
          borderTop: "1px solid #334155"
        }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            marginBottom: "12px"
          }}>
            <div style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              background: "#f97316",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontWeight: "700",
              fontSize: "13px"
            }}>
              D
            </div>
            <div>
              <div style={{ color: "#f1f5f9", fontSize: "13px", fontWeight: "600" }}>
                demo
              </div>
              <div style={{ color: "#64748b", fontSize: "11px" }}>
                Pääkäyttäjä
              </div>
            </div>
          </div>
          <button
            onClick={() => setIsLoggedIn(false)}
            style={{
              width: "100%",
              background: "transparent",
              color: "#94a3b8",
              border: "1px solid #334155",
              padding: "8px 12px",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "12px"
            }}
          >
            Kirjaudu ulos
          </button>
        </div>
      </aside>

      {/* MAIN */}
      <main style={{ flex: 1, padding: "32px 40px", overflowX: "hidden" }}>
        {/* TRIPS */}
        {currentView === "trips" && tripView === "list" && (
          <TripList
            refreshTrigger={refreshTrigger}
            onSelect={(id) => {
              setSelectedTripId(id);
              setTripView("detail");
            }}
            onCreate={() => {
              setSelectedTripId(null);
              setTripView("create");
            }}
          />
        )}
        {currentView === "trips" && tripView === "detail" && (
          <TripDetail
            tripId={selectedTripId}
            onBack={() => setTripView("list")}
            onEdit={() => setTripView("edit")}
            refreshTrigger={refreshTrigger}
            triggerRefresh={() => setRefreshTrigger(t => t + 1)}
          />
        )}
        {currentView === "trips" && (tripView === "create" || tripView === "edit") && (
          <TripForm
            tripId={tripView === "edit" ? selectedTripId : null}
            onSave={(id) => {
              setSelectedTripId(id);
              setTripView("detail");
              setRefreshTrigger(t => t + 1);
            }}
            onCancel={() => setTripView(tripView === "edit" ? "detail" : "list")}
          />
        )}

        {/* ORDERS */}
        {currentView === "orders" && orderView === "list" && (
          <OrderList
            refreshTrigger={refreshTrigger}
            onSelect={(id) => {
              setSelectedOrderId(id);
              setOrderView("edit");
            }}
            onCreate={() => {
              setSelectedOrderId(null);
              setOrderView("create");
            }}
          />
        )}
        {currentView === "orders" && (orderView === "create" || orderView === "edit") && (
          <OrderForm
            orderId={orderView === "edit" ? selectedOrderId : null}
            onSave={() => {
              setOrderView("list");
              setRefreshTrigger(t => t + 1);
            }}
            onCancel={() => setOrderView("list")}
          />
        )}

        {currentView === "calculator" && (
          <CostCalculator />
        )}
      </main>
    </div>
  );
}

export default App;