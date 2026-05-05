import React, { useState } from "react";

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setError("");
    if (!username || !password) {
      setError("Täytä käyttäjätunnus ja salasana.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:5000/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      const data = await response.json();
      if (response.ok && data.success) {
        onLogin();
      } else {
        setError(data.message || "Kirjautuminen epäonnistui.");
      }
    } catch (err) {
      setError("Palvelinyhteys epäonnistui.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0f172a",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "Arial, sans-serif"
    }}>
      <div style={{
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(249,115,22,0.4)",
        borderRadius: "16px",
        padding: "48px",
        width: "100%",
        maxWidth: "400px",
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)"
      }}>
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{ fontSize: "48px", marginBottom: "12px" }}>🚛</div>
          <h1 style={{
            color: "#f97316",
            fontSize: "24px",
            fontWeight: "700",
            margin: 0
          }}>
            Freight Planner
          </h1>
          <p style={{ color: "#94a3b8", marginTop: "8px", fontSize: "14px" }}>
            Kirjaudu sisään jatkaaksesi
          </p>
        </div>

        {error && (
          <div style={{
            background: "rgba(239,68,68,0.15)",
            border: "1px solid rgba(239,68,68,0.4)",
            borderRadius: "8px",
            padding: "12px 16px",
            color: "#fca5a5",
            marginBottom: "16px",
            fontSize: "14px"
          }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: "16px" }}>
          <label style={{
            display: "block",
            color: "#94a3b8",
            fontSize: "13px",
            marginBottom: "6px"
          }}>
            Käyttäjätunnus
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="demo"
            style={{
              width: "100%",
              padding: "10px 14px",
              borderRadius: "8px",
              border: "1px solid #475569",
              background: "rgba(255,255,255,0.05)",
              color: "#f1f5f9",
              fontSize: "14px",
              outline: "none",
              boxSizing: "border-box"
            }}
          />
        </div>

        <div style={{ marginBottom: "24px" }}>
          <label style={{
            display: "block",
            color: "#94a3b8",
            fontSize: "13px",
            marginBottom: "6px"
          }}>
            Salasana
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="••••••••"
            style={{
              width: "100%",
              padding: "10px 14px",
              borderRadius: "8px",
              border: "1px solid #475569",
              background: "rgba(255,255,255,0.05)",
              color: "#f1f5f9",
              fontSize: "14px",
              outline: "none",
              boxSizing: "border-box"
            }}
          />
        </div>

        <button
          onClick={handleLogin}
          disabled={loading}
          style={{
            width: "100%",
            padding: "12px",
            borderRadius: "8px",
            border: "none",
            background: loading ? "#475569" : "#f97316",
            color: "#fff",
            fontWeight: "700",
            fontSize: "15px",
            cursor: loading ? "not-allowed" : "pointer"
          }}
        >
          {loading ? "Kirjaudutaan..." : "Kirjaudu sisään"}
        </button>

        <div style={{
          marginTop: "24px",
          padding: "12px 16px",
          background: "rgba(255,255,255,0.03)",
          borderRadius: "8px",
          border: "1px solid rgba(255,255,255,0.08)"
        }}>
          <p style={{ color: "#64748b", fontSize: "12px", margin: 0 }}>
            Demo-tunnukset:
          </p>
          <p style={{ color: "#94a3b8", fontSize: "12px", margin: "4px 0 0" }}>
            Käyttäjätunnus: <strong style={{ color: "#f1f5f9" }}>demo</strong>
          </p>
          <p style={{ color: "#94a3b8", fontSize: "12px", margin: "2px 0 0" }}>
            Salasana: <strong style={{ color: "#f1f5f9" }}>freight2024</strong>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;