// Renders a prerequisite template into a live form (spec sections 11-13).
// Visibility (visible_when) is evaluated client-side for UX; the backend is the
// authoritative validator.

import { useRunCheck } from "../api/queries";
import type {
  CheckRunResponse,
  FieldError,
  PrerequisiteField,
  PrerequisiteTemplate,
} from "../api/types";

interface Props {
  template: PrerequisiteTemplate;
  suiteId: string;
  environmentId: string;
  values: Record<string, unknown>;
  errors: FieldError[];
  onChange: (id: string, value: unknown) => void;
}

export function isVisible(field: PrerequisiteField, values: Record<string, unknown>): boolean {
  if (!field.visible_when) return true;
  return values[field.visible_when.field] === field.visible_when.equals;
}

export function PrerequisiteForm({
  template,
  suiteId,
  environmentId,
  values,
  errors,
  onChange,
}: Props) {
  const errorFor = (id: string) => errors.find((e) => e.field_id === id)?.message;

  return (
    <div className="stack">
      {template.sections.map((section) => (
        <div key={section.id} className="card">
          <h3>{section.title}</h3>
          {section.fields.filter((f) => isVisible(f, values)).map((field) => (
            <FieldRenderer
              key={field.id}
              field={field}
              value={values[field.id]}
              error={errorFor(field.id)}
              suiteId={suiteId}
              environmentId={environmentId}
              values={values}
              onChange={onChange}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function FieldRenderer({
  field,
  value,
  error,
  suiteId,
  environmentId,
  values,
  onChange,
}: {
  field: PrerequisiteField;
  value: unknown;
  error: string | undefined;
  suiteId: string;
  environmentId: string;
  values: Record<string, unknown>;
  onChange: (id: string, value: unknown) => void;
}) {
  return (
    <div className="field">
      <label htmlFor={field.id}>
        {field.label}
        {field.required && <span style={{ color: "var(--failure)" }}> *</span>}
      </label>
      {field.description && <span className="hint">{field.description}</span>}
      <FieldInput field={field} value={value} onChange={onChange} />
      {field.type === "check" && (
        <CheckField
          field={field}
          suiteId={suiteId}
          environmentId={environmentId}
          values={values}
        />
      )}
      {error && <span className="error">{error}</span>}
    </div>
  );
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: PrerequisiteField;
  value: unknown;
  onChange: (id: string, value: unknown) => void;
}) {
  switch (field.type) {
    case "textarea":
      return (
        <textarea
          id={field.id}
          className="textarea"
          rows={3}
          value={(value as string) ?? ""}
          placeholder={field.placeholder ?? ""}
          onChange={(e) => onChange(field.id, e.target.value)}
        />
      );
    case "boolean":
    case "confirmation":
      return (
        <label className="row" style={{ gap: 8 }}>
          <input
            id={field.id}
            type="checkbox"
            checked={value === true}
            onChange={(e) => onChange(field.id, e.target.checked)}
          />
          <span className="muted" style={{ fontSize: 13 }}>
            {field.type === "confirmation" ? "I confirm this is done" : "Enabled"}
          </span>
        </label>
      );
    case "select":
      return (
        <select
          id={field.id}
          className="select"
          value={(value as string) ?? ""}
          onChange={(e) => onChange(field.id, e.target.value || undefined)}
        >
          <option value="">Select…</option>
          {field.options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      );
    case "multiselect":
      return (
        <div className="stack" style={{ gap: 6 }}>
          {field.options.map((o) => {
            const arr = Array.isArray(value) ? (value as string[]) : [];
            return (
              <label key={o} className="row" style={{ gap: 8 }}>
                <input
                  type="checkbox"
                  checked={arr.includes(o)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...arr, o]
                      : arr.filter((x) => x !== o);
                    onChange(field.id, next);
                  }}
                />
                <span style={{ fontSize: 13 }}>{o}</span>
              </label>
            );
          })}
        </div>
      );
    case "check":
      return null;
    case "number":
    case "integer":
      return (
        <input
          id={field.id}
          className="input"
          type="number"
          value={(value as string) ?? ""}
          placeholder={field.placeholder ?? ""}
          onChange={(e) =>
            onChange(field.id, e.target.value === "" ? undefined : Number(e.target.value))
          }
        />
      );
    default:
      return (
        <input
          id={field.id}
          className="input"
          type={field.sensitive ? "password" : "text"}
          value={(value as string) ?? ""}
          placeholder={field.placeholder ?? ""}
          onChange={(e) => onChange(field.id, e.target.value)}
        />
      );
  }
}

function CheckField({
  field,
  suiteId,
  environmentId,
  values,
}: {
  field: PrerequisiteField;
  suiteId: string;
  environmentId: string;
  values: Record<string, unknown>;
}) {
  const runCheck = useRunCheck();
  const result = runCheck.data as CheckRunResponse | undefined;

  return (
    <div className="row" style={{ gap: 10, marginTop: 4 }}>
      <button
        type="button"
        className="btn"
        disabled={runCheck.isPending}
        onClick={() =>
          runCheck.mutate({ field_id: field.id, suite_id: suiteId, environment_id: environmentId, values })
        }
      >
        {runCheck.isPending ? "Checking…" : "Run check"}
      </button>
      {result && (
        <span className={`pill ${result.passed ? "passed" : "failed"}`}>
          <span className="dot" />
          {result.message}
        </span>
      )}
      {field.remediation && !result?.passed && (
        <span className="muted" style={{ fontSize: 12 }}>
          {field.remediation}
        </span>
      )}
    </div>
  );
}
