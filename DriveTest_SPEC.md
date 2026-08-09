# Network Test Orchestration Platform — Master Instructions for Cursor

## 1. Purpose of this document

This file is the single source of truth for building the project.

You are acting as:
- Senior software architect
- Senior Python backend engineer
- Senior React/TypeScript frontend engineer
- DevOps engineer
- Network automation engineer
- Security-minded reviewer
- AI integration engineer

The human developer has limited coding experience and is building this project primarily with AI assistance.

Therefore:

1. Never assume the user understands an implementation detail.
2. Prefer simple, maintainable solutions over clever solutions.
3. Build incrementally.
4. Do not generate the entire application in one huge step.
5. Before changing code, explain what will be changed and why.
6. After every meaningful change, run the relevant tests/checks.
7. Do not silently change architecture decisions in this document.
8. If an architectural change is required, explain it first and update this spec.
9. Never expose secrets in logs, code, test output, screenshots, database records, or frontend responses.
10. Keep the code production-oriented, but avoid unnecessary enterprise complexity in the MVP.

---

# 2. Product goal

Build a web-based task and test orchestration platform for network equipment validation.

The system will:

1. Let a user select a Test Suite.
2. Load the requirements of that Suite.
3. Let the user select a compatible Environment.
4. Resolve prerequisites based on:
   - Suite
   - Environment
   - Platform
   - System type
5. Dynamically generate a prerequisite form.
6. Validate all required prerequisite fields.
7. Run automatic prerequisite checks where possible.
8. Require manual confirmation for prerequisites that cannot be checked automatically.
9. Let the user select a Git repository branch/commit using that user's own Git credentials.
10. Pull the selected Git revision into a temporary workspace.
11. Execute tests sequentially.
12. Detect script/runtime failures separately from product/test failures.
13. Let every test produce a deterministic verdict OR explicitly punt the verdict to AI.
14. Always run an AI review for every completed test.
15. Calculate the final verdict according to the rules in this document.
16. Store structured results, logs, AI analysis, evidence, Git revision, environment, and user.
17. Present a clear dark premium dashboard and run report.

---

# 3. Core product terminology

## Suite

A Suite is a collection of related tests.

Examples:

- PWHE Shaping
- BGP Convergence
- MPLS Validation
- Optics Validation
- Routing Scale

A Suite defines what it requires in order to run.

A Suite does NOT hardcode one specific lab.

---

## Environment

An Environment represents an available lab/test setup.

It may contain:

- Devices
- Management addresses
- Device roles
- Platform
- System type
- Software version
- Traffic generator
- Capabilities
- Topology metadata
- Secret references

Example:

```yaml
name: lab_23
platform: platform_a
system_type: pwhe
software_version: "25.2"

capabilities:
  - qos
  - shaping
  - mpls
  - pwhe
```

---

## Requirement

A Requirement determines whether an Environment is compatible with a Suite.

Example:

```yaml
requirements:
  min_devices: 2
  traffic_generator: true

  capabilities:
    - qos
    - shaping
    - pwhe
```

Requirements answer:

> Can this Environment run this Suite at all?

---

## Prerequisite

A Prerequisite determines whether a compatible Environment is currently ready for execution.

Prerequisites may be:

- User input
- Select field
- Number
- IP address
- Interface name
- Checkbox/manual confirmation
- Automatic check
- Secret reference
- Conditional field

Prerequisites answer:

> Is this Environment ready to run this Suite now, and which runtime values are needed?

---

## Test

A Test is one independently evaluated validation scenario.

Do not model Shaping as one giant script.

A Suite should contain multiple Test Cases.

Example:

```text
PWHE Shaping Suite
├── Basic shaping
├── High priority queue
├── Max bandwidth
├── Congestion behavior
├── Counter validation
├── Packet loss validation
└── Cleanup validation
```

Every test has its own result.

---

# 4. Required top-level workflow

The UI and backend must follow this logical order:

