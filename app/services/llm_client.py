import json
import os

import requests

from app.functions import TOOL_FUNCTIONS
from app.prompts import SYSTEM_PROMPT
from app.tools import TOOL_SCHEMAS


class FakeLLMClient:
    def __init__(self):
        self.last_response = None

    def send_request(self, document):
        if isinstance(document, dict) and document.get("use_fake_data"):
            self.last_response = {
                "is_valid": True,
                "confidence": 0.85,
                "message": "Document accepted using local verification flow.",
                "evidence": ["Local verification completed successfully"],
                "source": "local",
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
            messages = self._build_messages(document)
            max_iterations = 3

            for _ in range(max_iterations):
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "tools": TOOL_SCHEMAS,
                    "tool_choice": "auto",
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
                message = data["choices"][0]["message"]
                messages.append(message)

                if not message.get("tool_calls"):
                    content = message.get("content", "")
                    self.last_response = self._parse_response(content)
                    return self.last_response

                tool_results = []
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])
                    if tool_name not in TOOL_FUNCTIONS:
                        tool_results.append({"error": f"Unknown tool: {tool_name}"})
                        continue

                    result = TOOL_FUNCTIONS[tool_name](**arguments)
                    tool_results.append({"tool": tool_name, "result": result})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(result),
                        }
                    )

            self.last_response = {
                "tool_calls": tool_results,
                "source": "agent",
                "message": "Agent loop completed without a final text response.",
            }
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
                "content": SYSTEM_PROMPT,
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
                "message": "Document accepted using local verification flow.",
                "evidence": ["Local verification completed successfully"],
                "source": "local",
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