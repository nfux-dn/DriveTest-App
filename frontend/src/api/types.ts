// Typed API models mirroring backend contracts. Verdict/business logic lives in
// the backend only (spec section 41); these are for display and requests.

export interface User {
  id: string;
  email: string;
  display_name: string;
}

export interface Suite {
  id: string;
  name: string;
  description: string | null;
  tests: string[];
}

export interface SuiteReadme {
  suite_id: string;
  markdown: string;
}

export type FieldType =
  | "text"
  | "textarea"
  | "number"
  | "integer"
  | "boolean"
  | "confirmation"
  | "select"
  | "multiselect"
  | "ip"
  | "host"
  | "interface"
  | "secret_reference"
  | "check";

export interface VisibleWhen {
  field: string;
  equals: unknown;
}

export interface PrerequisiteField {
  id: string;
  label: string;
  description: string | null;
  type: FieldType;
  required: boolean;
  default: unknown;
  placeholder: string | null;
  options: string[];
  visible_when: VisibleWhen | null;
  remediation: string | null;
  sensitive: boolean;
}

export interface PrerequisiteSection {
  id: string;
  title: string;
  fields: PrerequisiteField[];
}

export interface PrerequisiteTemplate {
  id: string;
  version: number;
  suite_id: string;
  sections: PrerequisiteSection[];
}

export interface FieldError {
  field_id: string;
  message: string;
}

export interface ValidateResponse {
  status: "PENDING" | "VALID" | "INVALID";
  errors: FieldError[];
  visible_fields: string[];
  pending_checks: string[];
}

export interface CheckRunResponse {
  field_id: string;
  handler: string;
  passed: boolean;
  message: string;
}

export interface GitConnection {
  id: string;
  provider: string;
  external_username: string | null;
  scopes: string | null;
  expires_at: string | null;
}

export interface AiConnection {
  id: string;
  provider: string;
  model: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface Repository {
  id: number;
  full_name: string;
  name: string;
  private: boolean;
  default_branch: string | null;
}

export interface Branch {
  name: string;
  commit_sha: string;
}

export interface Commit {
  sha: string;
  message: string;
  author: string | null;
  date: string | null;
}

export interface TestRun {
  id: string;
  test_id: string;
  order_index: number;
  execution_status: string;
  test_verdict: string | null;
  ai_verdict: string | null;
  final_verdict: string | null;
  ai_confidence: number | null;
  started_at: string | null;
  finished_at: string | null;
  result_json: Record<string, unknown> | null;
}

export interface Run {
  id: string;
  suite_id: string;
  user_id: string;
  repository: string | null;
  branch: string | null;
  commit_sha: string | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface RunDetail extends Run {
  tests: TestRun[];
}

export interface AiEvidence {
  source: string;
  details: string;
}

export interface AiAnalysis {
  observations?: string[];
  anomalies?: string[];
  evidence?: AiEvidence[];
  likely_root_cause?: string | null;
  recommended_next_step?: string | null;
}

export interface AiEvaluation {
  model: string;
  prompt_version: string;
  policy_version: string;
  ai_verdict: string;
  confidence: number | null;
  summary: string | null;
  analysis: AiAnalysis;
}

export interface TestRunDetail extends TestRun {
  ai: AiEvaluation | null;
}

export interface Artifact {
  id: string;
  artifact_type: string;
  path_or_object_key: string;
  size: number | null;
  created_at: string;
}

export interface RunReport {
  run_id: string;
  suite_id: string;
  user_id: string;
  status: string;
  repository: string | null;
  branch: string | null;
  commit_sha: string | null;
  started_at: string | null;
  finished_at: string | null;
  total: number;
  passed: number;
  failed: number;
  review_required: number;
  script_error: number;
  infra_error: number;
  timeout: number;
  other: number;
  tests: TestRun[];
}

export interface CreateRunRequest {
  suite_id: string;
  values: Record<string, unknown>;
  repository?: string | null;
  branch?: string | null;
  commit?: string | null;
}
