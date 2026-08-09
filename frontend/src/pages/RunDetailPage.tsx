import { useState } from "react";
import { useParams } from "react-router-dom";
import { useRunDetail } from "../api/queries";
import { StatusPill } from "../components/StatusPill";
import type { TestRun } from "../api/types";

export function RunDetailPage() {
  const { runId } = useParams();
  const run = useRunDetail(runId ?? null);

  if (run.isLoading) return <p className="muted">Loading run…</p>;
  if (run.isError || !run.data) return <p className="error">Run not found.</p>;

  const r = run.data;

  return (
    <div className="stack">
      <div className="row spread">
        <h1>{r.suite_id}</h1>
        <StatusPill value={r.status} />
      </div>

      <div className="card">
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))" }}>
          <Meta label="Environment" value={r.environment_id} />
          <Meta label="Git branch" value={r.branch ?? "demo definitions"} />
          <Meta label="Commit SHA" value={r.commit_sha ? r.commit_sha.slice(0, 12) : "—"} />
          <Meta label="Started" value={r.started_at ? new Date(r.started_at).toLocaleString() : "—"} />
          <Meta label="Finished" value={r.finished_at ? new Date(r.finished_at).toLocaleString() : "—"} />
        </div>
      </div>

      <h2>Tests</h2>
      <div className="stack">
        {r.tests.map((t) => (
          <TestRow key={t.id} test={t} />
        ))}
      </div>
    </div>
  );
}

function TestRow({ test }: { test: TestRun }) {
  const [open, setOpen] = useState(false);
  const result = test.result_json as Record<string, unknown> | null;

  return (
    <div className="card">
      <div className="row spread interactive" onClick={() => setOpen((o) => !o)} style={{ cursor: "pointer" }}>
        <div className="row" style={{ gap: 12 }}>
          <span className="muted">{open ? "▾" : "▸"}</span>
          <span style={{ fontWeight: 600 }}>{test.test_id}</span>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <StatusPill value={test.execution_status} />
          <StatusPill value={test.final_verdict ?? "review_required"} label={`Final: ${test.final_verdict ?? "PENDING"}`} />
        </div>
      </div>

      {open && (
        <div className="stack" style={{ marginTop: 14 }}>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))" }}>
            <Meta label="Execution Status" value={test.execution_status} />
            <Meta label="Test Verdict" value={test.test_verdict ?? "null (AI-judged)"} />
            <Meta label="AI Verdict" value={test.ai_verdict ?? "pending"} />
            <Meta
              label="AI Confidence"
              value={test.ai_confidence != null ? `${Math.round(test.ai_confidence * 100)}%` : "—"}
            />
          </div>

          {result && Boolean((result.measurements as object) && Object.keys(result.measurements as object).length) && (
            <div>
              <h3>Measurements</h3>
              <pre className="terminal">{JSON.stringify(result.measurements, null, 2)}</pre>
            </div>
          )}
          {result && Array.isArray(result.observations) && (result.observations as unknown[]).length > 0 && (
            <div>
              <h3>Observations</h3>
              <ul className="secondary" style={{ margin: 0, paddingLeft: 18 }}>
                {(result.observations as string[]).map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            </div>
          )}
          {!result && (
            <p className="muted">
              No structured result (execution did not complete successfully).
            </p>
          )}
          <p className="muted" style={{ fontSize: 12 }}>
            AI review and final verdict are produced in later phases (7-8).
          </p>
        </div>
      )}
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 12 }}>
        {label}
      </div>
      <div style={{ marginTop: 2 }}>{value}</div>
    </div>
  );
}
