from app.services.llm_client import LLMClient


class DocumentVerifier:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or LLMClient()

    def process_document(self, document):
        if self._looks_fake(document):
            return {
                "is_valid": False,
                "confidence": 0.0,
                "message": "Document contains unsupported or fake identifiers.",
                "evidence": ["fake_id"],
                "source": "validation",
            }

        response = self.llm_client.send_request(document)
        return response

    def check_validity(self, document):
        validity_check = self.llm_client.send_request({"action": "check_validity", "document": document})
        return validity_check.get("is_valid", False)

    def _looks_fake(self, document):
        if not isinstance(document, dict):
            return False

        document_types = document.get("documents") or []
        if isinstance(document_types, str):
            document_types = [document_types]

        for item in document_types:
            if isinstance(item, str) and "fake" in item.lower():
                return True

        return bool(document.get("document_type") and "fake" in str(document.get("document_type")).lower())