import { useEffect, useRef, useState } from "react";
import { api, Category, MessageDetail, MessageRow } from "../api";
import { LeadCard } from "../components/LeadCard";
import { Flags, Score, Tag, when } from "../components/ui";

const FILTERS: (Category | "All")[] = ["All", "Sales", "Support", "Spam", "Other"];

export function Inbox() {
  const [rows, setRows] = useState<MessageRow[]>([]);
  const [filter, setFilter] = useState<Category | "All">("All");
  const [selected, setSelected] = useState<MessageDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(0);
  const seen = useRef<Map<number, string | null>>(new Map());
  const [fresh, setFresh] = useState<Set<number>>(new Set());

  async function refresh() {
    const [msgs, health] = await Promise.all([api.messages(), api.health()]);
    const changed = new Set<number>();
    for (const m of msgs) {
      if (seen.current.has(m.id) && seen.current.get(m.id) !== m.category) changed.add(m.id);
      seen.current.set(m.id, m.category);
    }
    if (changed.size) setFresh(changed);
    setRows(msgs);
    setPending(health.unprocessed);
    setBusy(health.processing);
    return health;
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!busy) return;
    const t = setInterval(refresh, 500);
    return () => clearInterval(t);
  }, [busy]);

  async function processInbox() {
    await api.processInbox(450);
    setBusy(true);
  }

  async function open(row: MessageRow) {
    setSelected(await api.message(row.id));
  }

  const shown = filter === "All" ? rows : rows.filter((r) => r.category === filter);
  const counts = (c: Category) => rows.filter((r) => r.category === c).length;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Inbox</h1>
          <p>Every enquiry from the contact form and the shared inbox, sorted by AI.</p>
        </div>
        <div className="toolbar">
          {pending > 0 && <span className="muted small">{pending} waiting</span>}
          <button className="btn primary" onClick={processInbox} disabled={busy || pending === 0} data-testid="process-inbox">
            {busy ? "Sorting..." : "Sort new enquiries"}
          </button>
        </div>
      </div>

      <div className="toolbar" style={{ marginBottom: 14 }}>
        {FILTERS.map((f) => (
          <button key={f} className={`chip ${filter === f ? "on" : ""}`} onClick={() => setFilter(f)} data-testid={`filter-${f}`}>
            {f === "All" ? `All ${rows.length}` : `${f === "Sales" ? "Sales leads" : f} ${counts(f)}`}
          </button>
        ))}
      </div>

      <div className={selected ? "split" : ""}>
        <div className="card list" data-testid="inbox-list" style={{ overflow: "hidden" }}>
          {shown.length === 0 && <div className="empty">No messages</div>}
          {shown.map((r) => (
            <div
              key={r.id}
              className={`msg-row ${r.amber ? "amber" : ""} ${selected?.id === r.id ? "selected" : ""} ${fresh.has(r.id) ? "fresh" : ""}`}
              onClick={() => open(r)}
              data-testid="inbox-row"
              data-id={r.external_id ?? r.id}
            >
              <div><Tag category={r.status === "new" ? null : r.category} /></div>
              <div className="msg-from">
                {r.from_name}
                <div className="faint small" style={{ fontWeight: 400 }}>{when(r.received_at)}</div>
              </div>
              <div style={{ minWidth: 0 }}>
                <div className="msg-subject">{r.subject}</div>
                <div className="msg-reason">{r.reason ?? r.snippet}</div>
                {r.flags.length > 0 && <div style={{ marginTop: 4 }}><Flags flags={r.flags} /></div>}
              </div>
              <div style={{ textAlign: "right" }}>{r.category === "Sales" && <Score value={r.score} />}</div>
            </div>
          ))}
        </div>
        {selected && (
          <div className="sticky">
            <div className="row" style={{ justifyContent: "flex-end", marginBottom: 8 }}>
              <button className="btn" onClick={() => setSelected(null)}>Close</button>
            </div>
            <LeadCard lead={selected} />
            <div className="card pad" style={{ marginTop: 12 }}>
              <h3>Original email</h3>
              <div className="email-box">{selected.body}</div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
