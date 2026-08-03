import unittest
from unittest.mock import patch

from app.agents.verification_agent import VerificationAgent
from app.functions import check_required_documents, get_trainee_record, update_verification_status
from app.prompts import SYSTEM_PROMPT
from app.services.llm_client import FakeLLMClient, LLMClient
from app.tools import TOOL_SCHEMAS

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
        self.assertEqual(result['source'], 'local')
        self.assertIn('local verification', result['message'].lower())
        self.assertNotIn('fake', result['message'].lower())

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

    def test_llm_client_uses_project_system_prompt(self):
        client = LLMClient(api_key="demo-key")
        messages = client._build_messages({"name": "Jane Doe", "id": "123456", "documents": ["id_card"]})
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], SYSTEM_PROMPT)
        self.assertIn("Trainee Document Verification Agent", messages[0]["content"])

    def test_system_prompt_describes_verification_flow(self):
        self.assertIn("1. Review the uploaded documents", SYSTEM_PROMPT)
        self.assertIn("2. Check trainee records", SYSTEM_PROMPT)
        self.assertIn("3. Ask for explicit confirmation before updating", SYSTEM_PROMPT)

    def test_tool_schemas_are_available(self):
        self.assertTrue(any(tool["name"] == "get_trainee_record" for tool in TOOL_SCHEMAS))
        self.assertTrue(any(tool["name"] == "update_verification_status" for tool in TOOL_SCHEMAS))

    def test_backend_tools_return_expected_results(self):
        required_result = check_required_documents(["aadhaar", "resume", "degree_certificate", "pan"])
        self.assertEqual(required_result["missing_documents"], [])

        trainee_result = get_trainee_record("101")
        self.assertTrue(trainee_result["found"])
        self.assertEqual(trainee_result["trainee_id"], "101")

        update_result = update_verification_status("101", status="verified")
        self.assertFalse(update_result["success"])
        self.assertTrue(update_result["requires_confirmation"])

        confirmed_result = update_verification_status("101", status="verified", confirmed=True)
        self.assertTrue(confirmed_result["success"])
        self.assertEqual(confirmed_result["status"], "verified")

    def test_update_verification_status_schema_allows_confirmation_flag(self):
        update_schema = next(tool for tool in TOOL_SCHEMAS if tool["name"] == "update_verification_status")
        properties = update_schema["function"]["parameters"]["properties"]
        self.assertIn("confirmed", properties)
        self.assertEqual(properties["confirmed"]["type"], "boolean")

    def test_run_agent_loop_requests_confirmation_before_update(self):
        pending = self.agent.run_agent_loop({"name": "Rahul", "id": "101", "documents": ["aadhaar", "resume", "degree_certificate"]})
        self.assertTrue(pending["needs_confirmation"])
        self.assertEqual(pending["status"], "pending_confirmation")

        approved = self.agent.run_agent_loop({"name": "Rahul", "id": "101", "documents": ["aadhaar", "resume", "degree_certificate"]}, confirmation=True)
        self.assertTrue(approved["is_verified"])
        self.assertEqual(approved["status"], "verified")

    def test_llm_client_retries_after_tool_call(self):
        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        first_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "check_required_documents",
                                    "arguments": '{"documents": ["aadhaar"]}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        second_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"is_valid": true, "confidence": 0.9, "message": "Verified locally", "evidence": ["checked"], "source": "llm"}',
                    }
                }
            ]
        }

        with patch("app.services.llm_client.requests.post", side_effect=[FakeResponse(first_payload), FakeResponse(second_payload)]):
            client = LLMClient(api_key="demo-key")
            result = client.send_request({"name": "Jane Doe", "id": "123456", "documents": ["aadhaar"]})

        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["message"], "Verified locally")
        self.assertEqual(result["confidence"], 0.9)

    def test_llm_client_reports_unknown_tool(self):
        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        first_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_unknown",
                                "type": "function",
                                "function": {
                                    "name": "missing_tool",
                                    "arguments": '{}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        second_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"is_valid": true, "confidence": 0.8, "message": "Handled missing tool", "evidence": ["tool fallback"], "source": "llm"}',
                    }
                }
            ]
        }

        calls = []

        def fake_post(*args, **kwargs):
            calls.append(kwargs["json"])
            return FakeResponse(first_payload if len(calls) == 1 else second_payload)

        with patch("app.services.llm_client.requests.post", side_effect=fake_post):
            client = LLMClient(api_key="demo-key")
            result = client.send_request({"name": "Jane Doe", "id": "123456", "documents": ["aadhaar"]})

        self.assertEqual(result["message"], "Handled missing tool")
        self.assertEqual(len(calls), 2)
        self.assertIn("tool", calls[1]["messages"][-1]["role"])
        self.assertIn("Unknown tool 'missing_tool'", calls[1]["messages"][-1]["content"])

    def test_llm_client_handles_tool_exception(self):
        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        first_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_error",
                                "type": "function",
                                "function": {
                                    "name": "broken_tool",
                                    "arguments": '{}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        second_payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"is_valid": true, "confidence": 0.8, "message": "Recovered from tool error", "evidence": ["tool fallback"], "source": "llm"}',
                    }
                }
            ]
        }

        calls = []

        def fake_post(*args, **kwargs):
            calls.append(kwargs["json"])
            return FakeResponse(first_payload if len(calls) == 1 else second_payload)

        with patch("app.services.llm_client.TOOL_FUNCTIONS", {"broken_tool": lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))}):
            with patch("app.services.llm_client.requests.post", side_effect=fake_post):
                client = LLMClient(api_key="demo-key")
                result = client.send_request({"name": "Jane Doe", "id": "123456", "documents": ["aadhaar"]})

        self.assertEqual(result["message"], "Recovered from tool error")
        self.assertEqual(len(calls), 2)
        self.assertIn("tool", calls[1]["messages"][-1]["role"])
        self.assertIn("boom", calls[1]["messages"][-1]["content"])

if __name__ == '__main__':
    unittest.main()