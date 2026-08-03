TOOL_SCHEMAS = [
    {
        "name": "get_trainee_record",
        "type": "function",
        "function": {
            "name": "get_trainee_record",
            "description": (
                "Retrieve the trainee profile and current verification status "
                "using the trainee ID. Use this tool whenever the user requests "
                "verification or asks about a trainee."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trainee_id": {
                        "type": "string",
                        "description": "Unique trainee identifier (e.g. TR001)."
                    }
                },
                "required": ["trainee_id"]
            }
        }
    },

    {
        "name": "check_required_documents",
        "type": "function",
        "function": {
            "name": "check_required_documents",
            "description": (
                "Check whether all mandatory trainee documents have been uploaded. "
                "Return the uploaded documents and identify any missing documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "documents": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": (
                            "List of uploaded document names such as "
                            "Aadhaar Card, Resume, Degree Certificate."
                        )
                    }
                },
                "required": ["documents"]
            }
        }
    },

    {
        "name": "verify_uploaded_documents",
        "type": "function",
        "function": {
            "name": "verify_uploaded_documents",
            "description": (
                "Validate the uploaded trainee documents by comparing them with "
                "the trainee's stored records. Return whether each document is "
                "valid, invalid, mismatched, or unreadable."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trainee_id": {
                        "type": "string",
                        "description": "Unique trainee identifier."
                    },
                    "documents": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Names of uploaded documents."
                    }
                },
                "required": [
                    "trainee_id",
                    "documents"
                ]
            }
        }
    },

    {
        "name": "update_verification_status",
        "type": "function",
        "function": {
            "name": "update_verification_status",
            "description": (
                "Update the trainee verification status after the user has "
                "explicitly confirmed the verification results. This tool "
                "modifies trainee records and should only be called after "
                "receiving user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "trainee_id": {
                        "type": "string",
                        "description": "Unique trainee identifier."
                    },
                    "status": {
                        "type": "string",
                        "description": (
                            "Verification status such as VERIFIED, "
                            "PENDING, REJECTED, or INCOMPLETE."
                        )
                    }
                },
                "required": [
                    "trainee_id",
                    "status"
                ]
            }
        }
    }
]