import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AMBER_FLAGS, api, FLAG_TEXT, ReviewItem } from "../api";
import { Flags, Score, Tag } from "../components/ui";

export function Review({ onChange }: { onChange: () => void }) {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [status, setStatus] = useState("pending");
  const [current, setCurrent] = useState<ReviewItem | null>(null);
  const [text, setText] = useState("");
  const [editing, setEditing] = useState(false);
  const [toast, setToast] = useState<{ msg: string; crmId?: number } | null>(null);
  const navigate = useNavigate();

  async function load(keepId?: number) {
    const list = await api.review(status);
    setItems(list);
    const next = list.find((i) => i.id === keepId) ?? list[0] ?? null;
    select(next);
  }

  function select(item: ReviewItem | null) {
    setCurrent(item);
    setText(item?.final_body ?? "");
    setEditing(false);
  }

  useEffect(() => {
    const id = Number(new URLSearchParams(window.location.search).get("item")) || undefined;
    load(id);
  }, [status]);

  function flash(msg: string, crmId?: number) {
    setToast({ msg, crmId });
    setTimeout(() => setToast(null), 4000);
  }

  async function approve() {
    if (!current) return;
    const done = await api.approve(current.id, text !== current.draft_body ? text : undefined);
    let crmId: number | undefined;
    if (done.crm_payload) {
      const records = await api.crm();
      crmId = records.find((r) => r.source_message_ids.includes(done.message.id))?.id;
    }
    const merged = done.flags.includes("merged_duplicate");
    flash(
      done.crm_payload ? (merged ? "Reply sent. Merged into an existing CRM record" : "Reply sent. Lead added to CRM") : "Reply sent",
      crmId,
    );
    onChange();
    load();
  }

  async function reject() {
    if (!current) return;
    await api.reject(current.id);
    flash("Draft rejected. Nothing was sent");
    onChange();
    load();
  }

  async function saveEdit() {
    if (!current) return;
    const saved = await api.saveEdit(current.id, text);
    setCurrent(saved);
    setEditing(false);
    flash("Edit saved");
  }

  const amberFlags = current?.flags.filter((f) => AMBER_FLAGS.has(f)) ?? [];
  const m = current?.message;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Review queue</h1>
          <p>Nothing is sent or written to the CRM until you approve it.</p>
        </div>
        <div className="toolbar">
          {["pending", "approved", "rejected"].map((s) => (
            <button key={s} className={`chip ${status === s ? "on" : ""}`} onClick={() => setStatus(s)}>
              {s[0].toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="review-grid">
        <div className="card review-list" data-testid="review-list">
          {items.length === 0 && <div className="empty">Queue is empty</div>}
          {items.map((i) => (
            <div
              key={i.id}
              className={`queue-item ${current?.id === i.id ? "selected" : ""} ${i.amber ? "amber" : ""}`}
              onClick={() => select(i)}
              data-testid="review-item"
              data-id={i.message.external_id ?? i.id}
            >
              <div className="row">
                <Tag category={i.kind === "sales" ? "Sales" : "Support"} />
                <span className="grow" />
                {i.kind === "sales" && <Score value={i.message.score} />}
              </div>
              <div style={{ fontWeight: 600 }}>{i.message.from_name}</div>
              <div className="muted small" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{i.message.subject}</div>
              <Flags flags={i.flags} />
            </div>
          ))}
        </div>

        {current && m && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }} data-testid="review-detail">
            {amberFlags.length > 0 && (
              <div className={`amber-banner ${amberFlags.includes("injection") ? "danger-banner" : ""}`} data-testid="amber-banner">
                <span style={{ fontSize: 18 }}>{amberFlags.includes("injection") ? "⛔" : "⚠"}</span>
                <div>
                  <strong>{amberFlags.includes("injection") ? "Suspicious instructions found" : "Needs a closer look"}</strong>
                  {amberFlags.map((f) => <div key={f} className="small">{FLAG_TEXT[f]}</div>)}
                  {m.injection_reasons.length > 0 && (
                    <div className="small" style={{ marginTop: 4 }}>Detected: {m.injection_reasons.join("; ")}</div>
                  )}
                </div>
              </div>
            )}

            <div className="card pad">
              <div className="row" style={{ marginBottom: 10 }}>
                <div className="grow">
                  <div style={{ fontWeight: 700 }}>{m.from_name} <span className="faint small">{m.from_email}</span></div>
                  <div className="muted small">{m.subject}</div>
                </div>
                <span className="small faint">AI confidence {Math.round(current.confidence * 100)}%</span>
              </div>
              <div className="email-box" data-testid="original-email">{m.body}</div>
              <div className="small muted" style={{ marginTop: 8 }}><strong>Why: </strong>{m.reason}</div>
            </div>

            <div className="card pad">
              <div className="row" style={{ marginBottom: 10 }}>
                <h2 className="grow" style={{ margin: 0 }}>Draft reply</h2>
                {current.edited_body !== null && <span className="flag info">Edited</span>}
              </div>
              <div className="small muted" style={{ marginBottom: 8 }}>Subject: {current.subject}</div>
              <textarea
                className="draft"
                value={text}
                readOnly={!editing || current.status !== "pending"}
                onChange={(e) => setText(e.target.value)}
                data-testid="draft-text"
              />
            </div>

            {current.kind === "support" && (
              <div className="card pad" data-testid="citations">
                <h3>Sources from the help docs</h3>
                {current.citations.length === 0 ? (
                  <div className="muted small">No help article covers this question.</div>
                ) : (
                  <div className="citations">
                    {current.citations.map((c, idx) => (
                      <div className="citation" key={idx} data-testid="citation">
                        <div className="citation-head">
                          <span>{c.doc_id}</span>
                          <span>{c.doc_title}</span>
                          <span className="faint" style={{ fontWeight: 500 }}>&rsaquo; {c.section}</span>
                          <span className="grow" />
                          {c.verified && <span className="flag info">Quote checked</span>}
                        </div>
                        <p className="citation-quote">{c.quote}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {current.crm_payload && (
              <div className="crm-preview" data-testid="crm-preview">
                <strong>On approval, this lead goes to the CRM:</strong>{" "}
                {String(current.crm_payload.name)}, {String(current.crm_payload.company)}, score {String(current.crm_payload.score)}
                {current.crm_payload.budget ? `, budget ${current.crm_payload.budget}` : ", no budget stated"}
              </div>
            )}

            {current.status === "pending" ? (
              <div className="actions">
                <button className="btn reject" onClick={reject} data-testid="reject">Reject</button>
                {editing ? (
                  <button className="btn" onClick={saveEdit} data-testid="save-edit">Save edit</button>
                ) : (
                  <button className="btn" onClick={() => setEditing(true)} data-testid="edit">Edit</button>
                )}
                <button className="btn approve lg" onClick={approve} data-testid="approve">Approve and send</button>
              </div>
            ) : (
              <div className="muted small" style={{ textAlign: "right" }}>
                {current.status === "approved" ? "Approved" : "Rejected"} by {current.decided_by}
              </div>
            )}
          </div>
        )}
      </div>

      {toast && (
        <div className="toast" data-testid="toast">
          {toast.msg}
          {toast.crmId && (
            <button className="btn" style={{ marginLeft: 12, padding: "4px 10px" }} onClick={() => navigate(`/crm?highlight=${toast.crmId}`)} data-testid="view-crm">
              View in CRM
            </button>
          )}
        </div>
      )}
    </>
  );
}
