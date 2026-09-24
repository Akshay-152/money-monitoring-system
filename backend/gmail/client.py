"""Gmail client boundary; credentials are intentionally supplied by deployment."""
class GmailClient:
    """Encapsulate Gmail watch/history calls so the parser stays provider-independent."""
    def __init__(self, service=None):
        self.service = service

    def watch(self, user_id="me", topic_name=""):
        """Register an INBOX watch when an authenticated Gmail service is available."""
        if not self.service:
            raise RuntimeError("Gmail OAuth is not configured")
        return self.service.users().watch(userId=user_id, body={"labelIds": ["INBOX"], "topicName": topic_name}).execute()
