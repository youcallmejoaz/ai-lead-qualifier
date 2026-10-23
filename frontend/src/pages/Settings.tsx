import { useEffect, useState } from "react";
import { api } from "../api";

export function Settings() {
  const [s, setS] = useState<Record<string, any> | null>(null);
  const [yamlText, setYamlText] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.settings().then((v) => {
      setS(v);
      setYamlText(v.icp_yaml);
    });
  }, []);

  async function save(body: Record<string, unknown>) {
    setError(null);
    try {
      const r = await api.saveSettings(body);
      setNote(r.rescored ? `Saved. ${r.rescored} leads rescored.` : "Saved.");
      setS({ ...s, ...body });
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (!s) return null;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p>Review rules and your ideal customer profile.</p>
        </div>
        {note && <span className="flag info">{note}</span>}
      </div>
      <div className="split" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="card pad" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h2>Review gate</h2>
          <label className="switch">
            <input
              type="checkbox"
              checked={s.auto_approve_enabled}
              onChange={(e) => save({ auto_approve_enabled: e.target.checked })}
              data-testid="auto-approve"
            />
            Auto approve high confidence items
          </label>
          <div className="small muted">
            Off by default. When on, items at or above the threshold are sent without a click. Amber items
            (low confidence, unsure fields, hidden instructions, missing citations) always wait for a person.
          </div>
          <label className="row small">
            <span className="grow">Auto approve threshold</span>
            <input type="number" min={0.5} max={1} step={0.01} defaultValue={s.auto_approve_threshold}
              onBlur={(e) => save({ auto_approve_threshold: Number(e.target.value) })} style={{ width: 90 }} />
          </label>
          <label className="row small">
            <span className="grow">Flag amber below this confidence</span>
            <input type="number" min={0} max={1} step={0.01} defaultValue={s.amber_threshold}
              onBlur={(e) => save({ amber_threshold: Number(e.target.value) })} style={{ width: 90 }} />
          </label>
        </div>
        <div className="card pad">
          <h2>Ideal customer profile</h2>
          <p className="small muted" style={{ marginTop: 0 }}>Scores are worked out from these rules, so changing them rescores every lead.</p>
          <textarea className="yaml" value={yamlText} onChange={(e) => setYamlText(e.target.value)} spellCheck={false} />
          {error && <div className="flag danger" style={{ margin: "8px 0" }}>{error}</div>}
          <div className="actions" style={{ marginTop: 10 }}>
            <button className="btn primary" onClick={() => save({ icp_yaml: yamlText })}>Save and rescore</button>
          </div>
        </div>
      </div>
    </>
  );
}
