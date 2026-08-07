from app.functions import check_required_documents, get_trainee_record, update_verification_status
from app.services.document_verifier import DocumentVerifier
from app.services.llm_client import LLMClient
from datetime import datetime

class VerificationAgent:
    def __init__(self, llm_client=None, document_verifier=None):
        self.llm_client = llm_client or LLMClient()
        self.document_verifier = document_verifier or DocumentVerifier(self.llm_client)
        self._verification_state = {}
        self.semantic_memory={}
        self.episodic_memory={}
        self._uploaded_documents={}
        self.chat_history={}
        self.reasoning_steps={}
        self.pending_verification = None

    def add_message(self,trainee_id,role,message):
        trainee_id=str(trainee_id)
        self.chat_history.setdefault(trainee_id,[]).append({
            "role":role,
            "message":message
        })  
        self.chat_history[trainee_id]=self.chat_history[trainee_id][-20:]


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

        self.reasoning_steps.setdefault(
            trainee_id,
            []
        ).append(step)
    def remember_upload(self,trainee_id,documents):
        trainee_id=str(trainee_id)
        if trainee_id not in self.episodic_memory:
            self.episodic_memory[trainee_id]=[]
        self.episodic_memory[trainee_id].append({
            "event":"upload",
            "documents":documents,
            "timestamp":datetime.now().strftime("%H:%M:%S") 
        })    

    def get_uploaded_documents(self,trainee_id):
        trainee_id=str(trainee_id)
        uploaded = []

        for event in self.episodic_memory.get(trainee_id, []):
            uploaded.extend(event["documents"])

        return list(dict.fromkeys(uploaded))   

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
        self.add_message(
            trainee_id,
            "user",
            f"Uploaded documents:{','.join(new_documents)}
        )
        self.add_message(
           trainee_id,
           "agent",
           f"Missing documents: {', '.join(required_result['missing_documents'])}"
        )
        self.add_message(
           trainee_id,
           "agent",
           "Verification completed."
        )

    # -----------------------------
    # Remember previously uploaded documents
    # -----------------------------
        new_documents = self._normalize_documents(
            document.get("documents", [])
        )
        self.remember_upload(
            trainee_id,
            new_documents
        )

        stored_documents = self.get_uploaded_documents(
            trainee_id
        )

        submitted_documents = list(
            dict.fromkeys(
                stored_documents + new_documents
            )
        )

        self._uploaded_documents[trainee_id] = submitted_documents
        required_result = check_required_documents(
            submitted_documents
            )

        trainee_result = get_trainee_record(trainee_id)
        self.semantic_memory[trainee_id] = {
            "name": trainee_result.get("full_name"),
            "required_documents": required_result["required_documents"],
            "status": trainee_result.get("status")
        }

    # Save current verification state
        self._verification_state[trainee_id] = {
            "trainee_id": trainee_id,
            "name": document.get("name")
            or document.get("full_name"),
            "submitted_documents": submitted_documents,
            "required_documents": required_result["required_documents"],
            "missing_documents": required_result["missing_documents"],
            "status": "pending_confirmation",
        }

    # =====================================================
    # STEP 1 : User clicked Confirm Verification
    # =====================================================
        if confirmation:
            state = self._verification_state.get(trainee_id)
            if not state:
                return {
                    "status": "error",
                    "message": "No verification session found."
                }

            if state["missing_documents"]:
                return {
                    "status": "pending_confirmation",
                    "needs_confirmation": False,
                    "message": (
                    "Cannot confirm verification because some "
                    "required documents are still missing."
                ),
                "uploaded_documents": state["submitted_documents"],
                "missing_documents": state["missing_documents"],
                "trainee": trainee_result,
            }

            verified_result = self.confirm_verification(trainee_id)
            if trainee_id in self.semantic_memory:
                self.semantic_memory[trainee_id]["status"]="verified"
                
            update_result = update_verification_status(
                trainee_id,
                status="verified",
                confirmed=True,
                )

        # Clear memory after successful verification
            self._uploaded_documents.pop(trainee_id,None)
            self._verification_state.pop(trainee_id,None)

            return {
                "is_verified": True,
                "status": "verified",
                "message": verified_result["message"],
                "uploaded_documents": submitted_documents,
                "missing_documents": [],
                "trainee": trainee_result,
                "update": update_result,
            }

    # =====================================================
    # STEP 2 : Missing documents
    # =====================================================
        if required_result["missing_documents"]:
            return {
                "status": "pending_confirmation",
                "needs_confirmation": True,
                "message": (
                    "Required documents are missing. "
                    "Please upload the missing document(s)."
                ),
                "uploaded_documents": submitted_documents,
                "missing_documents": required_result["missing_documents"],
                "trainee": trainee_result,
            }

    # =====================================================
    # STEP 3 : All documents uploaded
    # =====================================================
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

    def _normalize_documents(self, documents):
        if not documents:
            return []
        if isinstance(documents, str):
            documents = [documents]
        normalized = []
        for doc in documents:
            if not isinstance(doc,str):
                continue
            doc=doc.lower().strip()
            doc=doc.replace(".pdf","")
            doc=doc.replace(".jpg","")
            doc=doc.replace(".jpeg","")
            doc=doc.replace(".png","")

            if "aadhaar" in doc or "aadhar" in doc:
                doc="aadhaar"
            elif "resume" in doc:
                doc="resume"
            elif "degree" in doc:
                doc="degree_certificate"
            elif "pan" in doc:
                doc ="pan"
            normalized.append(doc)
        return list(dict.fromkeys(normalized))               
                

    def _should_block_for_missing_documents(self, submitted_documents, missing_documents):
        if not submitted_documents:
            return True
        return bool(missing_documents)