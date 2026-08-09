import { useState } from "react";
import { useConnectGit, useGitConnections, useRepositories } from "../api/queries";
import { ApiError } from "../api/client";

export function GitConnectPage() {
  const connections = useGitConnections();
  const connect = useConnectGit();
  const [token, setToken] = useState("");

  const connected = (connections.data ?? []).length > 0;
  const repos = useRepositories(connected);

  return (
    <div className="stack" style={{ maxWidth: 640 }}>
      <h1>Git Connection</h1>
      <p className="secondary">
        Connect your own GitHub account. The app uses your access to list repositories,
        branches and commits. Your token is encrypted at rest and never shown again.
      </p>

      {connected ? (
        <div className="card">
          <div className="row spread">
            <div>
              <div style={{ fontWeight: 600 }}>Connected to GitHub</div>
              <div className="muted" style={{ fontSize: 13 }}>
                {connections.data![0].external_username ?? "unknown"} ·{" "}
                {connections.data![0].scopes}
              </div>
            </div>
            <span className="pill passed">
              <span className="dot" />
              Connected
            </span>
          </div>
        </div>
      ) : (
        <div className="card">
          <h3>Connect with a personal access token</h3>
          <p className="muted" style={{ fontSize: 13 }}>
            Create a read-only token in GitHub and paste it here. OAuth is also supported
            when configured by an administrator.
          </p>
          <div className="field">
            <label htmlFor="pat">GitHub token</label>
            <input
              id="pat"
              className="input"
              type="password"
              value={token}
              placeholder="ghp_…"
              onChange={(e) => setToken(e.target.value)}
            />
          </div>
          {connect.isError && (
            <div className="error" style={{ marginBottom: 10 }}>
              {(connect.error as ApiError).message}
            </div>
          )}
          <button
            className="btn primary"
            disabled={!token || connect.isPending}
            onClick={() => connect.mutate(token)}
          >
            {connect.isPending ? "Connecting…" : "Connect"}
          </button>
        </div>
      )}

      {connected && (
        <div className="card">
          <h3>Accessible repositories</h3>
          {repos.isLoading && <p className="muted">Loading repositories…</p>}
          {repos.isError && (
            <p className="error">{(repos.error as ApiError).message}</p>
          )}
          <div className="stack" style={{ maxHeight: 260, overflow: "auto" }}>
            {(repos.data ?? []).map((r) => (
              <div key={r.id} className="row spread" style={{ fontSize: 13 }}>
                <span>{r.full_name}</span>
                <span className="muted">{r.private ? "private" : "public"}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
