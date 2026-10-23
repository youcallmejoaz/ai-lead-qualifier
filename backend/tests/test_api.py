import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.drafts.retriever import HelpDocRetriever
from app.main import create_app
from app.pipeline.process import Pipeline
from tests.fakes import FakeLLM


@pytest.fixture
def client(tmp_path):
    config = Config(database_url=f"sqlite:///{tmp_path / 'test.db'}", demo_mode=True)
    pipeline = Pipeline(FakeLLM(), HelpDocRetriever(), config)
    with TestClient(create_app(config, pipeline)) as c:
        yield c


def test_boot_seeds_and_processes(client):
    assert client.get("/api/health").json()["unprocessed"] == 0
    msgs = client.get("/api/messages").json()
    assert len(msgs) == 80
    assert {m["category"] for m in msgs} == {"Sales", "Support", "Spam", "Other"}


def test_leads_sorted_by_score(client):
    scores = [l["score"] for l in client.get("/api/leads").json()]
    assert scores == sorted(scores, reverse=True)


def test_review_flow_edit_approve_reject(client):
    items = client.get("/api/review").json()
    sales = next(i for i in items if i["kind"] == "sales")
    support = next(i for i in items if i["kind"] == "support")
    assert client.get("/api/crm").json() == []

    assert client.put(f"/api/review/{sales['id']}", json={"body": "Edited"}).json()["edited_body"] == "Edited"
    approved = client.post(f"/api/review/{sales['id']}/approve", json={"body": "Edited again"}).json()
    assert approved["status"] == "approved" and approved["final_body"] == "Edited again"
    assert len(client.get("/api/crm").json()) == 1
    assert client.post(f"/api/review/{sales['id']}/approve").status_code == 409

    assert client.post(f"/api/review/{support['id']}/reject").json()["status"] == "rejected"


def test_contact_form_is_processed(client):
    r = client.post("/api/form", json={
        "name": "Dana Whitlock", "email": "dana.whitlock@harbourline-freight.example",
        "company": "Harbourline Freight", "subject": "Automating booking emails into our TMS",
        "message": "Same as before"})
    assert r.status_code == 200 and r.json()["queued"] is False
    detail = client.get(f"/api/messages/{r.json()['id']}").json()
    assert detail["category"] == "Sales" and detail["fields"]["name"]["value"] == "Dana Whitlock"


def test_contact_form_validates_email(client):
    r = client.post("/api/form", json={"name": "x", "email": "not-an-email", "subject": "s", "message": "m"})
    assert r.status_code == 422


def test_settings_icp_validation_and_rescore(client):
    s = client.get("/api/settings").json()
    assert s["auto_approve_enabled"] is False
    bad = client.put("/api/settings", json={"icp_yaml": "weights: {a: 1}"})
    assert bad.status_code == 422
    ok = client.put("/api/settings", json={"icp_yaml": s["icp_yaml"].replace("qualify_threshold: 60", "qualify_threshold: 70")})
    assert ok.json()["rescored"] > 0


def test_summary(client):
    s = client.get("/api/summary").json()
    assert s["enquiries_in"] == 80 and s["processed"] == 80
    assert s["time_saved_is_placeholder"] is True


def test_help_doc(client):
    assert "Resetting your password" in client.get("/api/help/HD01").json()["markdown"]
    assert client.get("/api/help/HD99").status_code == 404


def test_reset(client):
    client.post(f"/api/review/{client.get('/api/review').json()[0]['id']}/reject")
    r = client.post("/api/admin/reset", params={"process": False}).json()
    assert r == {"seeded": 80, "processed": 0}
    assert client.get("/api/health").json()["unprocessed"] == 80
