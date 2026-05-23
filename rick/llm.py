import json
import re
import os
import time
import requests

from .logging_setup import log
from .config import SYSTEM_PROMPT


def _strip_thinking(raw: str) -> str:
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    return raw.strip()


def _extract_json(text: str) -> str:
    text = _strip_thinking(text)
    for bloque in re.split(r"```(?:json)?", text):
        bloque = bloque.strip().rstrip("`").strip()
        if bloque.startswith("{"):
            return bloque
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def _parse_response(raw: str) -> dict:
    try:
        limpio = _extract_json(raw)
        result = json.loads(limpio)
        result.setdefault("accion", "CONVERSAR")
        result.setdefault("parametros", {})
        result.setdefault("respuesta_voz", "Hecho.")
        if not result["respuesta_voz"].strip():
            result["respuesta_voz"] = "Hecho."
        return result
    except json.JSONDecodeError:
        texto = _strip_thinking(raw).strip()
        return {
            "accion": "CONVERSAR",
            "parametros": {},
            "respuesta_voz": texto[:300] or "No entendí la respuesta.",
        }


def _error(msg: str) -> dict:
    return {"accion": "ERROR", "parametros": {}, "respuesta_voz": msg}


def _ollama(prompt: str, cfg: dict, system_prompt: str | None = None, raw: bool = False,
            model: str | None = None, max_tokens: int | None = None) -> dict | str:
    sp = system_prompt or SYSTEM_PROMPT
    payload = {
        "model": model or cfg["model"],
        "prompt": prompt,
        "system": sp,
        "stream": False,
        "options": {
            "temperature": 0.75,
            "num_predict": max_tokens or 600,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        },
    }
    last_error = None
    retries = 2
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                cfg["ollama_url"],
                json=payload,
                timeout=cfg.get("ollama_timeout", 120),
            )
            r.raise_for_status()
            raw_text = r.json()["response"].strip()
            log.debug(f"Ollama raw: {repr(raw_text[:200])}")
            return raw_text if raw else _parse_response(raw_text)
        except requests.ConnectionError as e:
            last_error = e
            log.warning(f"Ollama sin conexión (intento {attempt+1})")
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            last_error = e
            log.error(f"Ollama error: {e}")
            break
    return _error(f"Error de conexión con Ollama: {last_error}") if not raw else ""


def _gemini(prompt: str, cfg: dict, system_prompt: str | None = None, raw: bool = False,
            model: str | None = None, max_tokens: int | None = None) -> dict | str:
    try:
        import google.generativeai as genai
    except ImportError:
        return _error("SDK de Gemini no instalada. Ejecuta: pip install google-generativeai")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _error("GEMINI_API_KEY no configurada en .env o variables de entorno")

    sp = system_prompt or SYSTEM_PROMPT
    try:
        genai.configure(api_key=api_key)
        model_i = genai.GenerativeModel(
            model_name=model or cfg["model"],
            system_instruction=sp,
        )
        gen_config = {}
        if max_tokens:
            gen_config["max_output_tokens"] = max_tokens
        response = model_i.generate_content(prompt, generation_config=gen_config)
        raw_text = response.text.strip()
        log.debug(f"Gemini raw: {repr(raw_text[:200])}")
        return raw_text if raw else _parse_response(raw_text)
    except Exception as e:
        log.error(f"Gemini error: {e}")
        return _error(f"Error con Gemini: {str(e)[:100]}")


def _deepseek(prompt: str, cfg: dict, system_prompt: str | None = None, raw: bool = False,
              model: str | None = None, max_tokens: int | None = None) -> dict | str:
    try:
        from openai import OpenAI
    except ImportError:
        return _error("SDK de OpenAI no instalada. Ejecuta: pip install openai")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return _error("DEEPSEEK_API_KEY no configurada en .env o variables de entorno")

    sp = system_prompt or SYSTEM_PROMPT
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model=model or cfg["model"],
            messages=[
                {"role": "system", "content": sp},
                {"role": "user", "content": prompt},
            ],
            temperature=0.75,
            max_tokens=max_tokens or 600,
        )
        raw_text = response.choices[0].message.content.strip()
        log.debug(f"DeepSeek raw: {repr(raw_text[:200])}")
        return raw_text if raw else _parse_response(raw_text)
    except Exception as e:
        log.error(f"DeepSeek error: {e}")
        return _error(f"Error con DeepSeek: {str(e)[:100]}")


def _anthropic(prompt: str, cfg: dict, system_prompt: str | None = None, raw: bool = False,
               model: str | None = None, max_tokens: int | None = None) -> dict | str:
    try:
        from anthropic import Anthropic
    except ImportError:
        return _error("SDK de Anthropic no instalada. Ejecuta: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _error("ANTHROPIC_API_KEY no configurada en .env o variables de entorno")

    sp = system_prompt or SYSTEM_PROMPT
    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model or cfg["model"],
            max_tokens=max_tokens or cfg.get("max_tokens_reactive", 6144),
            system=sp,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text.strip()
        log.debug(f"Anthropic raw: {repr(raw_text[:200])}")
        return raw_text if raw else _parse_response(raw_text)
    except Exception as e:
        log.error(f"Anthropic error: {e}")
        return _error(f"Error con Anthropic: {str(e)[:100]}")


def consultar_llm(prompt: str, cfg: dict, system_prompt: str | None = None,
                  raw: bool = False, model: str | None = None,
                  max_tokens: int | None = None) -> dict | str:
    provider = cfg.get("provider", "ollama").lower()
    kw = {"system_prompt": system_prompt, "raw": raw, "model": model, "max_tokens": max_tokens}

    if provider == "ollama":
        return _ollama(prompt, cfg, **kw)
    elif provider == "gemini":
        return _gemini(prompt, cfg, **kw)
    elif provider == "deepseek":
        return _deepseek(prompt, cfg, **kw)
    elif provider == "anthropic":
        return _anthropic(prompt, cfg, **kw)
    else:
        return _error(f"Proveedor desconocido: {provider}")
