"""Meeting summarization: abstract interface + Ollama + API providers."""
from __future__ import annotations
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import httpx
from loguru import logger

@dataclass
class ActionItem:
    description: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None

@dataclass
class MeetingSummary:
    executive_summary: str
    key_points: list[str] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    duration_minutes: float = 0.0
    participants: list[str] = field(default_factory=list)

class Summarizer(ABC):
    @abstractmethod
    async def summarize(self, transcript: str, speakers: list[str]) -> MeetingSummary:
        """Summarize a transcript. transcript is pre-formatted with speaker labels."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this summarizer's backend is reachable."""
        ...


class OllamaSummarizer(Summarizer):
    """Local summarization via Ollama (default, privacy-preserving)."""

    SYSTEM_PROMPT = """You are a professional meeting notes assistant.
Analyze the transcript and extract structured information.
Always respond with valid JSON matching the specified schema exactly."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.is_success
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def _build_prompt(self, transcript: str, speakers: list[str]) -> str:
        participants_str = ", ".join(speakers) if speakers else "Unknown participants"
        return f"""Analyze this meeting transcript and produce a structured JSON summary.

Participants: {participants_str}

Transcript:
{transcript}

Respond ONLY with a JSON object matching this exact schema (no markdown, no explanation):
{{
  "executive_summary": "3-4 sentence overview of the meeting",
  "key_points": ["point 1", "point 2", "..."],
  "action_items": [
    {{"description": "task description", "assignee": "person or null", "deadline": "date/time or null"}}
  ],
  "decisions": ["decision 1", "decision 2"],
  "next_steps": ["step 1", "step 2"]
}}"""

    def _parse_response(self, raw: str) -> MeetingSummary:
        # Extract JSON from response (may have surrounding text)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            logger.warning("Could not extract JSON from summarization response")
            return MeetingSummary(executive_summary=raw[:500])

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in summarization: {e}")
            return MeetingSummary(executive_summary=raw[:500])

        action_items = [
            ActionItem(
                description=a.get("description", ""),
                assignee=a.get("assignee"),
                deadline=a.get("deadline"),
            )
            for a in data.get("action_items", [])
            if isinstance(a, dict)
        ]

        return MeetingSummary(
            executive_summary=data.get("executive_summary", ""),
            key_points=data.get("key_points", []),
            action_items=action_items,
            decisions=data.get("decisions", []),
            next_steps=data.get("next_steps", []),
        )

    async def summarize(self, transcript: str, speakers: list[str]) -> MeetingSummary:
        prompt = self._build_prompt(transcript, speakers)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                )
                r.raise_for_status()
                raw = r.json().get("response", "")
                return self._parse_response(raw)
        except httpx.ConnectError:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Start Ollama with: ollama serve"
            )


class APISummarizer(Summarizer):
    """Summarization via external APIs: Anthropic, OpenAI, Groq."""

    SUPPORTED_PROVIDERS = ("anthropic", "openai", "groq")

    def __init__(self, provider: str, api_key: str, model: str = ""):
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}. Choose from {self.SUPPORTED_PROVIDERS}")
        self.provider = provider
        self.api_key = api_key
        self.model = model or self._default_model(provider)

    @staticmethod
    def _default_model(provider: str) -> str:
        return {
            "anthropic": "claude-haiku-4-5-20251001",
            "openai": "gpt-4o-mini",
            "groq": "llama-3.1-8b-instant",
        }[provider]

    async def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_messages(self, transcript: str, speakers: list[str]) -> list[dict]:
        participants_str = ", ".join(speakers) if speakers else "Unknown"
        user_content = f"""Participants: {participants_str}

Transcript:
{transcript}

Respond ONLY with JSON matching this schema:
{{
  "executive_summary": "...",
  "key_points": ["..."],
  "action_items": [{{"description": "...", "assignee": null, "deadline": null}}],
  "decisions": ["..."],
  "next_steps": ["..."]
}}"""
        return [{"role": "user", "content": user_content}]

    async def summarize(self, transcript: str, speakers: list[str]) -> MeetingSummary:
        messages = self._build_messages(transcript, speakers)
        system = "You are a professional meeting assistant. Return only valid JSON."

        if self.provider == "anthropic":
            raw = await self._call_anthropic(messages, system)
        elif self.provider == "openai":
            raw = await self._call_openai(messages, system)
        elif self.provider == "groq":
            raw = await self._call_groq(messages, system)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        return OllamaSummarizer("_")._parse_response(raw)  # reuse parser

    async def _call_anthropic(self, messages: list[dict], system: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={"model": self.model, "max_tokens": 2048, "system": system, "messages": messages},
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"]

    async def _call_openai(self, messages: list[dict], system: str) -> str:
        msgs = [{"role": "system", "content": system}] + messages
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": msgs, "max_tokens": 2048},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def _call_groq(self, messages: list[dict], system: str) -> str:
        msgs = [{"role": "system", "content": system}] + messages
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": msgs, "max_tokens": 2048},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
