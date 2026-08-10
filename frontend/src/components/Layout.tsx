import { NavLink, Outlet } from "react-router-dom";
import { useHealth, useLogout, useMe } from "../api/queries";

export function Layout() {
  const me = useMe();
  const health = useHealth();
  const logout = useLogout();

  const backendOk = health.data?.status === "ok";

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 220,
          borderRight: "1px solid var(--border)",
          background: "var(--surface)",
          padding: "20px 14px",
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}
      >
        <div style={{ padding: "0 8px 18px", fontWeight: 700, fontSize: 16 }}>
          Drive<span style={{ color: "var(--info)" }}>Test</span>
        </div>
        <NavItem to="/" label="Dashboard" end />
        <NavItem to="/runs/new" label="New Run" />
        <NavItem to="/git" label="Git Connection" />
        <NavItem to="/ai" label="AI Provider" />

        <div style={{ marginTop: "auto", paddingTop: 18 }}>
          <div className="row" style={{ padding: "0 8px 10px", fontSize: 12 }}>
            <span
              className="dot"
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: backendOk ? "var(--success)" : "var(--failure)",
                display: "inline-block",
              }}
            />
            <span className="muted">Backend {backendOk ? "online" : "offline"}</span>
          </div>
          {me.data && (
            <div style={{ padding: "0 8px" }}>
              <div style={{ fontSize: 13 }}>{me.data.display_name}</div>
              <div className="muted" style={{ fontSize: 12 }}>
                {me.data.email}
              </div>
              <button
                className="btn"
                style={{ marginTop: 10, width: "100%" }}
                onClick={() => logout.mutate()}
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </aside>

      <main style={{ flex: 1, padding: "28px 32px", maxWidth: 1100 }}>
        <Outlet />
      </main>
    </div>
  );
}

function NavItem({ to, label, end }: { to: string; label: string; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      style={({ isActive }) => ({
        padding: "9px 10px",
        borderRadius: 6,
        color: isActive ? "var(--text)" : "var(--text-secondary)",
        background: isActive ? "var(--surface-elevated)" : "transparent",
        fontSize: 14,
      })}
    >
      {label}
    </NavLink>
  );
}
