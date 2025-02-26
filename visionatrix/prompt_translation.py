import logging
import re

import google.generativeai as genai
import ollama

from .db_queries import get_setting
from .etc import temporary_env_var
from .llm_utils import LLM_TRANSLATE_SYSTEM_PROMPT
from .pydantic_models import TranslatePromptRequest, TranslatePromptResponse

LOGGER = logging.getLogger("visionatrix")


async def translate_prompt_with_ollama(
    user_id: str, is_admin: bool, data: TranslatePromptRequest
) -> TranslatePromptResponse:
    ollama_url = await get_setting(user_id, "ollama_url", is_admin)
    ollama_llm_model = await get_setting(user_id, "ollama_llm_model", is_admin)
    ollama_keepalive = await get_setting(user_id, "ollama_keepalive", is_admin)
    if ollama_keepalive:
        ollama_keepalive += "m"
    else:
        ollama_keepalive = 0

    if not ollama_url:
        LOGGER.debug("No custom Ollama URL defined, trying default one.")
        ollama_url = None
    if not ollama_llm_model:
        LOGGER.debug("No custom Ollama LLM model defined, trying default one.")
        ollama_llm_model = "qwen2.5:14b"

    system_prompt = LLM_TRANSLATE_SYSTEM_PROMPT if data.system_prompt is None else data.system_prompt

    ollama_client = ollama.AsyncClient(host=ollama_url)
    ollama_response = await ollama_client.generate(
        ollama_llm_model, data.prompt, system=system_prompt, keep_alive=ollama_keepalive
    )
    return TranslatePromptResponse(
        prompt=data.prompt,
        result=re.sub(r"<think>.*?</think>", "", ollama_response["response"], flags=re.DOTALL).strip(),
        done_reason=ollama_response["done_reason"],
    )


async def translate_prompt_with_gemini(
    user_id: str, is_admin: bool, data: TranslatePromptRequest
) -> TranslatePromptResponse:
    google_proxy = await get_setting(user_id, "google_proxy", is_admin)
    google_api_key = await get_setting(user_id, "google_api_key", is_admin)
    gemini_model = await get_setting(user_id, "gemini_model", is_admin)
    if not gemini_model:
        gemini_model = "gemini-2.0-flash-001"

    if not google_api_key:
        raise ValueError("No GOOGLE_API_KEY defined, can't perform prompt translation")

    system_prompt = LLM_TRANSLATE_SYSTEM_PROMPT if data.system_prompt is None else data.system_prompt
    transport_type = "rest" if google_proxy else None
    genai.configure(api_key=google_api_key, transport=transport_type)
    model = genai.GenerativeModel(model_name=gemini_model, system_instruction=system_prompt)

    if google_proxy:
        # Due to a bug, we are currently making sync requests here if a proxy server is used:
        # https://github.com/google-gemini/generative-ai-python/issues/499
        LOGGER.debug("Google Proxy is defined.")
        with temporary_env_var("HTTP_PROXY", google_proxy), temporary_env_var("HTTPS_PROXY", google_proxy):
            response = model.generate_content(data.prompt, safety_settings="BLOCK_NONE")
    else:
        response = await model.generate_content_async(data.prompt, safety_settings="BLOCK_NONE")
    finish_reason = int(response.candidates[0].finish_reason)
    if finish_reason in (1, 2):  # FinishReason.STOP, FinishReason.MAX_TOKENS
        done_reason = "stop" if finish_reason == 1 else "max_tokens"
        return TranslatePromptResponse(prompt=data.prompt, result=response.text.rstrip(" \n"), done_reason=done_reason)
    raise ValueError(f"Gemini returned error with stop reason: {response.candidates[0].finish_reason.name}")
