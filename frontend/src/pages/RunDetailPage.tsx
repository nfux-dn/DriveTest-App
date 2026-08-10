import { useState } from "react";
import { useParams } from "react-router-dom";
import { useRunDetail, useRunReport, useTestRunDetail } from "../api/queries";
import { StatusPill } from "../components/StatusPill";
import type { AiEvaluation, RunReport, TestRun } from "../api/types";

export function RunDetailPage() {
  const { runId } = useParams();
  const run = useRunDetail(runId ?? null);
  const isActive = run.data?.status === "RUNNING" || run.data?.status === "PENDING";
  const report = useRunReport(runId ?? null, isActive);

  if (run.isLoading) return <p className="muted">Loading run…</p>;
  if (run.isError || !run.data) return <p className="error">Run not found.</p>;

  const r = run.data;

  return (
    <div className="stack report-root">
      <div className="row spread no-print">
        <h1>{r.suite_id}</h1>
        <div className="row" style={{ gap: 10 }}>
          <StatusPill value={r.status} />
          <button className="btn" onClick={() => window.print()}>
            Print report
          </button>
        </div>
      </div>

      <div className="card">
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))" }}>
          <Meta label="Git branch" value={r.branch ?? "demo definitions"} />
          <Meta label="Commit SHA" value={r.commit_sha ? r.commit_sha.slice(0, 12) : "—"} />
          <Meta label="Requested by" value={r.user_id.slice(0, 8)} />
          <Meta label="Started" value={fmt(r.started_at)} />
          <Meta label="Finished" value={fmt(r.finished_at)} />
        </div>
      </div>

      {report.data && <Summary report={report.data} />}

      <h2>Tests</h2>
      <div className="stack">
        {r.tests.map((t) => (
          <TestRow key={t.id} test={t} />
        ))}
      </div>
    </div>
  );
}

function Summary({ report }: { report: RunReport }) {
  const cells: [string, number, string][] = [
    ["Passed", report.passed, "passed"],
    ["Failed", report.failed, "failed"],
    ["Review", report.review_required, "review_required"],
    ["Script errors", report.script_error, "script_error"],
    ["Infra errors", report.infra_error, "infra_error"],
    ["Timeouts", report.timeout, "timeout"],
  ];
  return (
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(140px,1fr))" }}>
      {cells.map(([label, value, cls]) => (
        <div key={label} className="card">
          <div className="row spread">
            <span className="muted" style={{ fontSize: 12 }}>
              {label}
            </span>
            <span className={`pill ${cls}`} style={{ padding: "1px 8px" }}>
              <span className="dot" />
              {value}
            </span>
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, marginTop: 6 }}>{value}</div>
        </div>
      ))}
    </div>
  );
}

function TestRow({ test }: { test: TestRun }) {
  const [open, setOpen] = useState(false);
  const detail = useTestRunDetail(test.id, open);
  const result = test.result_json as Record<string, unknown> | null;
  const disagreement =
    test.test_verdict != null &&
    test.ai_verdict != null &&
    test.test_verdict !== test.ai_verdict;

  return (
    <div className="card">
      <div
        className="row spread"
        onClick={() => setOpen((o) => !o)}
        style={{ cursor: "pointer" }}
      >
        <div className="row" style={{ gap: 12 }}>
          <span className="muted">{open ? "▾" : "▸"}</span>
          <span style={{ fontWeight: 600 }}>{test.test_id}</span>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <StatusPill value={test.execution_status} />
          <FinalVerdictPill test={test} />
        </div>
      </div>

      {open && (
        <div className="stack" style={{ marginTop: 14 }}>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))" }}>
            <Meta label="Execution Status" value={test.execution_status} />
            <Meta label="Test Verdict" value={test.test_verdict ?? "null (AI-judged)"} />
            <Meta label="AI Verdict" value={test.ai_verdict ?? "—"} />
            <Meta
              label="AI Confidence"
              value={test.ai_confidence != null ? `${Math.round(test.ai_confidence * 100)}%` : "—"}
            />
          </div>

          {disagreement && (
            <div className="pill review_required" style={{ alignSelf: "flex-start" }}>
              <span className="dot" />
              Test and AI verdicts disagree — final verdict reflects the rule, not a hidden override.
            </div>
          )}

          {result && hasContent(result.measurements) && (
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

          {detail.data?.ai && <AiReview ai={detail.data.ai} />}
          {detail.isLoading && <p className="muted">Loading AI review…</p>}
          {!detail.isLoading && detail.data && !detail.data.ai && (
            <p className="muted">
              No AI review (execution did not complete successfully).
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// AI review styled as an engineering assistant, not a chatbot (spec section 36).
function AiReview({ ai }: { ai: AiEvaluation }) {
  const a = ai.analysis ?? {};
  return (
    <div className="card" style={{ background: "var(--surface-elevated)" }}>
      <div className="row spread">
        <h3 style={{ margin: 0 }}>AI Review</h3>
        <span className="muted" style={{ fontSize: 12 }}>
          {ai.model} · prompt {ai.prompt_version}
        </span>
      </div>

      {ai.summary && (
        <Section title="Summary">
          <p style={{ margin: 0 }}>{ai.summary}</p>
        </Section>
      )}
      {a.anomalies && a.anomalies.length > 0 && (
        <Section title="Anomalies">
          <ul style={{ margin: 0, paddingLeft: 18, color: "var(--warning)" }}>
            {a.anomalies.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </Section>
      )}
      {a.evidence && a.evidence.length > 0 && (
        <Section title="Evidence">
          <ul className="secondary" style={{ margin: 0, paddingLeft: 18 }}>
            {a.evidence.map((e, i) => (
              <li key={i}>
                <span className="muted">[{e.source}]</span> {e.details}
              </li>
            ))}
          </ul>
        </Section>
      )}
      {a.likely_root_cause && (
        <Section title="Likely Root Cause">
          <p style={{ margin: 0 }}>{a.likely_root_cause}</p>
        </Section>
      )}
      {a.recommended_next_step && (
        <Section title="Recommended Next Step">
          <p style={{ margin: 0 }}>{a.recommended_next_step}</p>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 12 }}>
      <div className="muted" style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5 }}>
        {title}
      </div>
      <div style={{ marginTop: 4 }}>{children}</div>
    </div>
  );
}

function FinalVerdictPill({ test }: { test: TestRun }) {
  if (test.execution_status !== "COMPLETED") {
    return <span className="pill" style={{ color: "var(--text-muted)" }}>No verdict</span>;
  }
  const value = test.final_verdict ?? "review_required";
  return <StatusPill value={value} label={`Final: ${test.final_verdict ?? "PENDING"}`} />;
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

function fmt(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function hasContent(value: unknown): boolean {
  return !!value && typeof value === "object" && Object.keys(value as object).length > 0;
}
