import { useEffect, useState } from "react";
import { api } from "../api";

const CAT_COLORS: Record<string, string> = {
  Sales: "var(--sales)",
  Support: "var(--support)",
  Spam: "var(--spam)",
  Other: "var(--other)",
};

export function Summary() {
  const [s, setS] = useState<Record<string, any> | null>(null);
  useEffect(() => {
    api.summary().then(setS);
  }, []);
  if (!s) return null;
  if (s.empty) return <div className="empty">No enquiries yet</div>;

  const maxDay = Math.max(...s.per_day.map((d: any) => d.count), 1);
  const total = Object.values(s.by_category as Record<string, number>).reduce((a, b) => a + b, 0) || 1;

  return (
    <div data-testid="summary">
      <div className="page-head">
        <div>
          <h1>Weekly summary</h1>
          <p>Week ending {new Date(s.week_end).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</p>
        </div>
      </div>

      <div className="tiles">
        <div className="card tile"><div className="label">Enquiries in</div><div className="value">{s.enquiries_in}</div><div className="note">form and inbox</div></div>
        <div className="card tile"><div className="label">Qualified leads</div><div className="value" style={{ color: "var(--sales)" }}>{s.qualified_leads}</div><div className="note">{s.by_category.Sales} sales enquiries scored</div></div>
        <div className="card tile"><div className="label">In the CRM</div><div className="value">{s.crm_records}</div><div className="note">{s.duplicates_merged} duplicates merged</div></div>
        <div className="card tile">
          <div className="label">Time saved<span className="placeholder">Placeholder</span></div>
          <div className="value">{s.time_saved_hours}h</div>
          <div className="note">assumes {s.minutes_per_enquiry} min of manual triage per enquiry</div>
        </div>
      </div>

      <div className="split" style={{ marginTop: 18, gridTemplateColumns: "1fr 1fr" }}>
        <div className="card pad">
          <h2>Enquiries per day</h2>
          <div className="bars">
            {s.per_day.map((d: any) => (
              <div className="col" key={d.date}>
                <span className="small" style={{ fontWeight: 700 }}>{d.count}</span>
                <div className="fill" style={{ height: `${(d.count / maxDay) * 100}%` }} />
                <span className="small faint">{new Date(d.date).toLocaleDateString("en-GB", { weekday: "short" })}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card pad">
          <h2>How the AI sorted them</h2>
          <div className="stack" style={{ marginBottom: 14 }}>
            {Object.entries(s.by_category as Record<string, number>).map(([k, v]) => (
              <span key={k} style={{ width: `${(v / total) * 100}%`, background: CAT_COLORS[k] }} />
            ))}
          </div>
          {Object.entries(s.by_category as Record<string, number>).map(([k, v]) => (
            <div className="row" key={k} style={{ justifyContent: "space-between", padding: "4px 0" }}>
              <span className="row"><span style={{ width: 10, height: 10, borderRadius: 3, background: CAT_COLORS[k] }} />{k === "Sales" ? "Sales leads" : k}</span>
              <strong>{v}</strong>
            </div>
          ))}
          <hr style={{ border: 0, borderTop: "1px solid var(--border)", margin: "12px 0" }} />
          <div className="row" style={{ justifyContent: "space-between" }}><span>Drafts approved</span><strong>{s.drafts.approved}</strong></div>
          <div className="row" style={{ justifyContent: "space-between" }}><span>Drafts edited before sending</span><strong>{s.drafts.edited}</strong></div>
          <div className="row" style={{ justifyContent: "space-between" }}><span>Waiting for review</span><strong>{s.drafts.pending}</strong></div>
          <div className="row" style={{ justifyContent: "space-between" }}><span>Flagged amber for a person</span><strong>{s.amber_flagged}</strong></div>
          <div className="row" style={{ justifyContent: "space-between" }}><span>Hidden instructions caught</span><strong>{s.injection_flagged}</strong></div>
        </div>
      </div>
    </div>
  );
}