```text
SELECT SUITE
    ↓
Load Suite Requirements
    ↓
Find Compatible Environments
    ↓
SELECT ENVIRONMENT
    ↓
Resolve Prerequisite Profile
    ↓
Generate Dynamic Prerequisite Form
    ↓
Fill Inputs / Manual Confirmations
    ↓
Run Automatic Prerequisite Checks
    ↓
All Required Prerequisites Satisfied?
    ├── NO → Block execution
    └── YES
          ↓
Select Git Repository / Branch / Commit
          ↓
Create Task / Run
          ↓
Create Temporary Workspace
          ↓
Fetch Exact Git Revision
          ↓
Execute Tests Sequentially
          ↓
Evaluate Each Test
          ↓
Store Results
          ↓
Generate Suite Report
```

---

# 5. Test verdict model

This is a critical architectural rule.

A test may work in one of two modes.

## Mode A — test determines its own verdict

The test returns:

```text
test_verdict = PASSED
```

or:

```text
test_verdict = FAILED
```

AI still reviews the test and returns its own opinion.

---

## Mode B — test punts the verdict to AI

The test returns:

```text
test_verdict = null
```

AI is responsible for determining whether the test passed or failed.

---

# 6. AI is mandatory for every completed test

AI review runs for every successfully executed test.

AI must always provide:

- ai_verdict
- confidence
- summary
- observations
- anomalies
- evidence
- likely_root_cause when applicable
- recommended_next_step when applicable

AI is therefore always a reviewer.

For tests with `test_verdict = null`, AI is also the judge.

---

# 7. Final verdict rule

This rule must be implemented exactly.

A test may be marked PASSED only when:

```text
ai_verdict == PASSED
AND
(
  test_verdict == PASSED
  OR
  test_verdict == null
)
```

Equivalent logic:

```python
if ai_verdict == "PASSED" and (
    test_verdict == "PASSED" or test_verdict is None
):
    final_verdict = "PASSED"
else:
    final_verdict = "FAILED"
```

However, AI must also be allowed to return:

```text
INCONCLUSIVE
```

When AI returns INCONCLUSIVE:

```text
final_verdict = REVIEW_REQUIRED
```

Therefore:

| Test Verdict | AI Verdict | Final Verdict |
|---|---|---|
| PASSED | PASSED | PASSED |
| FAILED | PASSED | FAILED |
| PASSED | FAILED | FAILED |
| FAILED | FAILED | FAILED |
| null | PASSED | PASSED |
| null | FAILED | FAILED |
| PASSED | INCONCLUSIVE | REVIEW_REQUIRED |
| FAILED | INCONCLUSIVE | FAILED |
| null | INCONCLUSIVE | REVIEW_REQUIRED |

A deterministic test failure must never become PASSED because AI thinks it passed.

---

# 8. Execution failure is not a test failure

Keep execution state separate from test result.

Supported execution states:

```text
PENDING
RUNNING
COMPLETED
SCRIPT_ERROR
INFRA_ERROR
TIMEOUT
CANCELLED
SKIPPED
```

Examples:

## SCRIPT_ERROR

- Python exception
- Invalid result structure
- Parser crash
- Missing dependency
- Application bug

## INFRA_ERROR

- SSH connection failure
- Authentication failure
- Remote device unreachable
- Traffic generator unreachable
- Environment connectivity problem

## TIMEOUT

Execution exceeded its configured timeout.

If execution did not complete successfully, AI should NOT produce a normal product verdict.

It may optionally produce an error summary, but:

```text
final_verdict != PASSED
```

---

# 9. Test package format

Every test should live in Git as a self-contained package.

Recommended structure:

```text
network-tests/
├── suites/
│   ├── shaping/
│   │   ├── suite.yaml
│   │   ├── README.md
│   │   └── tests/
│   │       ├── max_bandwidth/
│   │       │   ├── test.py
│   │       │   ├── test.yaml
│   │       │   └── README.md
│   │       └── ...
│   ├── bgp/
│   ├── mpls/
│   └── optics/
│
├── prerequisites/
│   ├── shaping/
│   │   ├── common.yaml
│   │   ├── platform_a/
│   │   │   ├── default.yaml
│   │   │   └── pwhe.yaml
│   │   └── platform_b/
│   │       ├── default.yaml
│   │       └── pwhe.yaml
│   └── ...
│
├── framework/
│   ├── ssh/
│   ├── logging/
│   ├── result_models/
│   ├── evaluators/
│   └── common/
│
└── schemas/
```

---

# 10. Suite definition

Example `suite.yaml`:

