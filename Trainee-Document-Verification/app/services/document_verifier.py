from app.services.llm_client import LLMClient


class DocumentVerifier:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or LLMClient()

    def process_document(self, document):
        if not isinstance(document, dict):
            return {
                "is_valid": False,
                "confidence": 0.0,
                "message": "Invalid document format.",
                "evidence": [],
                "source": "validation",
            }

        if not document:
            return {
                "is_valid": False,
                "confidence": 0.0,
                "message": "No document provided.",
                "evidence": [],
                "source": "validation",
            }

        if self._looks_fake(document):
            return {
                "is_valid": False,
                "confidence": 0.0,
                "message": "Document contains unsupported or fake identifiers.",
                "evidence": ["fake_id"],
                "source": "validation",
            }

        if getattr(self.llm_client, "api_key", None) in (None, ""):
            return self._local_validation_response(document)

        response = self.llm_client.send_request(document)
        return response

    def check_validity(self, document):
        response = self.process_document(document)
        return response.get("is_valid", False)

    def _looks_fake(self, document):
        if not isinstance(document, dict):
            return False

        fake_keywords = ["fake", "dummy", "sample"]
        fields = [
            document.get("document_type"),
            document.get("document_name"),
            document.get("name"),
            document.get("documents"),
        ]

        for value in fields:
            if isinstance(value, str):
                if any(keyword in value.lower() for keyword in fake_keywords):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and any(keyword in item.lower() for keyword in fake_keywords):
                        return True

        return False

    def _local_validation_response(self, document):
        name = document.get("name") or document.get("full_name")
        id_number = document.get("id") or document.get("trainee_id") or document.get("id_number")

        if name and id_number:
            return {
                "is_valid": True,
                "confidence": 0.7,
                "message": "Document passed local verification.",
                "evidence": ["Name and identity fields are present"],
                "source": "local",
            }

        return {
            "is_valid": False,
            "confidence": 0.0,
            "message": "Document is missing required fields.",
            "evidence": [],
            "source": "local",
        }