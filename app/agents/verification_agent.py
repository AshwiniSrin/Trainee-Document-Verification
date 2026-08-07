from app.functions import check_required_documents, get_trainee_record, update_verification_status
from app.services.document_verifier import DocumentVerifier
from app.services.llm_client import LLMClient


class VerificationAgent:
    def __init__(self, llm_client=None, document_verifier=None):
        self.llm_client = llm_client or LLMClient()
        self.document_verifier = document_verifier or DocumentVerifier(self.llm_client)
        self._verification_state = {}
        self.pending_verification = None

    def verify_document(self, document):
        """
        Verify trainee documents using the DocumentVerifier and the required-document checks.
        """
        if document is None:
            document = {}

        if not isinstance(document, dict):
            return {"is_valid": False, "message": "Document payload must be a dictionary."}

        if document.get("use_fake_data"):
            document = {
                "name": document.get("name", "Jane Doe"),
                "id_number": document.get("id_number", "FAKE-12345"),
                "document_type": document.get("document_type", "id_card"),
                "documents": document.get("documents", ["id_card"]),
                "use_fake_data": True,
            }

        validation_result = self.validate_data(document)
        if not validation_result["is_valid"]:
            return validation_result

        result = self.document_verifier.process_document(document)
        if not result.get("is_valid", False):
            return result

        submitted_documents = self._normalize_documents(document.get("documents", []))
        required = check_required_documents(submitted_documents)
        trainee_id = document.get("id") or document.get("trainee_id") or document.get("id_number")
        required_document_types = {"aadhaar", "resume", "degree_certificate", "pan"}
        has_required_document = any(doc in required_document_types for doc in submitted_documents)

        self._verification_state[str(trainee_id)] = {
            "trainee_id": trainee_id,
            "name": document.get("name") or document.get("full_name"),
            "submitted_documents": submitted_documents,
            "missing_documents": required["missing_documents"],
            "status": "pending_confirmation" if has_required_document and required["missing_documents"] else "ready_for_confirmation",
        }

        if has_required_document and required["missing_documents"]:
            self.pending_verification = {
                "trainee_id": trainee_id,
                "status": "pending_confirmation",
            }
            return {
                "is_valid": False,
                "status": "pending",
                "missing_documents": required["missing_documents"],
                "needs_confirmation": True,
                "message": "Required documents are missing.",
            }

        return {
            "is_valid": True,
            "status": "ready_for_confirmation",
            "needs_confirmation": True,
            "message": result.get("message", "Document accepted using local verification flow."),
            "source": result.get("source", "verification_agent"),
            "confidence": result.get("confidence", 0.0),
            "evidence": result.get("evidence", []),
        }

    def validate_data(self, document):
        if not isinstance(document, dict):
            return {"is_valid": False, "message": "Document payload must be a dictionary."}

        name = document.get("name") or document.get("full_name")
        id_number = document.get("id_number") or document.get("id")

        if not name or not id_number:
            return {"is_valid": False, "message": "Document is missing required fields."}

        return {"is_valid": True, "message": "Document is valid."}

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

    def run_agent_loop(self, document, confirmation=False):
        if not isinstance(document, dict):
            return {"is_valid": False, "message": "Document payload must be a dictionary."}

        trainee_id = str(document.get("id") or document.get("trainee_id") or document.get("id_number") or "unknown")
        submitted_documents = self._normalize_documents(document.get("documents", []))
        required_result = check_required_documents(submitted_documents)
        trainee_result = get_trainee_record(trainee_id)

        self._verification_state[str(trainee_id)] = {
            "trainee_id": trainee_id,
            "name": document.get("name") or document.get("full_name"),
            "submitted_documents": submitted_documents,
            "required_documents": required_result["required_documents"],
            "missing_documents": required_result["missing_documents"],
            "status": "pending_confirmation",
        }

        if confirmation:
            stored_state = self._verification_state.get(str(trainee_id), {})
            if stored_state.get("missing_documents"):
                return {
                    "needs_confirmation": False,
                    "status": "pending_confirmation",
                    "message": "Cannot confirm verification while required documents are missing.",
                    "missing_documents": stored_state.get("missing_documents", []),
                    "trainee": trainee_result,
                }

            verified_result = self.confirm_verification(trainee_id)
            return {
                "is_verified": verified_result.get("is_verified", False),
                "status": verified_result.get("status", "verified"),
                "message": verified_result.get("message"),
                "trainee": trainee_result,
                "update": update_verification_status(trainee_id, status="verified", confirmed=True),
            }

        if not confirmation and required_result["complete"]:
            return {
                "needs_confirmation": True,
                "status": "pending_confirmation",
                "message": "Verification looks complete. Please confirm before updating the trainee status.",
                "missing_documents": required_result["missing_documents"],
                "trainee": trainee_result,
            }

        if not confirmation and required_result["missing_documents"]:
            return {
                "needs_confirmation": True,
                "status": "pending_confirmation",
                "message": "Required documents are missing. Please upload the missing document(s) and resubmit once complete.",
                "missing_documents": required_result["missing_documents"],
                "trainee": trainee_result,
            }

        update_result = update_verification_status(trainee_id, status="verified", confirmed=confirmation)
        self._verification_state[str(trainee_id)]["status"] = "verified"
        return {
            "is_verified": True,
            "status": "verified",
            "message": "Verification completed successfully after confirmation.",
            "trainee": trainee_result,
            "update": update_result,
        }

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

    def _should_block_for_missing_documents(self, submitted_documents, missing_documents):
        if not submitted_documents:
            return True
        return bool(missing_documents)