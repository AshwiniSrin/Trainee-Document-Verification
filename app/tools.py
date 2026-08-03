TOOL_SCHEMAS = [
    {
        "name": "get_trainee_record",
        "description": "Retrieve trainee profile and current verification state from the local records store.",
        "parameters": {
            "type": "object",
            "properties": {
                "trainee_id": {"type": "string", "description": "The trainee identifier."}
            },
            "required": ["trainee_id"],
        },
    },
    {
        "name": "check_required_documents",
        "description": "Check whether the supplied document list covers the required verification documents.",
        "parameters": {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The submitted document names.",
                }
            },
            "required": ["documents"],
        },
    },
    {
        "name": "update_verification_status",
        "description": "Update the trainee verification status after explicit user approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "trainee_id": {"type": "string", "description": "The trainee identifier."},
                "status": {"type": "string", "description": "The new verification status such as verified or pending."},
            },
            "required": ["trainee_id", "status"],
        },
    },
]
