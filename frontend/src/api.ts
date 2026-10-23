export type Category = "Sales" | "Support" | "Spam" | "Other";

export interface FieldValue<T = string | number | null> {
  value: T;
  confidence: number;
}

export interface MessageRow {
  id: number;
  external_id: string | null;
  source: string;
  from_name: string;
  from_email: string;
  company: string | null;
  subject: string;
  snippet: string;
  received_at: string;
  status: string;
  category: Category | null;
  confidence: number | null;
  reason: string | null;
  injection: boolean;
  score: number | null;
  qualified: boolean;
  flags: string[];
  amber: boolean;
  review_id: number | null;
  review_status: string | null;
}

export interface MessageDetail extends MessageRow {
  body: string;
  injection_reasons: string[];
  model: string | null;
  fields: Record<string, FieldValue> | null;
  score_breakdown: { factor: string; points: number; max: number; note: string }[] | null;
}

export interface Citation {
  passage_id: string;
  doc_id: string;
  doc_title: string;
  section: string;
  quote: string;
  verified: boolean;
}

export interface ReviewItem {
  id: number;
  kind: "sales" | "support";
  status: "pending" | "approved" | "rejected";
  subject: string;
  draft_body: string;
  edited_body: string | null;
  final_body: string;
  citations: Citation[];
  crm_payload: Record<string, string | number | null> | null;
  flags: string[];
  amber: boolean;
  confidence: number;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string;
  message: MessageDetail;
}

export interface CrmRecord {
  id: number;
  company: string;
  primary_name: string;
  primary_email: string;
  contacts: { name: string; email: string }[];
  need: string | null;
  budget: string | null;
  timeline: string | null;
  score: number;
  stage: string;
  source_message_ids: number[];
  merge_count: number;
  created_at: string;
  updated_at: string;
}

export interface Health {
  ok: boolean;
  llm_mode: string;
  live_claude: boolean;
  unprocessed: number;
  processing: boolean;
  demo_mode: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  messages: () => request<MessageRow[]>("/api/messages"),
  message: (id: number) => request<MessageDetail>(`/api/messages/${id}`),
  leads: () => request<MessageDetail[]>("/api/leads"),
  crm: () => request<CrmRecord[]>("/api/crm"),
  review: (status = "pending") => request<ReviewItem[]>(`/api/review?status=${status}`),
  saveEdit: (id: number, body: string) =>
    request<ReviewItem>(`/api/review/${id}`, { method: "PUT", body: JSON.stringify({ body }) }),
  approve: (id: number, body?: string) =>
    request<ReviewItem>(`/api/review/${id}/approve`, { method: "POST", body: JSON.stringify({ body: body ?? null }) }),
  reject: (id: number) => request<ReviewItem>(`/api/review/${id}/reject`, { method: "POST" }),
  processInbox: (delayMs = 0) => request<{ started: boolean }>(`/api/inbox/process?delay_ms=${delayMs}`, { method: "POST" }),
  submitForm: (form: { name: string; email: string; company: string; subject: string; message: string }) =>
    request<{ id: number; queued: boolean }>("/api/form", { method: "POST", body: JSON.stringify(form) }),
  summary: () => request<Record<string, any>>("/api/summary"),
  settings: () => request<Record<string, any>>("/api/settings"),
  saveSettings: (body: Record<string, unknown>) =>
    request<{ saved: boolean; rescored: number }>("/api/settings", { method: "PUT", body: JSON.stringify(body) }),
  helpDoc: (docId: string) => request<{ doc_id: string; markdown: string }>(`/api/help/${docId}`),
};

export const FLAG_TEXT: Record<string, string> = {
  low_confidence: "The AI is unsure about the category",
  unsure_fields: "Some key details could not be confirmed",
  injection: "Contains instructions aimed at the AI. Treated as data, not followed",
  parse_failed: "The AI output could not be read. Needs a person",
  no_citation: "The draft has no help doc citation",
  no_relevant_doc: "No help article answers this. A holding reply was drafted",
  draft_failed: "The draft could not be generated",
  sales_opportunity: "Support email from a strong prospect. Worth a sales follow up",
  merged_duplicate: "Merged into an existing CRM record",
};

export const AMBER_FLAGS = new Set([
  "low_confidence",
  "unsure_fields",
  "injection",
  "parse_failed",
  "no_citation",
  "no_relevant_doc",
  "draft_failed",
]);
