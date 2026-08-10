import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { api } from "./client";
import type {
  Artifact,
  Branch,
  CheckRunResponse,
  Commit,
  CreateRunRequest,
  GitConnection,
  PrerequisiteTemplate,
  Repository,
  Run,
  RunDetail,
  RunReport,
  Suite,
  SuiteReadme,
  TestRunDetail,
  User,
  ValidateResponse,
} from "./types";

export function useHealth(): UseQueryResult<{ status: string }> {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<{ status: string }>("/health"),
    refetchInterval: 15000,
  });
}

export function useMe(): UseQueryResult<User> {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<User>("/api/auth/me"),
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; display_name?: string }) =>
      api.post<User>("/api/auth/login", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/api/auth/logout"),
    onSuccess: () => qc.clear(),
  });
}

export function useSuites(): UseQueryResult<Suite[]> {
  return useQuery({ queryKey: ["suites"], queryFn: () => api.get<Suite[]>("/api/suites") });
}

export function useSuiteReadme(suiteId: string | null): UseQueryResult<SuiteReadme> {
  return useQuery({
    queryKey: ["suite-readme", suiteId],
    queryFn: () => api.get<SuiteReadme>(`/api/suites/${suiteId}/readme`),
    enabled: !!suiteId,
  });
}

export function usePrerequisites(
  suiteId: string | null,
): UseQueryResult<PrerequisiteTemplate> {
  return useQuery({
    queryKey: ["prerequisites", suiteId],
    queryFn: () => api.get<PrerequisiteTemplate>(`/api/suites/${suiteId}/prerequisites`),
    enabled: !!suiteId,
  });
}

export function useValidatePrerequisites() {
  return useMutation({
    mutationFn: (payload: { suite_id: string; values: Record<string, unknown> }) =>
      api.post<ValidateResponse>("/api/prerequisites/validate", payload),
  });
}

export function useRunCheck() {
  return useMutation({
    mutationFn: (payload: {
      field_id: string;
      suite_id: string;
      values: Record<string, unknown>;
    }) =>
      api.post<CheckRunResponse>(
        `/api/prerequisites/checks/${payload.field_id}/run`,
        payload,
      ),
  });
}

export function useGitConnections(): UseQueryResult<GitConnection[]> {
  return useQuery({
    queryKey: ["git-connections"],
    queryFn: () => api.get<GitConnection[]>("/api/git/connections"),
  });
}

export function useConnectGit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (token: string) =>
      api.post<GitConnection>("/api/git/connect", { token }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["git-connections"] }),
  });
}

export function useRepositories(enabled: boolean): UseQueryResult<Repository[]> {
  return useQuery({
    queryKey: ["repositories"],
    queryFn: () => api.get<Repository[]>("/api/git/repositories"),
    enabled,
  });
}

export function useBranches(fullName: string | null): UseQueryResult<Branch[]> {
  return useQuery({
    queryKey: ["branches", fullName],
    queryFn: () => api.get<Branch[]>(`/api/git/repositories/${fullName}/branches`),
    enabled: !!fullName,
  });
}

export function useCommits(
  fullName: string | null,
  branch: string | null,
): UseQueryResult<Commit[]> {
  return useQuery({
    queryKey: ["commits", fullName, branch],
    queryFn: () =>
      api.get<Commit[]>(
        `/api/git/repositories/${fullName}/commits${branch ? `?branch=${branch}` : ""}`,
      ),
    enabled: !!fullName && !!branch,
  });
}

export function useRuns(): UseQueryResult<Run[]> {
  return useQuery({
    queryKey: ["runs"],
    queryFn: () => api.get<Run[]>("/api/runs"),
    refetchInterval: 5000,
  });
}

export function useRunDetail(runId: string | null): UseQueryResult<RunDetail> {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.get<RunDetail>(`/api/runs/${runId}`),
    enabled: !!runId,
    // Poll while running (spec Phase 9: polling first).
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "RUNNING" || status === "PENDING" ? 2000 : false;
    },
  });
}

export function useCreateRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateRunRequest) => api.post<Run>("/api/runs", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}

export function useRunReport(
  runId: string | null,
  poll: boolean,
): UseQueryResult<RunReport> {
  return useQuery({
    queryKey: ["report", runId],
    queryFn: () => api.get<RunReport>(`/api/runs/${runId}/report`),
    enabled: !!runId,
    refetchInterval: poll ? 2000 : false,
  });
}

export function useTestRunDetail(
  testRunId: string | null,
  enabled: boolean,
): UseQueryResult<TestRunDetail> {
  return useQuery({
    queryKey: ["test-run", testRunId],
    queryFn: () => api.get<TestRunDetail>(`/api/test-runs/${testRunId}`),
    enabled: enabled && !!testRunId,
  });
}

export function useArtifacts(
  testRunId: string | null,
  enabled: boolean,
): UseQueryResult<Artifact[]> {
  return useQuery({
    queryKey: ["artifacts", testRunId],
    queryFn: () => api.get<Artifact[]>(`/api/test-runs/${testRunId}/artifacts`),
    enabled: enabled && !!testRunId,
  });
}
