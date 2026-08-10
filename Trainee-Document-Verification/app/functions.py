SEMANTIC_MEMORY={
    "required_documents":{
        "value":["aadhaar","resume","degree_certificate","pan"],
        "description":"Documents required to complete trainee verification."
    },
    "verification_policy": {
        "value": "All four required documents must be submitted before verification can be confirmed.",
        "description": "Rule governing when a trainee can be marked verified.",
    },
}
def get_fact(key):
    """Retrieve a single semantic fact by its key."""
    entry = SEMANTIC_MEMORY.get(key)
    return entry["value"] if entry else None

def get_trainee_record(trainee_id):
    record = {
        "trainee_id": str(trainee_id),
        "full_name": "Rahul Sharma",
        "status": "pending",
        "found": True,
    }
    return record


def check_required_documents(documents):
    required_documents = get_fact("required_documents")
    submitted_documents = [doc.lower() for doc in documents or [] if isinstance(doc, str)]
    missing_documents = [doc for doc in required_documents if doc not in submitted_documents]
    return {
        "documents": submitted_documents,
        "required_documents": required_documents,
        "missing_documents": missing_documents,
        "complete": not missing_documents,
    }


def verify_uploaded_documents(trainee_id, documents):
    """
    Validate uploaded documents.
    This is a mock implementation.
    Replace with OCR/database validation later.
    """

    verification_results = []

    for document in documents or []:
        verification_results.append({
            "document": document,
            "status": "Valid",
            "remarks": "Document verified successfully."
        })

    return {
        "trainee_id": str(trainee_id),
        "verification_results": verification_results,
        "overall_status": "verified"
    }


def update_verification_status(trainee_id, status="verified", confirmed=False):
    if not confirmed:
        return {
            "success": False,
            "requires_confirmation": True,
            "message": (
                f"Updating trainee {trainee_id} to '{status}' requires user confirmation."
            ),
        }

    return {
        "success": True,
        "trainee_id": str(trainee_id),
        "status": status,
        "updated": True,
        "message": f"Verification status updated to {status}.",
    }


TOOL_FUNCTIONS = {
    "get_trainee_record": get_trainee_record,
    "check_required_documents": check_required_documents,
    "verify_uploaded_documents": verify_uploaded_documents,
    "update_verification_status": update_verification_status,
    "get_fact":get_fact,
}
