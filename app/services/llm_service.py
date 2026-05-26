"""LLM service for RAG queries with OpenAI and Anthropic support."""
import json
import logging
import os
import time
from typing import AsyncGenerator, Optional
import openai
from anthropic import Anthropic
from app.utils.latency_tracker import LatencyRecorder, STAGE_LLM

logger = logging.getLogger(__name__)

# Initialize clients (lazy)
_openai_client: Optional[openai.AsyncOpenAI] = None
_anthropic_client: Optional[Anthropic] = None


def _get_openai_client() -> Optional[openai.AsyncOpenAI]:
    """Get OpenAI client if API key is available."""
    global _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        if _openai_client is None:
            _openai_client = openai.AsyncOpenAI(api_key=api_key)
        return _openai_client
    return None


def _get_anthropic_client() -> Optional[Anthropic]:
    """Get Anthropic client if API key is available."""
    global _anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        if _anthropic_client is None:
            _anthropic_client = Anthropic(api_key=api_key)
        return _anthropic_client
    return None


def detect_free_tier_limit(provider: str) -> bool:
    """
    Detect if using free tier (basic heuristic).
    
    Args:
        provider: "openai" or "anthropic"
        
    Returns:
        True if free tier detected
    """
    # Basic heuristic: check for common free tier patterns
    # This can be extended with actual API checks
    return False


async def stream_llm_response(
    system_prompt: str,
    user_prompt: str,
    provider: str = "openai",
    recorder: Optional[LatencyRecorder] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream LLM response using SSE-compatible generator.
    
    Args:
        system_prompt: System prompt
        user_prompt: User prompt
        provider: "openai" or "anthropic"
        
    Yields:
        Chunks of text
    """
    start = time.perf_counter()
    try:
        if provider == "openai":
            client = _get_openai_client()
            if not client:
                yield "Error: OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
                return
            
            try:
                stream = await client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Use free-tier compatible model
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    stream=True,
                    temperature=0.7
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                error_msg = str(e)
                if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                    yield f"Error: Free tier limit reached. {error_msg}"
                else:
                    yield f"Error: {error_msg}"
                return
        
        elif provider == "anthropic":
            client = _get_anthropic_client()
            if not client:
                yield "Error: Anthropic API key not configured. Please set ANTHROPIC_API_KEY environment variable."
                return
            
            try:
                # Anthropic streaming
                with client.messages.stream(
                    model="claude-3-haiku-20240307",  # Cheapest model
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                        
            except Exception as e:
                logger.error(f"Anthropic API error: {e}")
                error_msg = str(e)
                if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                    yield f"Error: Free tier limit reached. {error_msg}"
                else:
                    yield f"Error: {error_msg}"
                return
        
        else:
            yield f"Error: Unknown provider: {provider}"
            return
            
    except Exception as e:
        logger.error(f"LLM service error: {e}", exc_info=True)
        yield f"Error: {str(e)}"
    finally:
        if recorder is not None:
            elapsed_ms = (time.perf_counter() - start) * 1000
            recorder.record(STAGE_LLM, elapsed_ms)


def get_available_providers() -> list[str]:
    """Get list of available LLM providers."""
    providers = []
    if os.getenv("OPENAI_API_KEY"):
        providers.append("openai")
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append("anthropic")
    return providers


class LLMService:
    """Non-streaming LLM completion helper."""

    ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
    OPENAI_MODEL = "gpt-4o-mini"

    @staticmethod
    def _select_provider() -> tuple[str, str]:
        if os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic", LLMService.ANTHROPIC_MODEL
        if os.getenv("OPENAI_API_KEY"):
            return "openai", LLMService.OPENAI_MODEL
        raise ValueError("No LLM API key configured")

    @staticmethod
    async def complete(
        prompt: str,
        *,
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> tuple[str, str]:
        """Return (response_text, model_name)."""
        import asyncio

        provider, model_name = LLMService._select_provider()

        if provider == "anthropic":
            client = _get_anthropic_client()
            if client is None:
                raise ValueError("No LLM API key configured")

            def _sync_anthropic() -> str:
                message = client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                return message.content[0].text

            text = await asyncio.to_thread(_sync_anthropic)
            return text, model_name

        client = _get_openai_client()
        if client is None:
            raise ValueError("No LLM API key configured")

        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        return content, model_name
