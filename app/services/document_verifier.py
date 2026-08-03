from app.services.llm_client import LLMClient


class DocumentVerifier:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or LLMClient()

    def process_document(self, document):
        response = self.llm_client.send_request(document)
        return response

    def check_validity(self, document):
        validity_check = self.llm_client.send_request({"action": "check_validity", "document": document})
        return validity_check.get("is_valid", False)