import { MessageDetail } from "../api";
import { ConfBar, Flags, Tag } from "./ui";

const FIELD_LABELS: [string, string][] = [
  ["name", "Name"],
  ["company", "Company"],
  ["need", "Need"],
  ["budget", "Budget"],
  ["timeline", "Timeline"],
  ["industry", "Industry"],
  ["company_size", "Company size"],
  ["urgency", "Urgency"],
];

function fmt(key: string, value: unknown) {
  if (value === null || value === undefined || value === "unknown") return null;
  if (key === "company_size") return `${Number(value).toLocaleString()} staff`;
  return String(value);
}

export function LeadCard({ lead }: { lead: MessageDetail }) {
  const score = lead.score ?? 0;
  const ringColor = score >= 70 ? "var(--sales)" : score >= 45 ? "var(--amber-line)" : "var(--faint)";
  return (
    <div className="card pad lead-card" data-testid="lead-card">
      <div className="lead-top">
        {lead.score !== null && (
          <div className="ring" style={{ background: `conic-gradient(${ringColor} ${score * 3.6}deg, var(--surface-2) 0)` }}>
            <div className="ring-inner" data-testid="lead-score">{score}</div>
          </div>
        )}
        <div className="grow">
          <div className="row" style={{ marginBottom: 4 }}>
            <Tag category={lead.category} />
            {lead.qualified && <span className="flag info">Qualified</span>}
          </div>
          <div style={{ fontWeight: 700, fontSize: 17 }}>{lead.from_name}</div>
          <div className="muted small">{lead.subject}</div>
        </div>
      </div>

      <div className="reason" data-testid="lead-reason">
        <strong>Why: </strong>{lead.reason}
        {lead.confidence !== null && <span className="faint"> ({Math.round(lead.confidence * 100)}% sure)</span>}
      </div>

      <Flags flags={lead.flags} />

      {lead.fields && (
        <div>
          <h3>Extracted fields</h3>
          <div className="fields" data-testid="lead-fields">
            {FIELD_LABELS.map(([key, label]) => {
              const f = lead.fields![key];
              const v = fmt(key, f?.value);
              return [
                <span key={`${key}k`} className="k">{label}</span>,
                <span key={`${key}v`} className={`v ${v ? "" : "null"}`}>{v ?? "not stated"}</span>,
                <span key={`${key}c`}><ConfBar value={f?.confidence ?? 0} /></span>,
              ];
            })}
          </div>
        </div>
      )}

      {lead.score_breakdown && (
        <div>
          <h3>Score against your ideal customer</h3>
          <div className="breakdown">
            {lead.score_breakdown.map((b) => (
              <div className="breakdown-row" key={b.factor}>
                <span className="muted">{b.factor.replace("_", " ")}</span>
                <div className="bar" title={b.note}><span style={{ width: `${(b.points / b.max) * 100}%` }} /></div>
                <span className="small" style={{ textAlign: "right" }}>{Math.round(b.points)}/{b.max}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
