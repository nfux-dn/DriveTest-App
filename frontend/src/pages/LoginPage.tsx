import { useState } from "react";
import { useLogin } from "../api/queries";
import { ApiError } from "../api/client";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const login = useLogin();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login.mutate({ email, display_name: displayName || undefined });
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 20,
      }}
    >
      <div className="card" style={{ width: 380 }}>
        <h1>
          Drive<span style={{ color: "var(--info)" }}>Test</span>
        </h1>
        <p className="secondary" style={{ marginTop: -4 }}>
          Network Test Orchestration Platform
        </p>
        <form onSubmit={onSubmit} style={{ marginTop: 18 }}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="input"
              type="email"
              required
              value={email}
              placeholder="engineer@example.com"
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="name">Display name (optional)</label>
            <input
              id="name"
              className="input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
          {login.isError && (
            <div className="error" style={{ marginBottom: 10 }}>
              {(login.error as ApiError).message}
            </div>
          )}
          <button className="btn primary" style={{ width: "100%" }} disabled={login.isPending}>
            {login.isPending ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
