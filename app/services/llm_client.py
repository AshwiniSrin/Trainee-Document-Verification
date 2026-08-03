import json
import os
import urllib.error
import urllib.request

import requests


class FakeLLMClient:
    def __init__(self):
        self.last_response = None

    def send_request(self, document):
        if isinstance(document, dict) and document.get("use_fake_data"):
            self.last_response = {
                "is_valid": True,
                "confidence": 0.85,
                "message": "Fake document sample accepted using the configured demo LLM.",
                "evidence": ["Sample payload used for demo verification"],
                "source": "demo",
            }
        else:
            self.last_response = {
                "is_valid": True,
                "confidence": 0.6,
                "message": "Fake LLM accepted the document payload.",
                "evidence": ["Local fake response"],
                "source": "demo",
            }
        return self.last_response

    def receive_response(self):
        return self.last_response


class LLMClient:
    def __init__(self, api_key=None, model=None, api_base=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_base = (api_base or os.getenv("OPENAI_API_BASE") or os.getenv("API_URL") or "https://api.openai.com/v1").rstrip("/")
        self.last_response = None

    def send_request(self, document):
        if isinstance(document, dict) and document.get("use_fake_data"):
            self.last_response = self._fallback_response(document)
            return self.last_response

        if not self.api_key:
            self.last_response = self._fallback_response(document)
            return self.last_response

        try:
            payload = {
                "model": self.model,
                "messages": self._build_messages(document),
                "temperature": 0.2,
            }
            response = requests.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            self.last_response = self._parse_response(content)
            return self.last_response
        except (requests.RequestException, KeyError, ValueError, TimeoutError) as exc:
            self.last_response = self._fallback_response(document, error=str(exc))
            return self.last_response

    def receive_response(self):
        return self.last_response

    def _build_messages(self, document):
        return [
            {
                "role": "system",
                "content": (
                    "You are a document verification assistant for trainee document validation. "
                    "Review the supplied document metadata carefully and decide whether the record looks plausible and complete. "
                    "Return valid JSON only with these exact fields: is_valid, confidence, message, evidence. "
                    "Use booleans for is_valid, numbers between 0 and 1 for confidence, and a short explanation in message. "
                    "Put supporting details in evidence as an array of short strings. "
                    "Treat missing required fields as invalid. "
                    "Treat obvious fake ID values, placeholder IDs, or suspicious patterns as invalid. "
                    "Check whether the document type is supported and consistent with the provided metadata. "
                    "Scoring style: use high confidence only for clearly strong matches, moderate confidence for partially complete records, and low confidence for ambiguous or weak evidence. "
                    "If the details look missing, fake, inconsistent, or suspicious, set is_valid to false. "
                    "If the data appears complete and credible, set is_valid to true."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Verify this document metadata and respond with JSON only. "
                    f"Document: {json.dumps(document, indent=2)}"
                ),
            },
        ]

    def _parse_response(self, content):
        try:
            parsed = json.loads(content)
            return {
                "is_valid": bool(parsed.get("is_valid", False)),
                "confidence": parsed.get("confidence", 0.0),
                "message": parsed.get("message", "Document reviewed by LLM."),
                "evidence": parsed.get("evidence", []),
                "source": "llm",
            }
        except (TypeError, ValueError):
            return {
                "is_valid": False,
                "confidence": 0.0,
                "message": content.strip() or "The LLM returned an unreadable response.",
                "evidence": [],
                "source": "llm",
            }

    def _fallback_response(self, document, error=None):
        name = document.get("name") or document.get("full_name")
        id_number = document.get("id_number") or document.get("id")

        if isinstance(document, dict) and document.get("use_fake_data"):
            return {
                "is_valid": True,
                "confidence": 0.85,
                "message": "Fake document sample accepted using the configured OpenAI-compatible setup.",
                "evidence": ["Sample payload used for demo verification"],
                "source": "demo",
            }

        if name and id_number:
            return {
                "is_valid": True,
                "confidence": 0.6,
                "message": "Document passed local validation; OpenAI call was not available.",
                "evidence": ["Name and identity fields are present"],
                "source": "fallback",
            }

        return {
            "is_valid": False,
            "confidence": 0.0,
            "message": "Document is missing required fields.",
            "evidence": [error] if error else [],
            "source": "fallback",
        }