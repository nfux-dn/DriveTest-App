import { Link } from "react-router-dom";
import { useRuns } from "../api/queries";
import { StatusPill } from "../components/StatusPill";
import type { Run } from "../api/types";

export function DashboardPage() {
  const runs = useRuns();

  const list = runs.data ?? [];
  const stats = summarize(list);

  return (
    <div className="stack">
      <div className="row spread">
        <h1>Dashboard</h1>
        <Link to="/runs/new" className="btn primary">
          New Run
        </Link>
      </div>

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
                  {run.environment_id} · {new Date(run.created_at).toLocaleString()}
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
