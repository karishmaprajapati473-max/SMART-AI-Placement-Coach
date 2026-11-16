import { Link, useLocation, useNavigate } from "react-router-dom";

const navItems = [
  { to: "/dashboard", icon: "▦", label: "Overview" },
  { to: "/coding", icon: "⌘", label: "Coding coach" },
];

export default function AppShell({ children, title, eyebrow, active = "", backTo, backLabel = "Back" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const storedUser = (() => {
    try { return JSON.parse(localStorage.getItem("smartUser") || "null"); }
    catch { return null; }
  })();
  const initials = (storedUser?.name || "Student").split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link to="/dashboard" className="brand-lockup">
          <span className="brand-mark">S</span>
          <span className="brand-copy"><strong>SMART</strong><small>PLACEMENT COACH</small></span>
        </Link>
        <div className="side-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navItems.map((item) => {
            const isActive = active === item.to || location.pathname === item.to;
            return <Link key={item.to} to={item.to} className={`side-link ${isActive ? "active" : ""}`}>
              <span className="side-icon">{item.icon}</span><span>{item.label}</span>
            </Link>;
          })}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-help">
          <div className="help-icon">✦</div>
          <strong>Learn with purpose</strong>
          <p>Build skills one concept and one challenge at a time.</p>
        </div>
        <div className="side-profile">
          <span className="avatar">{initials || "S"}</span>
          <span className="profile-copy"><strong>{storedUser?.name || "Student"}</strong><small>{storedUser?.email || "Your learning space"}</small></span>
          <button type="button" className="logout-link" title="Sign out" aria-label="Sign out" onClick={() => { localStorage.removeItem("smartUser"); navigate("/"); }}>↗</button>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-left">
            {backTo && <Link to={backTo} className="back-link">← {backLabel}</Link>}
            <div className="topbar-heading">
              {eyebrow && <span className="eyebrow">{eyebrow}</span>}
              {title && <strong>{title}</strong>}
            </div>
          </div>
          <div className="topbar-right">
            <span className="system-status"><i /> Learning workspace</span>
            <span className="avatar avatar-small">{initials || "S"}</span>
          </div>
        </header>
        <main className="page-content">{children}</main>
        <footer className="app-footer"><span>SMART AI Placement Coach</span><span>Learn · Practice · Improve</span></footer>
      </div>
    </div>
  );
}
