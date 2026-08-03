from app.services.document_verifier import DocumentVerifier
from app.services.llm_client import LLMClient


class VerificationAgent:
    def __init__(self, llm_client=None, document_verifier=None):
        self.llm_client = llm_client or LLMClient()
        self.document_verifier = document_verifier or DocumentVerifier(self.llm_client)
        self._verification_state = {}

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

        trainee_id = document.get("id") or document.get("trainee_id") or document.get("id_number")
        required_documents = ["aadhaar", "resume", "degree_certificate", "pan"]
        submitted_documents = self._normalize_documents(document.get("documents", []))
        missing_documents = [doc for doc in required_documents if doc not in submitted_documents]

        self._verification_state[str(trainee_id)] = {
            "trainee_id": trainee_id,
            "name": document.get("name") or document.get("full_name"),
            "submitted_documents": submitted_documents,
            "missing_documents": missing_documents,
            "status": "pending" if missing_documents else "ready",
        }

        if missing_documents:
            return {
                "is_valid": False,
                "confidence": 0.55,
                "message": "Required documents are missing. Please upload the missing files.",
                "evidence": [f"Missing: {', '.join(missing_documents)}"],
                "missing_documents": missing_documents,
                "status": "pending",
                "source": "verification_agent",
            }

        verification_result = self.document_verifier.process_document(document)
        verification_result.update({
            "missing_documents": [],
            "status": "ready",
            "source": verification_result.get("source", "verification_agent"),
        })
        return verification_result

    def confirm_verification(self, trainee_id):
        state = self._verification_state.get(str(trainee_id))
        if not state:
            return {"is_verified": False, "status": "unknown", "message": "No verification state found for this trainee."}

        state["status"] = "verified"
        return {
            "is_verified": True,
            "status": "verified",
            "message": f"Verification completed successfully for trainee {trainee_id}.",
            "trainee_id": trainee_id,
        }

    def validate_data(self, document):
        if not isinstance(document, dict):
            return {"is_valid": False, "message": "Document payload must be a dictionary."}

        name = document.get("name") or document.get("full_name")
        id_number = document.get("id_number") or document.get("id")

        if not name or not id_number:
            return {"is_valid": False, "message": "Document is missing required fields."}

        return {"is_valid": True, "message": "Document is valid."}

    def _normalize_documents(self, documents):
        if not documents:
            return []
        if isinstance(documents, str):
            documents = [documents]
        normalized = []
        for document in documents:
            if isinstance(document, str):
                normalized.append(document.strip().lower())
        return normalized