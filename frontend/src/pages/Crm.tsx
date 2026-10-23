import { useEffect, useState } from "react";
import { api, CrmRecord } from "../api";
import { Score } from "../components/ui";

export function Crm() {
  const [records, setRecords] = useState<CrmRecord[]>([]);
  const [glow, setGlow] = useState<number | null>(null);

  useEffect(() => {
    api.crm().then((r) => {
      setRecords(r);
      const id = Number(new URLSearchParams(window.location.search).get("highlight"));
      if (id) setGlow(id);
    });
  }, []);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>CRM</h1>
          <p>Qualified leads, written only after someone approved them. Duplicates are matched by email and company.</p>
        </div>
        <span className="muted small">Mock CRM. A HubSpot adapter is included for a real account.</span>
      </div>
      <div className="card" style={{ overflow: "hidden" }}>
        {records.length === 0 ? (
          <div className="empty">Nothing in the CRM yet. Approve a qualified lead in the review queue.</div>
        ) : (
          <table data-testid="crm-table">
            <thead>
              <tr><th>Company</th><th>Contacts</th><th>Need</th><th>Budget</th><th>Score</th><th>Stage</th></tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id} className={glow === r.id ? "glow" : ""} data-testid="crm-row" data-company={r.company}>
                  <td>
                    <div style={{ fontWeight: 700 }}>{r.company}</div>
                    {r.merge_count > 0 && (
                      <span className="flag info" style={{ marginTop: 4 }} data-testid="merged-badge">
                        {r.source_message_ids.length} enquiries merged
                      </span>
                    )}
                  </td>
                  <td className="small">
                    {r.contacts.map((c) => (
                      <div key={c.email}>{c.name} <span className="faint">{c.email}</span></div>
                    ))}
                  </td>
                  <td className="small" style={{ whiteSpace: "pre-line", maxWidth: 320 }}>{r.need}</td>
                  <td className="small">{r.budget ?? <span className="faint">not stated</span>}</td>
                  <td><Score value={r.score} /></td>
                  <td><span className="tag Sales">{r.stage}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
