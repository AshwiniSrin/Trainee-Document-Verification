import unittest
from app.agents.verification_agent import VerificationAgent
from app.services.llm_client import FakeLLMClient

class TestVerificationAgent(unittest.TestCase):

    def setUp(self):
        self.agent = VerificationAgent()

    def test_verify_document_valid(self):
        document = {"name": "John Doe", "id": "123456", "documents": ["id_card", "transcript"]}
        result = self.agent.verify_document(document)
        self.assertTrue(result['is_valid'])

    def test_verify_document_invalid(self):
        document = {"name": "Jane Doe", "id": "654321", "documents": ["fake_id"]}
        result = self.agent.verify_document(document)
        self.assertFalse(result['is_valid'])

    def test_validate_data_missing_fields(self):
        data = {"name": "John Doe"}
        result = self.agent.validate_data(data)
        self.assertFalse(result['is_valid'])

    def test_validate_data_complete(self):
        data = {"name": "John Doe", "id": "123456"}
        result = self.agent.validate_data(data)
        self.assertTrue(result['is_valid'])

    def test_verify_document_with_fake_llm_client(self):
        fake_agent = VerificationAgent(llm_client=FakeLLMClient())
        document = {"name": "Jane Doe", "id": "FAKE-12345", "documents": ["id_card"], "use_fake_data": True}
        result = fake_agent.verify_document(document)
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['source'], 'demo')

    def test_verify_document_reports_missing_required_documents(self):
        document = {"name": "Rahul", "id": "101", "documents": ["aadhaar", "resume", "degree_certificate"]}
        result = self.agent.verify_document(document)
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['missing_documents'], ['pan'])
        self.assertEqual(result['status'], 'pending')

    def test_confirm_verification_marks_trainee_verified(self):
        document = {"name": "Rahul", "id": "101", "documents": ["aadhaar", "resume", "degree_certificate", "pan"]}
        self.agent.verify_document(document)
        result = self.agent.confirm_verification(101)
        self.assertTrue(result['is_verified'])
        self.assertEqual(result['status'], 'verified')

if __name__ == '__main__':
    unittest.main()