import { Link } from "react-router-dom";
import { useRuns, useSyncSuites } from "../api/queries";
import { StatusPill } from "../components/StatusPill";
import { ApiError } from "../api/client";
import type { Run } from "../api/types";

export function DashboardPage() {
  const runs = useRuns();
  const syncSuites = useSyncSuites();

  const list = runs.data ?? [];
  const stats = summarize(list);

  return (
    <div className="stack">
      <div className="row spread">
        <h1>Dashboard</h1>
        <div className="row" style={{ gap: 8 }}>
          <button
            className="btn"
            disabled={syncSuites.isPending}
            onClick={() => syncSuites.mutate()}
            title="Re-index the suite catalog from the suites Git repository"
          >
            {syncSuites.isPending ? "Syncing…" : "Sync suites"}
          </button>
          <Link to="/runs/new" className="btn primary">
            New Run
          </Link>
        </div>
      </div>

      {syncSuites.isSuccess && (
        <p className="muted" style={{ fontSize: 13 }}>
          Synced {syncSuites.data.suites} suite(s) from {syncSuites.data.repository}@
          {syncSuites.data.branch}
          {syncSuites.data.commit ? ` (${syncSuites.data.commit.slice(0, 8)})` : ""}.
        </p>
      )}
      {syncSuites.isError && (
        <p className="error" style={{ fontSize: 13 }}>
          {(syncSuites.error as ApiError).message}
        </p>
      )}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))" }}>
        <Stat label="Total runs" value={list.length} />
        <Stat label="Running" value={stats.running} />
        <Stat label="Completed" value={stats.completed} />
        <Stat label="Failed" value={stats.failed} />
      </div>

      <h2 style={{ marginTop: 12 }}>Recent runs</h2>
      {list.length === 0 && <p className="muted">No runs yet. Start one from New Run.</p>}
      <div className="stack">
        {list.map((run) => (
          <Link key={run.id} to={`/runs/${run.id}`} style={{ color: "inherit" }}>
            <div className="card interactive row spread">
              <div>
                <div style={{ fontWeight: 600 }}>{run.suite_id}</div>
                <div className="muted" style={{ fontSize: 12 }}>
                  {new Date(run.created_at).toLocaleString()}
                </div>
              </div>
              <StatusPill value={run.status} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function summarize(runs: Run[]) {
  return {
    running: runs.filter((r) => r.status === "RUNNING" || r.status === "PENDING").length,
    completed: runs.filter((r) => r.status === "COMPLETED").length,
    failed: runs.filter((r) => r.status === "FAILED").length,
  };
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="card">
      <div className="muted" style={{ fontSize: 12 }}>
        {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}