```yaml
id: pwhe_shaping
name: PWHE Shaping
description: Validate PWHE shaping behavior.

requirements:
  min_devices: 2
  traffic_generator: true

  capabilities:
    - qos
    - shaping
    - pwhe

supported_platforms:
  - platform_a
  - platform_b

tests:
  - max_bandwidth
  - high_priority_queue
  - congestion_behavior
```

---

# 11. Dynamic prerequisite format

Prerequisite definitions must be declarative.

Use YAML for human editing.

Use JSON Schema or equivalent backend validation for machine validation.

Recommended field model:

```text
id
label
description
type
required
default
placeholder
options
validation
visible_when
check
remediation
sensitive
```

Supported field types for MVP:

```text
text
textarea
number
integer
boolean
confirmation
select
multiselect
ip
interface
secret_reference
check
```

---

# 12. Example prerequisite definition

```yaml
id: pwhe_shaping_platform_a
version: 1

sections:

  - id: connectivity
    title: Connectivity

    fields:

      - id: dut_management_ip
        label: DUT Management IP
        type: ip
        required: true

      - id: mse_management_ip
        label: MSE Management IP
        type: ip
        required: true

      - id: customer_port
        label: Customer Port
        type: interface
        required: true
        placeholder: ge800-31/0/17

  - id: traffic
    title: Traffic Generator

    fields:

      - id: traffic_generator
        label: Traffic Generator
        type: select
        required: true
        options:
          - ixia
          - spirent

      - id: traffic_generator_ip
        label: Traffic Generator IP
        type: ip
        required: true

  - id: physical
    title: Physical Validation

    fields:

      - id: topology_verified
        label: Physical topology verified
        type: confirmation
        required: true

  - id: checks
    title: Automatic Checks

    fields:

      - id: ssh_connectivity
        label: Verify SSH connectivity
        type: check
        required: true

        check:
          handler: ssh_connectivity
          target: ${dut_management_ip}
```

---

# 13. Conditional prerequisites

Fields may depend on another field.

Example:

```yaml
- id: ixia_chassis_ip
  label: Ixia Chassis IP
  type: ip
  required: true

  visible_when:
    field: traffic_generator
    equals: ixia
```

The backend must validate conditional rules.

Do not rely only on frontend validation.

---

# 14. Prerequisite template vs prerequisite instance

Keep these separate.

## Template

Stored in Git.

Defines:

- what fields exist
- validations
- descriptions
- automatic checks
- conditional logic

## Instance

Stored in the database for a specific Run.

Contains the actual values provided by the user.

Example:

```json
{
  "suite": "pwhe_shaping",
  "environment": "lab_23",
  "values": {
    "dut_management_ip": "10.10.1.20",
    "customer_port": "ge800-31/0/17",
    "traffic_generator": "ixia",
    "topology_verified": true
  }
}
```

Sensitive values must not be stored directly unless explicitly designed and encrypted.

Prefer secret references.

---

# 15. Automatic prerequisite checks

Automatic checks should use registered backend handlers.

Do NOT allow arbitrary code execution directly from YAML.

Good:

```yaml
check:
  handler: ssh_connectivity
```

Bad:

```yaml
check:
  command: "arbitrary shell command supplied by YAML"
```

Handlers should be implemented in application code.

Example registry:

```python
CHECK_HANDLERS = {
    "ssh_connectivity": check_ssh_connectivity,
    "interface_up": check_interface_up,
    "traffic_generator_reachable": check_tg_connectivity,
}
```

---

# 16. Git identity model

Use per-user Git identity.

Every application user connects their own Git account.

The application uses that user's Git authorization when:

- discovering repositories
- reading branches
- reading commits
- fetching code

The application must NOT use one global token for all users.

---

# 17. Git authentication

Preferred design:

```text
User
 ↓
Connect Git Provider
 ↓
OAuth / provider-approved authorization
 ↓
Encrypted credential / secret manager
 ↓
Git Service
```

Use read-only permissions for MVP.

Do not request write access unless a future feature explicitly requires it.

Never:

- log access tokens
- send access tokens to frontend after initial secure exchange
- include tokens in repository URLs stored in DB
- expose tokens to test scripts
- write tokens to result artifacts

---

# 18. Git workspace execution model

