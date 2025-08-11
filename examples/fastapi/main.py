# Simplified FastAPI server for PromptSan with anonymization proxy
import json
import os
import time
from typing import Any, Dict, Generator, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI
from pydantic import BaseModel

from promptsan import PromptSanitizer, SanConfig


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None


app = FastAPI(title="PromptSan Anonymization Proxy")


def load_config() -> SanConfig:
    """Load configuration from JSON file"""
    config_path = os.getenv("SANCONFIG_PATH", "examples/fastapi/config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SanConfig(**data)
    except Exception as exc:
        raise RuntimeError(f"Failed to load config from '{config_path}': {exc}")


def get_openai_client(request: Request, payload: ChatRequest) -> OpenAI:
    """Create OpenAI client with proper authentication"""
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

    # Get API key from header or payload
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        api_key = auth_header.split(" ", 1)[1]
    elif payload.api_key:
        api_key = payload.api_key
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    return OpenAI(api_key=api_key, base_url=base_url)


def anonymize_messages(
    messages: List[ChatMessage], sanitizer: PromptSanitizer
) -> tuple[List[Dict[str, str]], Dict[str, str]]:
    """Anonymize messages and return anonymized messages + mapping"""
    combined_text = "\n".join([f"{m.role}: {m.content}" for m in messages])

    print(f"[ANONYMIZE] Strategies configured: {sanitizer.cfg.strategies}")
    print(f"[ANONYMIZE] LLM model: {sanitizer.cfg.llm_model}")
    print(f"[ANONYMIZE] LLM base URL: {sanitizer.cfg.llm_base_url}")
    print(f"[ANONYMIZE] Original text:\n{combined_text}")

    result = sanitizer.anonymize(combined_text)

    print(f"[ANONYMIZE] Anonymized text:\n{result.text}")
    print(f"[ANONYMIZE] Mapping: {result.mapping}")

    # Apply mapping to individual messages
    anonymized_messages = []
    for msg in messages:
        content = msg.content
        for entity, token in result.mapping.items():
            content = content.replace(entity, token)
        anonymized_messages.append({"role": msg.role, "content": content})

    return anonymized_messages, result.mapping


def deanonymize_content(
    content: str, mapping: Dict[str, str], sanitizer: PromptSanitizer
) -> str:
    """Deanonymize content using mapping"""
    deanonymized = sanitizer.deanonymize(content, mapping)
    print(f"[DEANONYMIZE] Original: {content}")
    print(f"[DEANONYMIZE] Restored: {deanonymized}")
    return deanonymized


# Initialize global components
print("[DEBUG] Loading config...")
config = load_config()
print(f"[DEBUG] Config loaded: {config.strategies}")
SANITIZER = PromptSanitizer(config)
print(f"[STARTUP] PromptSan initialized with strategies: {SANITIZER.cfg.strategies}")


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "strategies": SANITIZER.cfg.strategies}


@app.get("/v1/models")
async def list_models(request: Request) -> Dict[str, Any]:
    """OpenAI-compatible models endpoint - proxies to OpenRouter"""
    try:
        # Get API key from header or env
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header.split(" ", 1)[1]
        else:
            api_key = os.getenv("OPENAI_API_KEY", "")

        if not api_key or api_key == "fake-key":
            raise HTTPException(
                status_code=401, detail="Missing valid API key for models endpoint"
            )

        # Create OpenAI client to query OpenRouter
        base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        client = OpenAI(api_key=api_key, base_url=base_url)

        # Get real models from OpenRouter
        models = client.models.list()
        return models.model_dump()

    except Exception as exc:
        print(f"[ERROR] Models endpoint: {exc}")
        raise HTTPException(status_code=502, detail=f"OpenRouter API error: {exc}")


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, payload: ChatRequest) -> Any:
    """Main chat completions endpoint with anonymization"""
    print(f"[REQUEST] Model: {payload.model}, Stream: {payload.stream}")

    try:
        # Step 1: Anonymize messages
        anonymized_messages, mapping = anonymize_messages(payload.messages, SANITIZER)

        # Step 2: Prepare OpenAI client and params
        client = get_openai_client(request, payload)

        params = {
            "model": payload.model,
            "messages": anonymized_messages,
            "stream": payload.stream,
        }
        if payload.temperature is not None:
            params["temperature"] = payload.temperature
        if payload.max_tokens is not None:
            params["max_tokens"] = payload.max_tokens

        # Step 3: Call OpenAI API
        if payload.stream:
            return handle_streaming_response(client, params, mapping)
        else:
            return handle_non_streaming_response(client, params, mapping)

    except Exception as exc:
        print(f"[ERROR] {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


def handle_non_streaming_response(
    client: OpenAI, params: Dict[str, Any], mapping: Dict[str, str]
) -> JSONResponse:
    """Handle non-streaming response"""
    try:
        response = client.chat.completions.create(**params)

        # Deanonymize response content
        if response.choices and response.choices[0].message.content:
            original_content = response.choices[0].message.content
            deanonymized_content = deanonymize_content(
                original_content, mapping, SANITIZER
            )

            # Build response dict and update content
            response_dict = response.model_dump()
            response_dict["choices"][0]["message"]["content"] = deanonymized_content

            return JSONResponse(content=response_dict)

        return JSONResponse(content=response.model_dump())

    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {exc}")


def handle_streaming_response(
    client: OpenAI, params: Dict[str, Any], mapping: Dict[str, str]
) -> StreamingResponse:
    """Handle streaming response"""

    def event_stream() -> Generator[str, None, None]:
        chat_id = f"chatcmpl_{uuid4().hex}"
        created = int(time.time())

        try:
            # Real-time streaming with deanonymization on-the-fly
            stream = client.chat.completions.create(**params)
            dean_stream = SANITIZER.deanonymize_stream(
                (
                    choice.delta.content
                    for chunk in stream
                    for choice in chunk.choices
                    if hasattr(choice.delta, "content") and choice.delta.content
                ),
                mapping,
            )

            first = True
            for piece in dean_stream:
                if piece:
                    delta = {"content": piece}
                    if first:
                        delta["role"] = "assistant"
                        first = False

                    chunk_data = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": params["model"],
                        "choices": [
                            {"index": 0, "delta": delta, "finish_reason": None}
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

            # Final chunk with finish_reason
            final_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": params["model"],
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as exc:
            error_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": params.get("model", "unknown"),
                "choices": [{"index": 0, "delta": {}, "finish_reason": "error"}],
                "error": str(exc),
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
