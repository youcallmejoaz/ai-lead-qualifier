"""HubSpot style adapter (stub).

Shows how a real CRM plugs in: map our fields to CRM properties, search for an
existing contact by email and a company by name or domain, then create or update.
The HTTP calls are left unimplemented so the demo never touches a real account.
"""

from typing import Any

from app.crm.base import CRMAdapter, LeadPayload, UpsertResult
from app.review.approval import Approval, verify


def to_hubspot_properties(payload: LeadPayload) -> dict[str, Any]:
    first, _, last = payload.name.partition(" ")
    return {
        "email": payload.email,
        "firstname": first,
        "lastname": last,
        "company": payload.company,
        "hs_lead_status": "OPEN",
        "lead_score": payload.score,
        "lead_need": payload.need or "",
        "lead_budget": payload.budget or "",
        "lead_timeline": payload.timeline or "",
    }


class HubSpotCRM(CRMAdapter):
    def __init__(self, access_token: str):
        self.access_token = access_token

    def upsert_lead(self, payload: LeadPayload, approval: Approval) -> UpsertResult:
        verify(approval)
        # 1. POST /crm/v3/objects/contacts/search  (filter email == payload.email)
        # 2. POST /crm/v3/objects/companies/search (name or domain)
        # 3. PATCH the existing contact, or POST /crm/v3/objects/contacts with
        #    to_hubspot_properties(payload), then associate it with the company.
        raise NotImplementedError("Connect a HubSpot private app token to enable this adapter")
