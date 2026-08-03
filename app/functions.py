def get_trainee_record(trainee_id):
    record = {
        "trainee_id": str(trainee_id),
        "full_name": "Rahul Sharma",
        "status": "pending",
        "found": True,
    }
    return record


def check_required_documents(documents):
    required_documents = ["aadhaar", "resume", "degree_certificate", "pan"]
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

def update_verification_status(trainee_id, status="verified"):
    return {
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
}