import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../services/api";
import { useAuth } from "../App";

export default function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();

  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const fn = mode === "login" ? login : register;
      const res = await fn(email, password);
      signIn(res.data.token, res.data.user);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.error || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="card" style={{ width: "100%", maxWidth: 380 }}>
        <h1 style={{ marginBottom: "0.25rem", fontSize: "1.4rem" }}>AI Cost Tracker</h1>
        <p className="muted" style={{ marginBottom: "1.5rem", fontSize: "0.85rem" }}>
          {mode === "login" ? "Sign in to your account" : "Create a new account"}
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "0.75rem" }}>
            <label style={{ fontSize: "0.85rem", display: "block", marginBottom: "0.3rem" }}>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ fontSize: "0.85rem", display: "block", marginBottom: "0.3rem" }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </div>
          {error && <p className="error-msg">{error}</p>}
          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ width: "100%", marginTop: "0.75rem", padding: "0.65rem" }}
          >
            {loading ? "Please wait…" : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        <p style={{ marginTop: "1rem", fontSize: "0.85rem", textAlign: "center" }}>
          {mode === "login" ? (
            <>No account? <button className="btn-ghost" style={{ padding: "2px 8px", fontSize: "0.85rem" }} onClick={() => setMode("register")}>Register</button></>
          ) : (
            <>Have an account? <button className="btn-ghost" style={{ padding: "2px 8px", fontSize: "0.85rem" }} onClick={() => setMode("login")}>Sign In</button></>
          )}
        </p>
      </div>
    </div>
  );
}
