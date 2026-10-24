"""FastAPI app: API routes plus the built React front end."""

import logging
import threading
import time
from contextlib import asynccontextmanager

import yaml
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import logging_pii
from app.api.serialize import crm_row, message_detail, message_row, review_row
from app.api.summary import weekly_summary
from app.config import ROOT_DIR, Config, get_config
from app.db import Base, init_db, make_engine, make_session_factory, session_scope
from app.drafts.retriever import HelpDocRetriever
from app.intake.form import ContactForm, create_from_form
from app.intake.inbox_sim import seed_inbox
from app.llm.cache import ResponseCache
from app.llm.client import ClaudeClient, LLMUnavailable
from app.models import CrmRecord, Message, ReviewItem
from app.pipeline.process import Pipeline, process_message, rescore_all, unprocessed
from app.pipeline.scoring import parse_icp
from app.review import service as review
from app.settings_store import all_settings, set_setting

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging_pii.install()
log = logging.getLogger("app")

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
HELP_DOCS = ROOT_DIR / "data" / "help_docs"


class State:
    def __init__(self, config: Config, pipeline: Pipeline | None = None):
        self.config = config
        self.engine = make_engine(config.database_url)
        init_db(self.engine)
        self.sessions = make_session_factory(self.engine)
        self.pipeline = pipeline or Pipeline(
            llm=ClaudeClient(
                ResponseCache(config.cache_path),
                live=config.llm_mode == "live",
                has_key=config.has_api_key,
                daily_limit=config.daily_call_limit,
            ),
            retriever=HelpDocRetriever(),
            config=config,
        )
        # SQLite and the review rules are simplest with one writer at a time.
        self.lock = threading.Lock()
        self.batch_running = False

    def process_pending(self, delay_ms: int = 0) -> int:
        done = 0
        with session_scope(self.sessions) as session:
            # Newest first, so the top of the inbox fills in first.
            ids = [m.id for m in reversed(unprocessed(session))]
        for mid in ids:
            done += self.process_one(mid)
            if delay_ms:
                time.sleep(delay_ms / 1000)
        return done

    def process_one(self, mid: int) -> bool:
        with self.lock, session_scope(self.sessions) as session:
            msg = session.get(Message, mid)
            if msg is None or msg.status != "new":
                return False
            try:
                process_message(session, self.pipeline, msg)
                return True
            except LLMUnavailable:
                log.warning("message %s left unprocessed: no cached result and no live Claude", mid)
                return False


