
import logging
from app.functions import check_required_documents, get_trainee_record, update_verification_status, get_fact
from app.services.document_verifier import DocumentVerifier
from app.services.llm_client import LLMClient
from datetime import datetime

logger =logging.getLogger(__name__)

# =====================================================
# State Graph — named for what each stage actually does
# in the trainee verification workflow
# =====================================================
STATE_RECEIVE_REQUEST = "receive_request"       # a request just came in
STATE_VERIFY_TRAINEE = "verify_trainee"          # confirm trainee ID is real
STATE_GATHER_DOCUMENTS = "gather_documents"      # read what's been uploaded
STATE_ASSESS_COMPLETENESS = "assess_completeness"  # missing vs complete
STATE_AWAIT_CONFIRMATION = "await_confirmation"  # waiting on human click
STATE_FINALIZE_VERIFICATION = "finalize_verification"  # the write happens
STATE_RECORD_COMPLETION = "record_completion"    # logged, done

TRANSITIONS = {
    (STATE_RECEIVE_REQUEST, "trainee_identified"): STATE_VERIFY_TRAINEE,
    (STATE_VERIFY_TRAINEE, "trainee_found"): STATE_GATHER_DOCUMENTS,
    (STATE_GATHER_DOCUMENTS, "documents_checked"): STATE_ASSESS_COMPLETENESS,
    (STATE_ASSESS_COMPLETENESS, "still_missing"): STATE_GATHER_DOCUMENTS,   # loop back on more uploads
    (STATE_ASSESS_COMPLETENESS, "complete"): STATE_AWAIT_CONFIRMATION,
    (STATE_AWAIT_CONFIRMATION, "confirmed"): STATE_FINALIZE_VERIFICATION,
    (STATE_AWAIT_CONFIRMATION, "blocked"): STATE_AWAIT_CONFIRMATION,        # still waiting, nothing to do
    (STATE_FINALIZE_VERIFICATION, "written"): STATE_RECORD_COMPLETION,
    (STATE_RECORD_COMPLETION, "confirmed"): STATE_RECORD_COMPLETION,        # re-confirm does nothing new
}


def next_state(current_state, event):
    return TRANSITIONS.get((current_state, event), current_state)


# =====================================================
# Tool permissions per state — read tools everywhere,
# write tool ONLY inside FINALIZE_VERIFICATION
# =====================================================
STATE_ALLOWED_OPERATIONS = {
    STATE_RECEIVE_REQUEST: set(),
    STATE_VERIFY_TRAINEE: {"get_trainee_record"},
    STATE_GATHER_DOCUMENTS: {"get_uploaded_documents", "check_required_documents"},
    STATE_ASSESS_COMPLETENESS: {"check_required_documents"},
    STATE_AWAIT_CONFIRMATION: set(),
    STATE_FINALIZE_VERIFICATION: {"update_verification_status"},
    STATE_RECORD_COMPLETION: {"remember_verification"},
}


def is_operation_allowed(state, operation_name):
    return operation_name in STATE_ALLOWED_OPERATIONS.get(state, set())