Every Run receives an isolated temporary workspace.

Example:

```text
/workspaces/<run_id>/
├── repo/
├── results/
├── logs/
└── artifacts/
```

Execution:

```text
Create workspace
 ↓
Authenticate as user
 ↓
Fetch repository
 ↓
Checkout exact commit
 ↓
Record commit SHA
 ↓
Remove Git credential from execution context
 ↓
Run tests
 ↓
Collect results
 ↓
Cleanup workspace
```

Persist at minimum:

```text
repository
branch
commit_sha
requested_by_user_id
```

The commit SHA is the true execution revision.

---

# 19. Script execution model

For MVP, tests may run using Python subprocesses.

Each test must execute in a separate process.

Never execute test Python code inside the API process.

Later, add Docker isolation if required.

Tests do not open their own SSH connections. Device access is provided by the
Run-owned Connection Manager via the ExecutionContext (see section 51).

Runner responsibilities:

- create execution context
- launch process
- capture stdout
- capture stderr
- enforce timeout
- capture exit code
- collect result JSON
- detect malformed result
- classify execution errors
- store logs/artifacts

---

# 20. Standard result contract

Each completed test should produce structured JSON.

Example:

```json
{
  "execution_status": "COMPLETED",
  "test_id": "max_bandwidth",
  "test_verdict": "PASSED",
  "measurements": {
    "configured_bandwidth_mbps": 1000,
    "measured_bandwidth_mbps": 998
  },
  "observations": [
    "Queue stayed within configured shaping range"
  ],
  "evidence": [
    "show qos queue statistics output"
  ],
  "artifacts": [
    "qos_stats.txt"
  ]
}
```

AI-judged test:

```json
{
  "execution_status": "COMPLETED",
  "test_id": "complex_log_analysis",
  "test_verdict": null,
  "observations": [],
  "evidence": [],
  "artifacts": [
    "routing_engine.log"
  ]
}
```

---

# 21. AI evaluation input

The AI evaluator should receive only relevant information.

Input should contain:

- test definition
- evaluation instructions
- expected behavior
- test result
- measurements
- observations
- selected log excerpts
- relevant artifacts or parsed artifact content
- platform/system metadata
- software version when relevant

Do not dump unlimited raw logs into the AI request.

Implement size limits and selective extraction.

---

# 22. AI output contract

AI must return structured output.

Example:

```json
{
  "ai_verdict": "PASSED",
  "confidence": 0.97,
  "summary": "Shaping behavior matched the expected profile.",
  "observations": [
    "Measured rate stayed inside tolerance."
  ],
  "anomalies": [],
  "evidence": [
    {
      "source": "measurement",
      "details": "998 Mbps measured against 1000 Mbps target"
    }
  ],
  "likely_root_cause": null,
  "recommended_next_step": null
}
```

Allowed AI verdicts:

```text
PASSED
FAILED
INCONCLUSIVE
```

Reject and retry malformed AI responses according to a bounded retry policy.

Never allow an AI response to execute commands.

---

# 23. AI prompt design

The prompt must clearly say:

1. You are evaluating network test evidence.
2. Use only supplied evidence.
3. Do not invent missing measurements.
4. If evidence is insufficient, return INCONCLUSIVE.
5. Explain exactly why.
6. Cite evidence from the supplied result/logs.
7. Never override deterministic FAIL.
8. Output only the structured schema expected by the backend.

Prompts must be versioned.

Store:

```text
model
prompt_version
evaluation_policy_version
```

for every AI evaluation.

---

# 24. Backend stack

Use:

```text
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2
Alembic
PostgreSQL
httpx
asyncssh or another maintained SSH library
pytest
```

For MVP, do NOT add unless truly required:

```text
Kubernetes
Celery
Kafka
Temporal
multiple microservices
```

Start as a modular monolith.

---

# 25. Frontend stack

Use:

```text
React
TypeScript
Vite
React Router
TanStack Query
React Hook Form
Zod
```

A component library may be used if it supports custom theming cleanly.

Do not let the UI library dictate a generic visual identity.

---

# 26. Proposed backend modules

