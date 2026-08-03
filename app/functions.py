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


def update_verification_status(trainee_id, status="verified"):
    return {
        "trainee_id": str(trainee_id),
        "status": status,
        "updated": True,
        "message": f"Verification status updated to {status}.",
    }
