import unittest
from app.agents.verification_agent import VerificationAgent

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

if __name__ == '__main__':
    unittest.main()