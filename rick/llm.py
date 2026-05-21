import json
import re
import os
import time
import requests

from .logging_setup import log
from .config import SYSTEM_PROMPT


def _strip_thinking(raw: str) -> str:
    """Elimina bloques <think>...</think> que generan algunos modelos."""
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    return raw.strip()


def _extract_json(text: str) -> str:
    """Extrae el primer objeto JSON válido del texto."""
    text = _strip_thinking(text)
    # Quitar bloques markdown ```json ... ```
    for bloque in re.split(r"```(?:json)?", text):
        bloque = bloque.strip().rstrip("`").strip()
        if bloque.startswith("{"):
            return bloque
    # Buscar con regex
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def _parse_response(raw: str) -> dict:
    """Convierte una respuesta de modelo en el dict estándar."""
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


def _ollama(prompt: str, cfg: dict) -> dict:
    """Consulta Ollama (modelos locales)."""
    payload = {
        "model":   cfg["model"],
        "prompt":  prompt,
        "system":  SYSTEM_PROMPT,
        "stream":  False,
        "options": {
            "temperature":  0.75,
            "num_predict":  600,
            "top_p":        0.9,
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
            raw = r.json()["response"].strip()
            log.debug(f"Ollama raw: {repr(raw[:200])}")
            return _parse_response(raw)

        except requests.ConnectionError as e:
            last_error = e
            log.warning(f"Ollama sin conexión (intento {attempt+1})")
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            last_error = e
            log.error(f"Ollama error: {e}")
            break

    return {
        "accion": "ERROR",
        "parametros": {},
        "respuesta_voz": f"Error de conexión con Ollama: {last_error}",
    }


def _gemini(prompt: str, cfg: dict) -> dict:
    """Consulta Gemini (Google)."""
    try:
        import google.generativeai as genai
    except ImportError:
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": "SDK de Gemini no instalada. Ejecuta: pip install google-generativeai",
        }

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": "GEMINI_API_KEY no configurada en .env o variables de entorno",
        }

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=cfg["model"],
            system_instruction=SYSTEM_PROMPT,
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        log.debug(f"Gemini raw: {repr(raw[:200])}")
        return _parse_response(raw)

    except Exception as e:
        log.error(f"Gemini error: {e}")
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": f"Error con Gemini: {str(e)[:100]}",
        }


def _deepseek(prompt: str, cfg: dict) -> dict:
    """Consulta DeepSeek (compatible con OpenAI API)."""
    try:
        from openai import OpenAI
    except ImportError:
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": "SDK de OpenAI no instalada. Ejecuta: pip install openai",
        }

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": "DEEPSEEK_API_KEY no configurada en .env o variables de entorno",
        }

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        response = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.75,
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()
        log.debug(f"DeepSeek raw: {repr(raw[:200])}")
        return _parse_response(raw)

    except Exception as e:
        log.error(f"DeepSeek error: {e}")
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": f"Error con DeepSeek: {str(e)[:100]}",
        }


def _anthropic(prompt: str, cfg: dict) -> dict:
    """Consulta Anthropic (Claude)."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": "SDK de Anthropic no instalada. Ejecuta: pip install anthropic",
        }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": "ANTHROPIC_API_KEY no configurada en .env o variables de entorno",
        }

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=cfg["model"],
            max_tokens=cfg.get("max_tokens_reactive", 1024),
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.content[0].text.strip()
        log.debug(f"Anthropic raw: {repr(raw[:200])}")
        return _parse_response(raw)

    except Exception as e:
        log.error(f"Anthropic error: {e}")
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": f"Error con Anthropic: {str(e)[:100]}",
        }


def consultar_llm(prompt: str, cfg: dict) -> dict:
    """Consulta el LLM usando el proveedor configurado."""
    provider = cfg.get("provider", "ollama").lower()

    if provider == "ollama":
        return _ollama(prompt, cfg)
    elif provider == "gemini":
        return _gemini(prompt, cfg)
    elif provider == "deepseek":
        return _deepseek(prompt, cfg)
    elif provider == "anthropic":
        return _anthropic(prompt, cfg)
    else:
        return {
            "accion": "ERROR",
            "parametros": {},
            "respuesta_voz": f"Proveedor desconocido: {provider}",
        }


# Mantener para compatibilidad hacia atrás
def consultar_ollama(prompt: str, cfg: dict, retries: int = 2) -> dict:
    """Deprecated: usa consultar_llm() en su lugar."""
    return _ollama(prompt, cfg)
