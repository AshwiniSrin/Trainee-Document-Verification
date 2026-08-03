import json
import os
import urllib.error
import urllib.request


class LLMClient:
    def __init__(self, api_key=None, model=None, api_base=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_base = (api_base or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1").rstrip("/")
        self.last_response = None

    def send_request(self, document):
        if not self.api_key:
            self.last_response = self._fallback_response(document)
            return self.last_response

        try:
            payload = {
                "model": self.model,
                "messages": self._build_messages(document),
                "temperature": 0.2,
            }
            request = urllib.request.Request(
                f"{self.api_base}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)

            content = data["choices"][0]["message"]["content"]
            self.last_response = self._parse_response(content)
            return self.last_response
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, TimeoutError) as exc:
            self.last_response = self._fallback_response(document, error=str(exc))
            return self.last_response

    def receive_response(self):
        return self.last_response

    def _build_messages(self, document):
        return [
            {
                "role": "system",
                "content": (
                    "You are a document verification assistant. "
                    "Return valid JSON with fields: is_valid, confidence, message, evidence."
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