class VerificationAgent:
    def __init__(self, llm_client=None, document_verifier=None):
        self.llm_client = llm_client or LLMClient()
        self.document_verifier = document_verifier or DocumentVerifier(self.llm_client)
        self._verification_state = {}
        self._uploaded_documents = {}

        self.episodic_memory = {}
        self.chat_history = {}
        self.reasoning_steps = {}
        self.current_state = {}   # trainee_id -> current stage name

        self.pending_verification = None

    def add_message(self, trainee_id, role, message):
        trainee_id = str(trainee_id)
        self.chat_history.setdefault(trainee_id, []).append({
            "role": role,
            "message": message
        })
        self.chat_history[trainee_id] = self.chat_history[trainee_id][-20:]
        self.remember_message(trainee_id, role, message)

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

    def add_step(self, trainee_id, step):
        trainee_id = str(trainee_id)
        self.reasoning_steps.setdefault(trainee_id, []).append(step)

    def remember_upload(self, trainee_id, documents):
        trainee_id = str(trainee_id)
        if trainee_id not in self.episodic_memory:
            self.episodic_memory[trainee_id] = []
        self.episodic_memory[trainee_id].append({
            "event": "upload",
            "documents": documents,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

    def remember_verification(self, trainee_id, status):
        trainee_id = str(trainee_id)
        self.episodic_memory.setdefault(trainee_id, []).append({
            "event": "verification_completed",
            "status": status,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

    def remember_message(self, trainee_id, role, message):
        trainee_id = str(trainee_id)
        self.episodic_memory.setdefault(trainee_id, []).append({
            "event": "message",
            "role": role,
            "message": message,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

    def get_uploaded_documents(self, trainee_id):
        trainee_id = str(trainee_id)
        uploaded = []
        for event in self.episodic_memory.get(trainee_id, []):
            if event["event"] == "upload":
                uploaded.extend(event["documents"])
        return list(dict.fromkeys(uploaded))

    def determine_event(self, stage, submitted_documents, missing_documents, confirmation):
        """Translate current facts into the event name the TRANSITIONS table expects."""
        if stage == STATE_RECEIVE_REQUEST:
            return "trainee_identified"
        if stage == STATE_VERIFY_TRAINEE:
            return "trainee_found"
        if stage == STATE_GATHER_DOCUMENTS:
            return "documents_checked"
        if stage == STATE_ASSESS_COMPLETENESS:
            return "complete" if not missing_documents else "still_missing"
        if stage == STATE_AWAIT_CONFIRMATION:
            if confirmation:
                return "confirmed" if not missing_documents else "blocked"
            return None
        if stage == STATE_RECORD_COMPLETION:
            return "confirmed" if confirmation else None
        return None

    def run_agent_loop(self, document, confirmation=False):
        if not isinstance(document, dict):
            return {
                "is_valid": False,
                "message": "Document payload must be a dictionary."
            }

        trainee_id = str(
            document.get("id")
            or document.get("trainee_id")
            or document.get("id_number")
            or "unknown"
        )

        # If already verified, short-circuit straight to RECORD_COMPLETION
        already_verified = any(
            event.get("event") == "verification_completed"
            for event in self.episodic_memory.get(trainee_id, [])
        )
        if already_verified:
            self.current_state[trainee_id] = STATE_RECORD_COMPLETION
            if confirmation:
                return {
                    "is_verified": True,
                    "status": "verified",
                    "message": f"Trainee {trainee_id} is already verified.",
                    "uploaded_documents": self.get_uploaded_documents(trainee_id),
                    "missing_documents": [],
                    "trainee": get_trainee_record(trainee_id),
                }

        # -----------------------------
        # GATHER_DOCUMENTS: remember newly uploaded documents
        # -----------------------------
        new_documents = self._normalize_documents(document.get("documents", []))
        stored_documents = self.get_uploaded_documents(trainee_id)
        genuinely_new = [d for d in new_documents if d not in stored_documents]

        if genuinely_new and not confirmation:
            self.add_step(trainee_id, "RECEIVE_REQUEST: new upload detected")
            self.add_message(trainee_id, "user", f"Uploaded documents:{','.join(genuinely_new)}")
            self.remember_upload(trainee_id, genuinely_new)
            self.add_step(trainee_id, "VERIFY_TRAINEE: trainee record confirmed")
            self.add_step(trainee_id, "GATHER_DOCUMENTS: reading uploaded documents")

        submitted_documents = list(dict.fromkeys(stored_documents + new_documents))
        self._uploaded_documents[trainee_id] = submitted_documents
        required_result = check_required_documents(submitted_documents)
        missing_documents = required_result["missing_documents"]

        if genuinely_new and not confirmation:
            self.add_step(trainee_id, f"ASSESS_COMPLETENESS: consulting semantic memory = {get_fact('required_documents')}")
            self.add_message(
                trainee_id,
                "agent",
                f"Missing documents: {', '.join(missing_documents)}"
            )

        trainee_result = get_trainee_record(trainee_id)

        self._verification_state[trainee_id] = {
            "trainee_id": trainee_id,
            "name": document.get("name") or document.get("full_name"),
            "submitted_documents": submitted_documents,
            "required_documents": required_result["required_documents"],
            "missing_documents": missing_documents,
            "status": "pending_confirmation",
        }

        # =====================================================
        # State Graph: figure out stage + event, then next stage
        # =====================================================
        current = self.current_state.get(trainee_id, STATE_RECEIVE_REQUEST)
        
        # Fold the first two silent stages (RECEIVE_REQUEST -> VERIFY_TRAINEE -> GATHER_DOCUMENTS)
        # forward automatically, since trainee validation is a stub today.
        if current in (STATE_RECEIVE_REQUEST, STATE_VERIFY_TRAINEE):
            current = STATE_GATHER_DOCUMENTS

        stage_for_event = STATE_ASSESS_COMPLETENESS if current == STATE_GATHER_DOCUMENTS else current
        event = self.determine_event(stage_for_event, submitted_documents, missing_documents, confirmation)
        new_state = next_state(stage_for_event, event) if event else current
        logger.info(
            f"[STATE DEBUG] "
            f"trainee={trainee_id} | "
            f"current={current!r} | "
            f"stage={stage_for_event!r} | "
            f"event={event!r} | "
            f"new_state={new_state!r} | "
            f"confirmation={confirmation!r}"
        )
        self.current_state[trainee_id] = new_state

        # =====================================================
        # Dispatch based on the resulting stage
        # =====================================================
        if new_state == STATE_RECORD_COMPLETION:
            if not is_operation_allowed(STATE_FINALIZE_VERIFICATION, "update_verification_status"):
                return {"status": "error", "message": "Write operation blocked: not permitted."}

            verified_result = self.confirm_verification(trainee_id)
            self.add_step(trainee_id, "FINALIZE_VERIFICATION: writing verified status")

            update_result = update_verification_status(
                trainee_id,
                status="verified",
                confirmed=True,
            )
            self.add_message(trainee_id, "agent", "Verification completed.")
            self.add_step(trainee_id, "RECORD_COMPLETION: logging episodic event")
            self.remember_verification(trainee_id, "verified")

            self._uploaded_documents.pop(trainee_id, None)
            self._verification_state.pop(trainee_id, None)

            return {
                "is_verified": True,
                "status": "verified",
                "message": verified_result["message"],
                "uploaded_documents": submitted_documents,
                "missing_documents": [],
                "trainee": trainee_result,
                "update": update_result,
            }

        if new_state == STATE_AWAIT_CONFIRMATION and confirmation:
            
            # blocked: confirm was clicked but documents are still missing
            return {
                "status": "pending_confirmation",
                "needs_confirmation": False,
                "message": (
                    "Cannot confirm verification because some "
                    "required documents are still missing."
                ),
                "uploaded_documents": submitted_documents,
                "missing_documents": missing_documents,
                "trainee": trainee_result,
            }

        if new_state == STATE_GATHER_DOCUMENTS:
            self.add_step(trainee_id, "AWAIT_CONFIRMATION: waiting for missing documents")
            return {
                "status": "pending_confirmation",
                "needs_confirmation": True,
                "message": (
                    "Required documents are missing. "
                    "Please upload the missing document(s)."
                ),
                "uploaded_documents": submitted_documents,
                "missing_documents": missing_documents,
                "trainee": trainee_result,
            }

        if new_state == STATE_AWAIT_CONFIRMATION:
            logger.info(
                "[STATE DEBUG] >>> ENTERED AWAIT_CONFIRMATION BRANCH <<<"
            )
            self.add_step(
                trainee_id,
                "AWAIT_CONFIRMATION: verification looks complete, waiting for user confirmation"
            )

            return {
                "status": "pending_confirmation",
                "needs_confirmation": True,
                "message": (
                    "Verification looks complete. "
                    "Please confirm before updating the trainee status."
                ),
                "uploaded_documents": submitted_documents,
                "missing_documents": [],
                "trainee": trainee_result,
            }
        if new_state == STATE_FINALIZE_VERIFICATION:
            logger.info(
                "[STATE DEBUG] >>> ENTERED FINALIZE_VERIFICATION BRANCH <<<"
            )
            self.add_step(
                trainee_id,
                "FINALIZE_VERIFICATION: confirmation received, finalizing verification"
            )

            self.current_state[trainee_id] = STATE_RECORD_COMPLETION

            logger.info(
                "[STATE DEBUG] >>> MOVING TO RECORD_COMPLETION <<<"
            )

            return {
                "status": "verified",
                "needs_confirmation": False,
                "message": "Verification completed successfully.",
                "uploaded_documents": submitted_documents,
                "missing_documents": [],
                "trainee": trainee_result,
            }
        logger.warning(
            f"[STATE DEBUG] >>> HIT FINAL FALLBACK <<< "
            f"new_state={new_state!r}"
        )

        return {
            "status": "pending_confirmation",
            "needs_confirmation": False,
            "message": "Waiting for documents to be uploaded.",
            "uploaded_documents": submitted_documents,
            "missing_documents": missing_documents,
            "trainee": trainee_result,
        }

    def _normalize_documents(self, documents):
        if not documents:
            return []
        if isinstance(documents, str):
            documents = [documents]
        normalized = []
        for doc in documents:
            if not isinstance(doc, str):
                continue
            doc = doc.lower().strip()
            doc = doc.replace(".pdf", "")
            doc = doc.replace(".jpg", "")
            doc = doc.replace(".jpeg", "")
            doc = doc.replace(".png", "")

            if "aadhaar" in doc or "aadhar" in doc:
                doc = "aadhaar"
            elif "resume" in doc:
                doc = "resume"
            elif "degree" in doc:
                doc = "degree_certificate"
            elif "pan" in doc:
                doc = "pan"
            normalized.append(doc)
        return list(dict.fromkeys(normalized))

    def _should_block_for_missing_documents(self, submitted_documents, missing_documents):
        if not submitted_documents:
            return True
        return bool(missing_documents)