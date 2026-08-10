import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  useBranches,
  useCommits,
  useCreateRun,
  useGitConnections,
  usePrerequisites,
  useRepositories,
  useSuiteReadme,
  useSuites,
  useValidatePrerequisites,
} from "../api/queries";
import { PrerequisiteForm, isVisible } from "../components/PrerequisiteForm";
import { ApiError } from "../api/client";
import type { FieldError } from "../api/types";

const STEPS = ["Suite", "Environment", "Git Revision", "Review & Run"];

export function NewRunWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const [suiteId, setSuiteId] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<FieldError[]>([]);

  const [repository, setRepository] = useState<string | null>(null);
  const [branch, setBranch] = useState<string | null>(null);
  const [commit, setCommit] = useState<string | null>(null);

  const suites = useSuites();
  const readme = useSuiteReadme(suiteId);
  const prereqs = usePrerequisites(suiteId);
  const validate = useValidatePrerequisites();
  const createRun = useCreateRun();

  const gitConnections = useGitConnections();
  const connected = (gitConnections.data ?? []).length > 0;
  const repos = useRepositories(connected && step === 2);
  const branches = useBranches(repository);
  const commits = useCommits(repository, branch);

  const onChangeValue = (id: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [id]: value }));
  };

  // Environment tab: validate prerequisites on the backend before continuing.
  const goValidateThenNext = async () => {
    if (!suiteId) return;
    const res = await validate.mutateAsync({ suite_id: suiteId, values });
    setErrors(res.errors);
    if (res.status === "VALID") setStep(2);
  };

  const submit = async () => {
    if (!suiteId) return;
    const run = await createRun.mutateAsync({
      suite_id: suiteId,
      values,
      repository: repository ?? undefined,
      branch: branch ?? undefined,
      commit: commit ?? undefined,
    });
    navigate(`/runs/${run.id}`);
  };

  const visibleValueSummary = useMemo(() => {
    if (!prereqs.data) return [] as [string, unknown][];
    const out: [string, unknown][] = [];
    for (const s of prereqs.data.sections) {
      for (const f of s.fields) {
        if (f.type === "check") continue;
        if (isVisible(f, values) && values[f.id] !== undefined) {
          out.push([f.label, f.sensitive ? "••••••" : values[f.id]]);
        }
      }
    }
    return out;
  }, [prereqs.data, values]);

  return (
    <div className="stack">
      <h1>New Run</h1>
      <Stepper step={step} />

      {step === 0 && (
        <div className="grid">
          {(suites.data ?? []).map((s) => (
            <div
              key={s.id}
              className={`card interactive ${suiteId === s.id ? "selected" : ""}`}
              onClick={() => setSuiteId(s.id)}
            >
              <div style={{ fontWeight: 600 }}>{s.name}</div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                {s.description}
              </div>
              <div className="secondary" style={{ fontSize: 12, marginTop: 8 }}>
                {s.tests.length} tests
              </div>
            </div>
          ))}
        </div>
      )}

      {step === 1 && suiteId && (
        <div className="stack">
          {/* Suite README: purpose + connectivity (spec section 51). */}
          <div className="card">
            {readme.isLoading && <p className="muted">Loading suite details…</p>}
            {readme.data && readme.data.markdown ? (
              <div className="markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {readme.data.markdown}
                </ReactMarkdown>
              </div>
            ) : (
              !readme.isLoading && (
                <p className="muted">This suite has no README yet.</p>
              )
            )}
          </div>

          {/* Device details / prerequisite form. */}
          {prereqs.data ? (
            <PrerequisiteForm
              template={prereqs.data}
              suiteId={suiteId}
              values={values}
              errors={errors}
              onChange={onChangeValue}
            />
          ) : (
            prereqs.isLoading && <p className="muted">Loading prerequisite form…</p>
          )}
          {validate.isError && <p className="error">{(validate.error as ApiError).message}</p>}
        </div>
      )}

      {step === 2 && (
        <div className="card stack">
          <h3>Git Revision</h3>
          {!connected && (
            <p className="muted">
              You have not connected GitHub. You can still run using the built-in demo
              definitions, or connect GitHub from the Git Connection page.
            </p>
          )}
          {connected && (
            <>
              <div className="field">
                <label>Repository</label>
                <select
                  className="select"
                  value={repository ?? ""}
                  onChange={(e) => {
                    setRepository(e.target.value || null);
                    setBranch(null);
                    setCommit(null);
                  }}
                >
                  <option value="">Use built-in demo definitions</option>
                  {(repos.data ?? []).map((r) => (
                    <option key={r.id} value={r.full_name}>
                      {r.full_name}
                    </option>
                  ))}
                </select>
              </div>
              {repository && (
                <div className="field">
                  <label>Branch</label>
                  <select
                    className="select"
                    value={branch ?? ""}
                    onChange={(e) => {
                      setBranch(e.target.value || null);
                      setCommit(null);
                    }}
                  >
                    <option value="">Select branch…</option>
                    {(branches.data ?? []).map((b) => (
                      <option key={b.name} value={b.name}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {repository && branch && (
                <div className="field">
                  <label>Commit (optional — defaults to latest)</label>
                  <select
                    className="select"
                    value={commit ?? ""}
                    onChange={(e) => setCommit(e.target.value || null)}
                  >
                    <option value="">Latest on {branch}</option>
                    {(commits.data ?? []).map((c) => (
                      <option key={c.sha} value={c.sha}>
                        {c.sha.slice(0, 8)} — {c.message}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {step === 3 && (
        <div className="card stack">
          <h3>Review & Run</h3>
          <SummaryRow label="Suite" value={suiteId} />
          <SummaryRow
            label="Git"
            value={repository ? `${repository} @ ${branch}${commit ? ` (${commit.slice(0, 8)})` : " (latest)"}` : "Built-in demo definitions"}
          />
          <div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
              Device details / prerequisites
            </div>
            {visibleValueSummary.map(([label, val]) => (
              <div key={label} className="row spread" style={{ fontSize: 13 }}>
                <span className="secondary">{label}</span>
                <span>{String(val)}</span>
              </div>
            ))}
          </div>
          {createRun.isError && (
            <p className="error">{(createRun.error as ApiError).message}</p>
          )}
        </div>
      )}

      <div className="row spread" style={{ marginTop: 8 }}>
        <button className="btn" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          Back
        </button>
        <NextButton
          step={step}
          canProceed={{ 0: !!suiteId, 1: true, 2: true, 3: true }}
          validating={validate.isPending}
          submitting={createRun.isPending}
          onNext={() => {
            if (step === 1) void goValidateThenNext();
            else setStep((s) => s + 1);
          }}
          onSubmit={() => void submit()}
        />
      </div>
    </div>
  );
}

function NextButton({
  step,
  canProceed,
  validating,
  submitting,
  onNext,
  onSubmit,
}: {
  step: number;
  canProceed: Record<number, boolean>;
  validating: boolean;
  submitting: boolean;
  onNext: () => void;
  onSubmit: () => void;
}) {
  if (step === STEPS.length - 1) {
    return (
      <button className="btn primary" disabled={submitting} onClick={onSubmit}>
        {submitting ? "Starting…" : "Start Run"}
      </button>
    );
  }
  const label = step === 1 ? (validating ? "Validating…" : "Validate & Continue") : "Next";
  return (
    <button className="btn primary" disabled={!canProceed[step] || validating} onClick={onNext}>
      {label}
    </button>
  );
}

function Stepper({ step }: { step: number }) {
  return (
    <div className="row wrap" style={{ gap: 8 }}>
      {STEPS.map((s, i) => (
        <span
          key={s}
          className="pill"
          style={{
            color: i === step ? "var(--text)" : "var(--text-muted)",
            background: i === step ? "var(--surface-elevated)" : "transparent",
            border: `1px solid ${i <= step ? "var(--border-bright)" : "var(--border)"}`,
          }}
        >
          {i + 1}. {s}
        </span>
      ))}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="row spread" style={{ fontSize: 13 }}>
      <span className="secondary">{label}</span>
      <span>{value ?? "—"}</span>
    </div>
  );
}
