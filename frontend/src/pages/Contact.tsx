import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const EMPTY = { name: "", email: "", company: "", subject: "", message: "" };

export function Contact() {
  const [form, setForm] = useState(EMPTY);
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState("");

  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setState("sending");
    try {
      await api.submitForm(form);
      setState("sent");
    } catch (err) {
      setError((err as Error).message);
      setState("error");
    }
  }

  return (
    <div className="site">
      <nav className="site-nav">
        <div className="brand"><span className="brand-mark" style={{ color: "#fff" }}>F</span>Fernhollow Digital</div>
        <div className="row muted small" style={{ gap: 24 }}>
          <span>Services</span><span>Work</span><span>About</span><strong style={{ color: "var(--text)" }}>Contact</strong>
        </div>
      </nav>
      <section className="site-hero">
        <div>
          <h1>Let's take the busywork off your team.</h1>
          <p className="lead">We build automations, AI assistants and integrations for growing businesses. Tell us what's slowing you down and we'll reply within one business day.</p>
          <p className="small faint" style={{ marginTop: 40 }}>Fernhollow Digital is a fictional company used for this demo.</p>
        </div>
        <div className="card pad" style={{ padding: 28 }}>
          {state === "sent" ? (
            <div data-testid="form-sent">
              <h2>Thanks, we've got it.</h2>
              <p className="muted">Your message is in our inbox. Someone from the team will reply soon.</p>
              <div className="row" style={{ marginTop: 16 }}>
                <button className="btn" onClick={() => { setForm(EMPTY); setState("idle"); }}>Send another</button>
                <Link className="btn primary" to="/" data-testid="go-inbox">Open the inbox (demo)</Link>
              </div>
            </div>
          ) : (
            <form className="form" onSubmit={submit} data-testid="contact-form">
              <h2 style={{ marginBottom: 0 }}>Contact us</h2>
              <div className="two">
                <label>Name<input required value={form.name} onChange={set("name")} name="name" /></label>
                <label>Work email<input required type="email" value={form.email} onChange={set("email")} name="email" /></label>
              </div>
              <label>Company<input value={form.company} onChange={set("company")} name="company" /></label>
              <label>Subject<input required value={form.subject} onChange={set("subject")} name="subject" /></label>
              <label>How can we help?<textarea required value={form.message} onChange={set("message")} name="message" /></label>
              {state === "error" && <div className="flag danger">{error}</div>}
              <button className="btn primary lg" type="submit" disabled={state === "sending"} data-testid="form-submit">
                {state === "sending" ? "Sending..." : "Send enquiry"}
              </button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
