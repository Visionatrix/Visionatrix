import logging
import os
from contextlib import contextmanager

import google.generativeai as genai
import ollama

from .db_queries import get_setting
from .db_queries_async import get_setting_async
from .llm_utils import LLM_TRANSLATE_SYSTEM_PROMPT
from .pydantic_models import TranslatePromptRequest, TranslatePromptResponse

LOGGER = logging.getLogger("visionatrix")


@contextmanager
def temporary_env_var(key: str, new_value):
    old_value = os.environ.get(key)
    if new_value is not None:
        os.environ[key] = new_value
    elif key in os.environ:
        del os.environ[key]
    try:
        yield
    finally:
        if old_value is not None:
            os.environ[key] = old_value
        elif key in os.environ:
            del os.environ[key]


def translate_prompt_with_ollama(user_id: str, is_admin: bool, data: TranslatePromptRequest) -> TranslatePromptResponse:
    ollama_url = get_setting(user_id, "ollama_url", is_admin)
    ollama_llm_model = get_setting(user_id, "ollama_llm_model", is_admin)

    if not ollama_url:
        LOGGER.debug("No custom Ollama URL defined, trying default one.")
        ollama_url = None
    if not ollama_llm_model:
        LOGGER.debug("No custom Ollama LLM model defined, trying default one.")
        ollama_llm_model = "qwen2.5:14b"

    system_prompt = LLM_TRANSLATE_SYSTEM_PROMPT if data.system_prompt is None else data.system_prompt

    ollama_client = ollama.Client(host=ollama_url)
    ollama_response = ollama_client.generate(ollama_llm_model, data.prompt, system=system_prompt, keep_alive=0)

    return TranslatePromptResponse(
        prompt=data.prompt,
        result=ollama_response["response"],
        done_reason=ollama_response["done_reason"],
    )


async def translate_prompt_with_ollama_async(
    user_id: str, is_admin: bool, data: TranslatePromptRequest
) -> TranslatePromptResponse:
    ollama_url = await get_setting_async(user_id, "ollama_url", is_admin)
    ollama_llm_model = await get_setting_async(user_id, "ollama_llm_model", is_admin)

    if not ollama_url:
        LOGGER.debug("No custom Ollama URL defined, trying default one.")
        ollama_url = None
    if not ollama_llm_model:
        LOGGER.debug("No custom Ollama LLM model defined, trying default one.")
        ollama_llm_model = "qwen2.5:14b"

    system_prompt = LLM_TRANSLATE_SYSTEM_PROMPT if data.system_prompt is None else data.system_prompt

    ollama_client = ollama.AsyncClient(host=ollama_url)
    ollama_response = await ollama_client.generate(ollama_llm_model, data.prompt, system=system_prompt, keep_alive=0)

    return TranslatePromptResponse(
        prompt=data.prompt,
        result=ollama_response["response"],
        done_reason=ollama_response["done_reason"],
    )


def translate_prompt_with_gemini(user_id: str, is_admin: bool, data: TranslatePromptRequest) -> TranslatePromptResponse:
    google_proxy = get_setting(user_id, "google_proxy", is_admin)
    google_api_key = get_setting(user_id, "google_api_key", is_admin)

    if not google_api_key:
        raise ValueError("No GOOGLE_API_KEY defined, can't perform prompt translation")

    system_prompt = LLM_TRANSLATE_SYSTEM_PROMPT if data.system_prompt is None else data.system_prompt
    genai.configure(api_key=google_api_key, transport="rest")
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system_prompt)

    if google_proxy:
        LOGGER.debug("Google Proxy is defined.")
        with temporary_env_var("HTTP_PROXY", google_proxy), temporary_env_var("HTTPS_PROXY", google_proxy):
            try:
                response = model.generate_content(data.prompt)
            except Exception as e:
                raise RuntimeError(str(e)) from e
    else:
        try:
            response = model.generate_content(data.prompt)
        except Exception as e:
            raise RuntimeError(str(e)) from e
    return TranslatePromptResponse(prompt=data.prompt, result=response.text, done_reason="")


async def translate_prompt_with_gemini_async(
    user_id: str, is_admin: bool, data: TranslatePromptRequest
) -> TranslatePromptResponse:
    google_proxy = await get_setting_async(user_id, "google_proxy", is_admin)
    google_api_key = await get_setting_async(user_id, "google_api_key", is_admin)

    if not google_api_key:
        raise ValueError("No GOOGLE_API_KEY defined, can't perform prompt translation")

    system_prompt = LLM_TRANSLATE_SYSTEM_PROMPT if data.system_prompt is None else data.system_prompt
    genai.configure(api_key=google_api_key, transport="rest")
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=system_prompt)

    if google_proxy:
        LOGGER.debug("Google Proxy is defined.")
        with temporary_env_var("HTTP_PROXY", google_proxy), temporary_env_var("HTTPS_PROXY", google_proxy):
            try:
                response = await model.generate_content_async(data.prompt)
            except Exception as e:
                raise RuntimeError(str(e)) from e
    else:
        try:
            response = await model.generate_content_async(data.prompt)
        except Exception as e:
            raise RuntimeError(str(e)) from e
    return TranslatePromptResponse(prompt=data.prompt, result=response.text, done_reason="")