```text
backend/
├── app/
│   ├── api/
│   ├── auth/
│   ├── db/
│   ├── git/
│   ├── environments/
│   ├── suites/
│   ├── prerequisites/
│   ├── runs/
│   ├── runner/
│   ├── evaluation/
│   ├── ai/
│   ├── results/
│   ├── schemas/
│   └── core/
├── tests/
├── alembic/
└── pyproject.toml
```

---

# 27. Proposed frontend modules

```text
frontend/
├── src/
│   ├── app/
│   ├── pages/
│   ├── components/
│   ├── features/
│   │   ├── suites/
│   │   ├── environments/
│   │   ├── prerequisites/
│   │   ├── git/
│   │   ├── runs/
│   │   └── results/
│   ├── api/
│   ├── hooks/
│   ├── types/
│   └── styles/
└── package.json
```

---

# 28. Database entities

MVP entities:

## users

```text
id
email
display_name
created_at
```

## git_connections

```text
id
user_id
provider
external_username
secret_reference
scopes
expires_at
created_at
updated_at
```

## suites

May initially be synced/indexed from Git.

```text
id
name
description
source_repository
source_path
```

## environments

```text
id
name
platform
system_type
software_version
capabilities_json
metadata_json
enabled
```

## runs

```text
id
suite_id
environment_id
user_id
repository
branch
commit_sha
status
started_at
finished_at
created_at
```

## prerequisite_instances

```text
id
run_id
template_version
values_json
validation_status
created_at
```

## test_runs

```text
id
run_id
test_id
order_index
execution_status
test_verdict
ai_verdict
final_verdict
ai_confidence
started_at
finished_at
result_json
```

## ai_evaluations

```text
id
test_run_id
model
prompt_version
policy_version
ai_verdict
confidence
summary
analysis_json
created_at
```

## artifacts

```text
id
test_run_id
artifact_type
path_or_object_key
size
created_at
```

---

# 29. REST API outline

MVP endpoints can follow this shape.

## Suites

```text
GET /api/suites
GET /api/suites/{suite_id}
GET /api/suites/{suite_id}/compatible-environments
```

## Environments

```text
GET /api/environments
GET /api/environments/{environment_id}
```

## Prerequisites

```text
GET /api/suites/{suite_id}/environments/{environment_id}/prerequisites
POST /api/prerequisites/validate
POST /api/prerequisites/checks/{check_id}/run
```

## Git

```text
GET /api/git/connections
POST /api/git/connect
GET /api/git/repositories
GET /api/git/repositories/{repo_id}/branches
GET /api/git/repositories/{repo_id}/commits
```

## Runs

```text
POST /api/runs
GET /api/runs
GET /api/runs/{run_id}
POST /api/runs/{run_id}/cancel
```

## Results

```text
GET /api/runs/{run_id}/tests
GET /api/test-runs/{test_run_id}
GET /api/test-runs/{test_run_id}/artifacts
```

---

# 30. MVP authentication

Keep application authentication simple but secure.

If company SSO is available later, integrate it.

Do not build a custom password system unless needed.

Separate:

```text
Application authentication
```

from:

```text
Git provider authorization
```

A user may be authenticated to the app while not yet connected to Git.

---

# 31. UI/UX design direction

The application should feel:

- premium
- dark
- technical
- modern
- high-end networking/infra product
- dense enough for engineers
- clean, not cyberpunk
- not flashy
- not gaming-like

Primary theme:

```text
Near black backgrounds
Charcoal / graphite surfaces
Subtle gray borders
Muted white text
Green for healthy/passed
Red for failed
Amber for warning/review
Blue only for neutral active states
```

---

# 32. Visual design tokens

Suggested conceptual palette:

```text
Background:
#090A0C

Surface:
#111318

Elevated surface:
#171A20

Border:
#272B33

Primary text:
#F4F6F8

Secondary text:
#9AA1AB

Muted text:
#666D78

Success:
#22C55E

Failure:
#EF4444

Warning:
#F59E0B

Info:
#3B82F6
```

These values may be slightly adjusted for contrast/accessibility.

---

# 33. Status visual language

PASSED:

```text
green check icon
green status pill
subtle green glow
```

FAILED:

```text
red X icon
red status pill
subtle red accent
```

RUNNING:

```text
animated spinner or pulse
neutral/blue status indicator
```

REVIEW_REQUIRED:

