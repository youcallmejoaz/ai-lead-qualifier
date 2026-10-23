import { useEffect, useState } from "react";
import { api, MessageDetail } from "../api";
import { LeadCard } from "../components/LeadCard";
import { Flags, Score } from "../components/ui";

export function Leads() {
  const [leads, setLeads] = useState<MessageDetail[]>([]);
  const [selected, setSelected] = useState<MessageDetail | null>(null);

  useEffect(() => {
    api.leads().then(setLeads);
  }, []);

  const qualified = leads.filter((l) => l.qualified).length;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Leads</h1>
          <p>Sales enquiries scored against your ideal customer profile. Strongest first. {qualified} of {leads.length} qualified.</p>
        </div>
      </div>
      <div className={selected ? "split" : ""}>
        <div className="card" style={{ overflow: "hidden" }}>
          <table data-testid="leads-table">
            <thead>
              <tr><th>#</th><th>Score</th><th>Contact</th><th>Need</th><th>Budget</th><th>Timeline</th></tr>
            </thead>
            <tbody>
              {leads.map((l, i) => {
                const f = l.fields ?? {};
                return (
                  <tr key={l.id} className={`clickable ${selected?.id === l.id ? "selected" : ""}`} onClick={() => setSelected(l)} data-testid="lead-row">
                    <td className="rank">{i + 1}</td>
                    <td><Score value={l.score} /></td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{l.from_name}</div>
                      <div className="muted small">{(f.company?.value as string) ?? l.company ?? ""}</div>
                      {l.flags.length > 0 && <div style={{ marginTop: 4 }}><Flags flags={l.flags} /></div>}
                    </td>
                    <td className="small">{(f.need?.value as string) ?? <span className="faint">not stated</span>}</td>
                    <td className="small">{(f.budget?.value as string) ?? <span className="faint">not stated</span>}</td>
                    <td className="small">{(f.timeline?.value as string) ?? <span className="faint">not stated</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {selected && (
          <div className="sticky">
            <div className="row" style={{ justifyContent: "flex-end", marginBottom: 8 }}>
              <button className="btn" onClick={() => setSelected(null)}>Close</button>
            </div>
            <LeadCard lead={selected} />
          </div>
        )}
      </div>
    </>
  );
}
