import { AMBER_FLAGS, Category, FLAG_TEXT } from "../api";

export function Tag({ category }: { category: Category | null }) {
  if (!category) return <span className="tag pending">Sorting</span>;
  return <span className={`tag ${category}`} data-testid="tag">{category === "Sales" ? "Sales lead" : category}</span>;
}

export function Score({ value }: { value: number | null }) {
  if (value === null) return <span className="faint">-</span>;
  const band = value >= 70 ? "high" : value >= 45 ? "mid" : "low";
  return <span className={`score ${band}`} data-testid="score">{value}</span>;
}

const FLAG_LABEL: Record<string, string> = {
  low_confidence: "Low confidence",
  unsure_fields: "Unsure fields",
  injection: "Hidden instructions",
  parse_failed: "Needs a person",
  no_citation: "No citation",
  no_relevant_doc: "No matching doc",
  draft_failed: "Draft failed",
  sales_opportunity: "Sales opportunity",
  merged_duplicate: "Duplicate merged",
};

export function Flags({ flags }: { flags: string[] }) {
  if (!flags.length) return null;
  return (
    <span className="row" style={{ gap: 6, flexWrap: "wrap" }}>
      {flags.map((f) => (
        <span
          key={f}
          className={`flag ${f === "injection" ? "danger" : AMBER_FLAGS.has(f) ? "" : "info"}`}
          title={FLAG_TEXT[f]}
          data-testid={`flag-${f}`}
        >
          {FLAG_LABEL[f] ?? f}
        </span>
      ))}
    </span>
  );
}

export function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.8 ? "var(--sales)" : value >= 0.5 ? "var(--amber-line)" : "var(--spam)";
  return (
    <div className="row" style={{ gap: 6 }} title={`${pct}% confident`}>
      <div className="conf" style={{ flex: 1 }}>
        <span style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="small faint" style={{ width: 32, textAlign: "right" }}>{pct}%</span>
    </div>
  );
}

export function when(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
}