```text
amber warning icon
amber status pill
```

SCRIPT_ERROR:

```text
red technical/error icon
```

INFRA_ERROR:

```text
orange/red connectivity icon
```

---

# 34. Hover and motion

Use subtle premium motion.

Examples:

- Cards lift 1–2px on hover.
- Border brightens slightly.
- Soft shadow increases.
- Buttons transition in 150–220ms.
- Status icons may have a soft glow.
- Running test row may show an animated progress shimmer.
- Expand/collapse panels use smooth transitions.

Avoid:

- excessive bouncing
- strong neon effects
- huge animations
- distracting gradients
- long animations

Respect reduced-motion accessibility settings.

---

# 35. Core screens

## Dashboard

Show:

- recent runs
- pass rate
- failed tests
- script errors
- review required
- currently running tasks

---

## New Run Wizard

Step 1:

```text
Select Suite
```

Step 2:

```text
Select Environment
```

Only compatible environments should appear.

Step 3:

```text
Prerequisites
```

Dynamic form plus automatic checks.

Step 4:

```text
Git Revision
```

Repository / branch / commit.

Step 5:

```text
Review & Run
```

Show a summary before execution.

---

## Live Run

Display:

```text
Suite name
Environment
Git branch
Commit SHA
Requested by
Start time
Elapsed time
```

Then test list:

```text
✓ Test 1     PASSED
✓ Test 2     PASSED
● Test 3     RUNNING
○ Test 4     PENDING
○ Test 5     PENDING
```

Each test can expand to show:

- stdout
- stderr
- measurements
- test verdict
- AI verdict
- final verdict
- AI summary
- AI evidence
- artifacts

---

## Test Result Detail

Prominently show:

```text
FINAL VERDICT
```

Then separately:

```text
Execution Status
Test Verdict
AI Verdict
AI Confidence
```

Never hide disagreement.

Example:

```text
Final Verdict: FAILED
Test Verdict: PASSED
AI Verdict: FAILED
AI Confidence: 92%
```

---

# 36. AI summary UI

AI summary should look like an engineering assistant, not a chatbot.

Use sections such as:

```text
AI Review

Summary
Anomalies
Evidence
Likely Root Cause
Recommended Next Step
```

Do not use chat bubbles.

---

# 37. Security requirements

Mandatory rules:

1. No secrets in Git.
2. No plaintext Git tokens in the database.
3. No credentials in logs.
4. No credentials in frontend payloads unless strictly needed.
5. No secret values inside AI prompts.
6. No arbitrary shell commands from user-controlled YAML.
7. Validate all paths to prevent directory traversal.
8. Validate Git repository/branch input.
9. Execute tests outside API process.
10. Apply timeouts.
11. Limit artifact/log sizes.
12. Sanitize displayed terminal output.
13. Record audit data for runs.
14. Never execute AI-generated commands automatically.

---

# 38. Logging

Use structured application logs.

Every meaningful log line should include context such as:

```text
run_id
test_run_id
user_id
suite_id
environment_id
```

Never include:

```text
password
token
private key
secret value
```

---

# 39. Error handling

Every API error should use a consistent shape.

Example:

```json
{
  "error": {
    "code": "GIT_FETCH_FAILED",
    "message": "Unable to fetch repository.",
    "details": null,
    "request_id": "..."
  }
}
```

Frontend should show a human-readable message.

Technical details belong in logs, not giant raw stack traces in the UI.

---

# 40. Testing strategy

Every module must have tests.

Backend:

```text
pytest
unit tests
API tests
result verdict tests
prerequisite validation tests
Git service tests with mocks
AI evaluator tests with mocked responses
```

Frontend:

```text
component tests where valuable
form validation tests
verdict display tests
critical wizard tests
```

Most important unit tests:

```text
final verdict truth table
prerequisite conditional logic
environment compatibility
result schema validation
execution error classification
```

---

# 41. Critical verdict unit tests

At minimum test:

```python
assert final("PASSED", "PASSED") == "PASSED"
assert final("FAILED", "PASSED") == "FAILED"
assert final("PASSED", "FAILED") == "FAILED"
assert final(None, "PASSED") == "PASSED"
assert final(None, "FAILED") == "FAILED"
assert final("PASSED", "INCONCLUSIVE") == "REVIEW_REQUIRED"
assert final(None, "INCONCLUSIVE") == "REVIEW_REQUIRED"
assert final("FAILED", "INCONCLUSIVE") == "FAILED"
```

