import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useMe } from "../api/queries";
import { Layout } from "../components/Layout";
import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";
import { NewRunWizard } from "../pages/NewRunWizard";
import { GitConnectPage } from "../pages/GitConnectPage";
import { RunDetailPage } from "../pages/RunDetailPage";

export function App() {
  const me = useMe();

  if (me.isLoading) {
    return <div style={{ display: "grid", placeItems: "center", height: "100vh" }}>Loading…</div>;
  }

  const authenticated = !!me.data && !me.isError;

  return (
    <BrowserRouter>
      <Routes>
        {!authenticated ? (
          <>
            <Route path="/login" element={<LoginPage />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </>
        ) : (
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="runs/new" element={<NewRunWizard />} />
            <Route path="runs/:runId" element={<RunDetailPage />} />
            <Route path="git" element={<GitConnectPage />} />
            <Route path="login" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        )}
      </Routes>
    </BrowserRouter>
  );
}