def create_app(config: Config | None = None, pipeline: Pipeline | None = None, seed: bool = True) -> FastAPI:
    config = config or get_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state = State(config, pipeline)
        app.state.s = state
        if seed:
            with session_scope(state.sessions) as session:
                added = seed_inbox(session)
            if added:
                n = state.process_pending()
                log.info("seeded %s sample enquiries, processed %s", added, n)
        yield

    app = FastAPI(title="AI Lead Qualifier", lifespan=lifespan)

    def st(request: Request) -> State:
        return request.app.state.s

    def db(request: Request):
        with session_scope(st(request).sessions) as session:
            yield session

    # ---------- status ----------
    @app.get("/api/health")
    def health(request: Request, session: Session = Depends(db)):
        s = st(request)
        return {
            "ok": True,
            "llm_mode": s.config.llm_mode,
            "live_claude": s.config.llm_mode == "live" and s.config.has_api_key,
            "unprocessed": len(unprocessed(session)),
            "processing": s.batch_running,
            "demo_mode": s.config.demo_mode,
        }

    # ---------- intake ----------
    @app.post("/api/form")
    def submit_form(form: ContactForm, request: Request):
        s = st(request)
        with s.lock, session_scope(s.sessions) as session:
            mid = create_from_form(session, form).id
        # The visitor gets an instant reply; triage and drafting run in the background.
        threading.Thread(target=s.process_one, args=(mid,), daemon=True).start()
        return {"id": mid, "queued": True}

    @app.post("/api/inbox/process")
    def process_inbox(request: Request, delay_ms: int = 0):
        s = st(request)
        if s.batch_running:
            return {"started": False, "reason": "already running"}

        def run():
            s.batch_running = True
            try:
                s.process_pending(delay_ms=max(0, min(delay_ms, 5000)))
            finally:
                s.batch_running = False

        threading.Thread(target=run, daemon=True).start()
        return {"started": True}

    # ---------- inbox and leads ----------
    @app.get("/api/messages")
    def list_messages(session: Session = Depends(db), category: str | None = None):
        msgs = session.scalars(select(Message).order_by(Message.received_at.desc())).all()
        rows = [message_row(m) for m in msgs]
        if category:
            rows = [r for r in rows if r["category"] == category]
        return rows

    @app.get("/api/messages/{message_id}")
    def get_message(message_id: int, session: Session = Depends(db)):
        msg = session.get(Message, message_id)
        if msg is None:
            raise HTTPException(404, "Message not found")
        return message_detail(msg)

    @app.get("/api/leads")
    def list_leads(session: Session = Depends(db)):
        msgs = session.scalars(select(Message)).all()
        leads = [message_detail(m) for m in msgs if m.classification and m.classification.category == "Sales" and m.lead]
        return sorted(leads, key=lambda r: (-r["score"], r["received_at"]))

    @app.get("/api/crm")
    def list_crm(session: Session = Depends(db)):
        records = session.scalars(select(CrmRecord).order_by(CrmRecord.updated_at.desc())).all()
        return [crm_row(r) for r in records]

    # ---------- review queue ----------
    @app.get("/api/review")
    def list_review(session: Session = Depends(db), status: str | None = "pending"):
        q = select(ReviewItem).order_by(ReviewItem.created_at)
        if status and status != "all":
            q = q.where(ReviewItem.status == status)
        return [review_row(i) for i in session.scalars(q)]

    @app.get("/api/review/{item_id}")
    def get_review(item_id: int, session: Session = Depends(db)):
        item = session.get(ReviewItem, item_id)
        if item is None:
            raise HTTPException(404, "Review item not found")
        return review_row(item)

    class EditBody(BaseModel):
        body: str = Field(min_length=1)

    class ApproveBody(BaseModel):
        body: str | None = None

    def _review_action(request: Request, fn):
        s = st(request)
        with s.lock, session_scope(s.sessions) as session:
            try:
                return review_row(fn(session))
            except review.ReviewError as exc:
                raise HTTPException(409, str(exc)) from exc

    @app.put("/api/review/{item_id}")
    def edit_review(item_id: int, payload: EditBody, request: Request):
        return _review_action(request, lambda session: review.save_edit(session, item_id, payload.body))

    @app.post("/api/review/{item_id}/approve")
    def approve_review(item_id: int, request: Request, payload: ApproveBody | None = None):
        body = payload.body if payload else None
        return _review_action(request, lambda session: review.approve(session, item_id, edited_body=body))

    @app.post("/api/review/{item_id}/reject")
    def reject_review(item_id: int, request: Request):
        return _review_action(request, lambda session: review.reject(session, item_id))

    # ---------- help docs ----------
    @app.get("/api/help/{doc_id}")
    def help_doc(doc_id: str):
        match = [p for p in HELP_DOCS.glob(f"{doc_id}_*.md") if p.stem.split("_", 1)[0] == doc_id]
        if not match:
            raise HTTPException(404, "Article not found")
        return {"doc_id": doc_id, "markdown": match[0].read_text()}

    # ---------- summary and settings ----------
    @app.get("/api/summary")
    def summary(session: Session = Depends(db)):
        return weekly_summary(session)

    @app.get("/api/settings")
    def get_settings(session: Session = Depends(db)):
        values = all_settings(session)
        values["icp_yaml"] = yaml.safe_dump(values.pop("icp"), sort_keys=False)
        return values

    class SettingsBody(BaseModel):
        auto_approve_enabled: bool | None = None
        auto_approve_threshold: float | None = Field(default=None, ge=0.5, le=1.0)
        amber_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
        icp_yaml: str | None = None

    @app.put("/api/settings")
    def put_settings(payload: SettingsBody, request: Request):
        s = st(request)
        with s.lock, session_scope(s.sessions) as session:
            for key in ("auto_approve_enabled", "auto_approve_threshold", "amber_threshold"):
                value = getattr(payload, key)
                if value is not None:
                    set_setting(session, key, value)
            rescored = 0
            if payload.icp_yaml is not None:
                try:
                    icp = parse_icp(payload.icp_yaml)
                except (ValueError, yaml.YAMLError) as exc:
                    raise HTTPException(422, f"ICP not saved: {exc}") from exc
                set_setting(session, "icp", icp)
                rescored = rescore_all(session)
            return {"saved": True, "rescored": rescored}

    # ---------- demo helpers ----------
    @app.post("/api/admin/reset")
    def reset(request: Request, process: bool = True):
        s = st(request)
        if not s.config.demo_mode:
            raise HTTPException(403, "Reset is only available in demo mode")
        with s.lock:
            Base.metadata.drop_all(s.engine)
            init_db(s.engine)
            with session_scope(s.sessions) as session:
                added = seed_inbox(session)
        processed = s.process_pending() if process else 0
        return {"seeded": added, "processed": processed}

    # ---------- front end ----------
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            candidate = FRONTEND_DIST / path
            if path and candidate.is_file() and FRONTEND_DIST in candidate.resolve().parents:
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