This business logic must not be duplicated across frontend and backend.

Backend is authoritative.

---

# 42. Development philosophy

Build the system in phases.

Do not jump ahead.

Each phase should end with:

```text
working code
tests passing
short README/update
manual verification steps
```

---

# 43. Recommended implementation phases

## Phase 1 — Skeleton

Create:

- backend FastAPI project
- frontend React project
- PostgreSQL development setup
- health endpoint
- basic dark theme
- navigation shell

Acceptance criteria:

```text
Backend runs
Frontend runs
Frontend can call backend health endpoint
```

---

## Phase 2 — Suite and Environment model

Implement:

- Suite models
- Environment models
- requirements matcher
- basic Suite list
- compatible Environment list

Acceptance:

User can select Suite and only see compatible Environments.

---

## Phase 3 — Dynamic prerequisites

Implement:

- prerequisite YAML schema
- parser
- validation
- dynamic frontend form
- conditional fields
- confirmation fields
- automatic check interface

Acceptance:

A prerequisite YAML file generates a usable form automatically.

---

## Phase 4 — Git connection

Implement per-user Git connection.

For initial MVP, support one Git provider first.

Implement:

- connect account
- list accessible repositories
- list branches
- list commits
- secure token storage abstraction

Acceptance:

Two users with different Git permissions see only what their own account can access.

---

## Phase 5 — Runner

Implement:

- run creation
- temporary workspace
- Git checkout
- sequential tests
- stdout/stderr
- timeout
- execution classification
- result.json validation

Acceptance:

A Suite containing 3 sample tests executes sequentially and stores independent results.

---

## Phase 6 — Deterministic verdict

Implement:

```text
test_verdict
```

including null for AI-judged tests.

Acceptance:

The system stores test verdict separately from execution status.

---

## Phase 7 — AI evaluator

Implement:

- structured AI request
- schema-validated output
- AI verdict
- confidence
- summary
- anomalies
- evidence
- INCONCLUSIVE
- prompt versioning

Acceptance:

AI review is stored for every completed test.

---

## Phase 8 — Final verdict engine

Implement the exact truth table from this spec.

Acceptance:

All final-verdict unit tests pass.

---

## Phase 9 — Live Run UI

Implement:

- run progress
- test status list
- auto-refresh/polling first
- expandable result rows
- logs
- AI review
- final verdict

Do not implement WebSockets unless polling becomes insufficient.

---

## Phase 10 — Reports and polish

Implement:

- Suite summary
- pass/fail counts
- review-required count
- script-error count
- timestamps
- Git revision
- export-friendly report view
- premium UI polish

---

# 44. Do not over-engineer the MVP

Do NOT introduce these without a demonstrated need:

```text
microservices
Kubernetes
Kafka
event sourcing
CQRS
service mesh
distributed workflow engine
custom DSL
complex plugin runtime
```

A modular monolith is preferred.

---

# 45. Cursor working rules

When I ask you to implement a feature:

1. Read this document first.
2. Inspect the existing repository.
3. Identify the smallest coherent change.
4. Tell me which files you will modify.
5. Implement the change.
6. Run tests/lint/type checks.
7. Fix failures.
8. Summarize what changed in simple language.
9. Tell me how I can manually verify it.
10. Do not continue into the next major feature unless I ask.

When I provide an error:

1. Read the full error.
2. Inspect related code.
3. Find root cause.
4. Make the smallest safe fix.
5. Run the relevant tests.
6. Explain the fix simply.

When architecture is ambiguous:

1. Prefer the decisions in this document.
2. If not covered, choose the simplest maintainable solution.
3. Explicitly mention the new decision.
4. Add it to project documentation.

---

# 46. Coding quality rules

Python:

- type hints
- Pydantic models
- small focused functions
- clear names
- no giant 1000-line files
- dependency injection where helpful, but keep it simple
- async only where it provides a clear benefit

TypeScript:

- strict mode
- avoid `any`
- reusable typed API models
- small components
- business rules belong in backend
- do not duplicate backend verdict logic

