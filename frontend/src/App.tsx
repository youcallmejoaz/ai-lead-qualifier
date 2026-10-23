import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api";
import { Contact } from "./pages/Contact";
import { Crm } from "./pages/Crm";
import { Inbox } from "./pages/Inbox";
import { Leads } from "./pages/Leads";
import { Review } from "./pages/Review";
import { Settings } from "./pages/Settings";
import { Summary } from "./pages/Summary";

export function App() {
  const location = useLocation();
  const [pending, setPending] = useState(0);
  const refreshCount = () => api.review("pending").then((r) => setPending(r.length)).catch(() => undefined);

  useEffect(() => {
    refreshCount();
    const t = setInterval(refreshCount, 3000);
    return () => clearInterval(t);
  }, [location.pathname]);

  if (location.pathname === "/contact") return <Contact />;

  const link = (to: string, label: string, extra?: React.ReactNode) => (
    <NavLink to={to} end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} data-testid={`nav-${label.split(" ")[0].toLowerCase()}`}>
      <span>{label}</span>
      {extra}
    </NavLink>
  );

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">F</span>Lead Qualifier</div>
        {link("/", "Inbox")}
        {link("/leads", "Leads")}
        {link("/review", "Review queue", pending > 0 ? <span className="nav-count" data-testid="review-count">{pending}</span> : null)}
        {link("/crm", "CRM")}
        {link("/summary", "Weekly summary")}
        {link("/settings", "Settings")}
        <NavLink to="/contact" className="nav-link"><span>Contact form &#8599;</span></NavLink>
        <div className="sidebar-foot">Fernhollow Digital (fictional)<br />Sample data only</div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Inbox />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/review" element={<Review onChange={refreshCount} />} />
          <Route path="/crm" element={<Crm />} />
          <Route path="/summary" element={<Summary />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
