"""Gmail adapter (stub).

The production version would use the Gmail API with OAuth:
1. users.messages.list with a label or query (for example `label:enquiries is:unread`).
2. users.messages.get for each id, decode the MIME body, and create a Message with source="gmail".
3. Add a "processed" label so the same email is not imported twice.
Approved replies would be sent with users.drafts.create + users.drafts.send, behind the
same approval check as the simulated outbox.
"""

from sqlalchemy.orm import Session


class GmailInbox:
    def __init__(self, credentials_path: str, label: str = "enquiries"):
        self.credentials_path = credentials_path
        self.label = label

    def fetch_new(self, session: Session) -> int:
        raise NotImplementedError("Connect Gmail OAuth credentials to enable this adapter")
