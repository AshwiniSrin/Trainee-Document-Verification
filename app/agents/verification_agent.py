from app.services.document_verifier import DocumentVerifier
from app.services.llm_client import LLMClient


class VerificationAgent:
    def __init__(self, llm_client=None, document_verifier=None):
        self.llm_client = llm_client or LLMClient()
        self.document_verifier = document_verifier or DocumentVerifier(self.llm_client)

    def verify_document(self, document):
        if document is None:
            document = {}

        if not isinstance(document, dict):
            return {"is_valid": False, "message": "Document payload must be a dictionary."}

        if document.get("use_fake_data"):
            document = {
                "name": document.get("name", "Jane Doe"),
                "id_number": document.get("id_number", "FAKE-12345"),
                "document_type": document.get("document_type", "id_card"),
                "use_fake_data": True,
            }

        validation_result = self.validate_data(document)
        if not validation_result["is_valid"]:
            return validation_result

        verification_result = self.document_verifier.process_document(document)
        return verification_result

    def validate_data(self, document):
        if not isinstance(document, dict):
            return {"is_valid": False, "message": "Document payload must be a dictionary."}

        name = document.get("name") or document.get("full_name")
        id_number = document.get("id_number") or document.get("id")

        if not name or not id_number:
            return {"is_valid": False, "message": "Document is missing required fields."}

        return {"is_valid": True, "message": "Document is valid."}