General:

- no magic strings where enums are appropriate
- no secrets hardcoded
- no TODO placeholders in completed features
- no swallowed exceptions
- no `except Exception: pass`
- no unbounded retries
- no infinite waits

---

# 47. Sample MVP demo scenario

Create a demo Suite:

```text
Demo Shaping Suite
```

with three tests.

## Test 1

Deterministic PASS:

```text
test_verdict = PASSED
AI verdict expected = PASSED
Final = PASSED
```

## Test 2

Deterministic PASS, AI detects anomaly:

```text
test_verdict = PASSED
AI verdict = FAILED
Final = FAILED
```

## Test 3

AI-owned verdict:

```text
test_verdict = null
AI verdict = PASSED
Final = PASSED
```

Also provide one script-error demo.

This scenario should be available in development mode for validating the system end-to-end.

---

# 48. Definition of MVP success

The MVP is successful when a user can:

1. Log into the application.
2. Connect their Git identity.
3. Select a Suite.
4. Select a compatible Environment.
5. Fill a dynamically generated prerequisite form.
6. Pass automatic/manual prerequisite validation.
7. Select branch/commit.
8. Start a Run.
9. Watch tests execute sequentially.
10. Clearly see script errors separately from test failures.
11. See `test_verdict`.
12. See `ai_verdict`.
13. See AI summary/evidence.
14. See `final_verdict`.
15. Open a historical Run and understand exactly:
    - who ran it
    - which environment
    - which Git commit
    - which tests ran
    - what failed
    - why AI reached its opinion

---

# 49. First instruction to Cursor

Do not start by implementing the full product.

Start by doing the following:

1. Read this entire document.
2. Propose the exact MVP repository structure.
3. Propose the initial database schema.
4. Propose the first 5 implementation milestones.
5. Identify any contradictions or missing decisions.
6. Do not write application code yet.
7. Present the proposal for approval.

After approval, begin only with Phase 1.

---

# 50. Product design principle

The system must make one question easy to answer:

> What happened in this test, why did the system decide this verdict, and can I trust/reproduce the result?

Every architecture, UI, logging, Git, prerequisite, and AI decision should support that goal.

---

# 51. SSH connection lifecycle

SSH connections are owned by the Run, not by individual tests.

At the beginning of a Run, DriveTest creates a persistent connection for every
required network device.

All tests in the Suite reuse those connections.

Tests MUST NOT create direct SSH connections themselves.

Tests interact with devices only through the DriveTest Network API /
ExecutionContext.

The Connection Manager is responsible for:

- connection establishment
- authentication
- keepalive
- reconnect
- command execution
- configuration execution
- command timeout
- logging
- credential masking
- session health
- closing sessions at the end of the Run

Connection lifecycle:

```text
RUN START
→ establish required sessions
→ execute all Suite tests
→ cleanup
→ close sessions
```

A dropped connection may be automatically re-established according to a bounded
reconnect policy.

Credentials must never be exposed to test code.

## 51.1 How this is implemented

Because tests execute in isolated subprocesses (section 19), the Run-owned
connections live in the DriveTest backend, and tests reach them through a small
client rather than by opening sockets:

```text
Run start
  → ConnectionManager establishes one session per required device
  → a per-Run Connection Broker (localhost, token-authenticated) is started
  → each test subprocess receives ONLY the broker URL, a per-Run token, and the
    set of device roles (never hosts credentials)
  → test code uses the ExecutionContext SDK:
        from drivetest import ExecutionContext
        ctx = ExecutionContext.from_env()
        output = ctx.device("dut").run("show version")
        ctx.device("dut").configure(["interface ...", "..."])
  → the broker forwards role+command to the ConnectionManager, which uses the
    persistent session and returns masked output
Run cleanup
  → broker stopped, all sessions closed
```

Required devices are resolved from the Environment's device metadata (role +
host, or host taken from a prerequisite value) plus credentials referenced via
secret references (section 14/17). The transport is pluggable: a real SSH
transport (paramiko) for labs, and a simulated transport as the default for
development/demo so the platform runs without live devices.

Note: automatic prerequisite checks (section 15) run BEFORE a Run exists, so they
perform their own lightweight reachability checks and are not part of this
Run-owned connection lifecycle.
