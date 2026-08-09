import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useBranches,
  useCommits,
  useCompatibleEnvironments,
  useCreateRun,
  useGitConnections,
  usePrerequisites,
  useRepositories,
  useSuites,
  useValidatePrerequisites,
} from "../api/queries";
import { PrerequisiteForm, isVisible } from "../components/PrerequisiteForm";
import { ApiError } from "../api/client";
import type { FieldError } from "../api/types";

const STEPS = ["Suite", "Environment", "Prerequisites", "Git Revision", "Review & Run"];

export function NewRunWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const [suiteId, setSuiteId] = useState<string | null>(null);
  const [environmentId, setEnvironmentId] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<FieldError[]>([]);

  const [repository, setRepository] = useState<string | null>(null);
  const [branch, setBranch] = useState<string | null>(null);
  const [commit, setCommit] = useState<string | null>(null);

  const suites = useSuites();
  const envs = useCompatibleEnvironments(suiteId);
  const prereqs = usePrerequisites(suiteId, environmentId);
  const validate = useValidatePrerequisites();
  const createRun = useCreateRun();

  const gitConnections = useGitConnections();
  const connected = (gitConnections.data ?? []).length > 0;
  const repos = useRepositories(connected && step === 3);
  const branches = useBranches(repository);
  const commits = useCommits(repository, branch);

  const onChangeValue = (id: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [id]: value }));
  };

  const goValidateThenNext = async () => {
    if (!suiteId || !environmentId) return;
    const res = await validate.mutateAsync({
      suite_id: suiteId,
      environment_id: environmentId,
      values,
    });
    setErrors(res.errors);
    if (res.status === "VALID") setStep(3);
  };

  const submit = async () => {
    if (!suiteId || !environmentId) return;
    const run = await createRun.mutateAsync({
      suite_id: suiteId,
      environment_id: environmentId,
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
              onClick={() => {
                setSuiteId(s.id);
                setEnvironmentId(null);
              }}
            >
              <div style={{ fontWeight: 600 }}>{s.name}</div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                {s.description}
              </div>
              <div className="secondary" style={{ fontSize: 12, marginTop: 8 }}>
                {s.tests.length} tests · caps: {s.requirements.capabilities.join(", ")}
              </div>
            </div>
          ))}
        </div>
      )}

      {step === 1 && (
        <div className="grid">
          {envs.isLoading && <p className="muted">Finding compatible environments…</p>}
          {envs.data?.length === 0 && (
            <p className="muted">No compatible environments for this suite.</p>
          )}
          {(envs.data ?? []).map((c) => (
            <div
              key={c.environment.id}
              className={`card interactive ${environmentId === c.environment.id ? "selected" : ""}`}
              onClick={() => setEnvironmentId(c.environment.id)}
            >
              <div style={{ fontWeight: 600 }}>{c.environment.name}</div>
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                {c.environment.platform} · {c.environment.system_type} ·{" "}
                {c.environment.software_version}
              </div>
              <div className="secondary" style={{ fontSize: 12, marginTop: 8 }}>
                {c.environment.capabilities.join(", ")}
              </div>
            </div>
          ))}
        </div>
      )}

      {step === 2 && prereqs.data && suiteId && environmentId && (
        <>
          <PrerequisiteForm
            template={prereqs.data}
            suiteId={suiteId}
            environmentId={environmentId}
            values={values}
            errors={errors}
            onChange={onChangeValue}
          />
          {validate.isError && (
            <p className="error">{(validate.error as ApiError).message}</p>
          )}
        </>
      )}

      {step === 3 && (
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

      {step === 4 && (
        <div className="card stack">
          <h3>Review & Run</h3>
          <SummaryRow label="Suite" value={suiteId} />
          <SummaryRow label="Environment" value={environmentId} />
          <SummaryRow
            label="Git"
            value={repository ? `${repository} @ ${branch}${commit ? ` (${commit.slice(0, 8)})` : " (latest)"}` : "Built-in demo definitions"}
          />
          <div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
              Prerequisites
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
          canProceed={{
            0: !!suiteId,
            1: !!environmentId,
            2: true,
            3: true,
            4: true,
          }}
          validating={validate.isPending}
          submitting={createRun.isPending}
          onNext={() => {
            if (step === 2) void goValidateThenNext();
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
  const label = step === 2 ? (validating ? "Validating…" : "Validate & Continue") : "Next";
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
