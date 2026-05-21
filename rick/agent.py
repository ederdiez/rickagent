import os
import time
import json
import re
from typing import Optional

from .logging_setup import log
from .config import AGENT_SYSTEM_PROMPT
from .llm import _extract_json

MAX_STEPS = 20
AGENT_MAX_TOKENS = 4096


# Definición de herramientas disponibles para el agente
AGENT_TOOLS = [
    {
        "name": "EJECUTAR_CMD",
        "description": "Ejecuta un comando de shell arbitrario y retorna stdout+stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cmd": {"type": "string", "description": "Comando shell a ejecutar"},
                "timeout": {"type": "integer", "description": "Timeout en segundos", "default": 10}
            },
            "required": ["cmd"]
        }
    },
    {
        "name": "EJECUTAR_PYTHON",
        "description": "Ejecuta código Python, retorna output y errores. Ideal para computar, procesar datos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo": {"type": "string", "description": "Código Python a ejecutar"},
                "timeout": {"type": "integer", "description": "Timeout en segundos", "default": 30}
            },
            "required": ["codigo"]
        }
    },
    {
        "name": "CREAR_ARCHIVO",
        "description": "Crea o sobreescribe un archivo con contenido dado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ruta": {"type": "string", "description": "Ruta absoluta del archivo"},
                "contenido": {"type": "string", "description": "Contenido del archivo"}
            },
            "required": ["ruta", "contenido"]
        }
    },
    {
        "name": "LEER_ARCHIVO",
        "description": "Lee el contenido de un archivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ruta": {"type": "string", "description": "Ruta absoluta del archivo"}
            },
            "required": ["ruta"]
        }
    },
    {
        "name": "MOVER_ARCHIVO",
        "description": "Mueve o renombra un archivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origen": {"type": "string"},
                "destino": {"type": "string"}
            },
            "required": ["origen", "destino"]
        }
    },
    {
        "name": "COPIAR_ARCHIVO",
        "description": "Copia un archivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origen": {"type": "string"},
                "destino": {"type": "string"}
            },
            "required": ["origen", "destino"]
        }
    },
    {
        "name": "BORRAR_ARCHIVO",
        "description": "Borra un archivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ruta": {"type": "string"}
            },
            "required": ["ruta"]
        }
    },
    {
        "name": "CREAR_CARPETA",
        "description": "Crea un directorio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ruta": {"type": "string"}
            },
            "required": ["ruta"]
        }
    },
    {
        "name": "LISTAR_DIR",
        "description": "Lista contenido de un directorio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ruta": {"type": "string"}
            },
            "required": ["ruta"]
        }
    },
    {
        "name": "LEER_DIR_RECURSIVO",
        "description": "Lista el árbol de archivos de un directorio con profundidad controlada.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ruta": {"type": "string", "description": "Ruta del directorio"},
                "profundidad": {"type": "integer", "description": "Profundidad máxima", "default": 3}
            },
            "required": ["ruta"]
        }
    },
    {
        "name": "BUSCAR_EN_ARCHIVOS",
        "description": "Busca texto (grep) en archivos de un directorio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patron": {"type": "string", "description": "Patrón a buscar"},
                "directorio": {"type": "string", "description": "Directorio donde buscar"},
                "extension": {"type": "string", "description": "Extensión de archivos (ej: .py)"}
            },
            "required": ["patron", "directorio"]
        }
    },
    {
        "name": "BUSCAR_ARCHIVO",
        "description": "Busca archivos por nombre.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Patrón de nombre (ej: *.py)"},
                "directorio": {"type": "string"},
                "profundidad": {"type": "integer"}
            },
            "required": ["nombre", "directorio"]
        }
    },
    {
        "name": "ESCRIBIR_Y_EJECUTAR",
        "description": "Escribe un script en /tmp y lo ejecuta.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del script"},
                "contenido": {"type": "string", "description": "Contenido del script"},
                "interprete": {"type": "string", "description": "Intérprete (python3, bash, etc)", "default": "python3"},
                "timeout": {"type": "integer", "default": 30}
            },
            "required": ["nombre", "contenido"]
        }
    },
    {
        "name": "GIT_CMD",
        "description": "Ejecuta comandos git (status, log, diff, add, commit, push, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "subcmd": {"type": "string", "description": "Subcomando y args, ej: 'log --oneline -5'"},
                "directorio": {"type": "string", "description": "Directorio del repositorio"}
            },
            "required": ["subcmd", "directorio"]
        }
    },
    {
        "name": "SISTEMA_INFO",
        "description": "Retorna información del sistema.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "ABRIR_URL",
        "description": "Abre una URL en el navegador.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "SCREENSHOT",
        "description": "Toma una captura de pantalla.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
]


def _is_complex_task(texto: str) -> bool:
    """Clasifica si una tarea requiere el agente o el modo reactivo."""
    complex_keywords = {
        "escribe", "crea", "programa", "script", "código", "implementa",
        "automatiza", "depura", "arregla el bug", "refactoriza", "analiza",
        "explora el proyecto", "busca en", "git", "ejecuta y", "prueba",
        "instala", "configura", "modifica el archivo", "proyecto",
        "función", "clase", "módulo", "test", "tests", "generador",
        "calcula", "procesa", "transforma", "convierte",
    }
    texto_lower = texto.lower()
    # Tareas largas probablemente son complejas
    if len(texto.split()) > 15:
        return True
    # Palabras clave de programación/automatización
    for kw in complex_keywords:
        if kw in texto_lower:
            return True
    return False


def run_agent_task(task: str, cfg: dict, memory, executor, tts) -> str:
    """
    Ejecuta una tarea compleja mediante agentic loop.
    Soporta múltiples proveedores: Anthropic (tool use nativo), Ollama/otros (JSON parsing).
    """
    provider = cfg.get("provider", "anthropic").lower()

    if provider == "anthropic":
        return _run_agent_anthropic(task, cfg, memory, executor, tts)
    else:
        # Ollama, Gemini, DeepSeek con JSON parsing manual
        return _run_agent_generic(task, cfg, memory, executor, tts)


def _run_agent_anthropic(task: str, cfg: dict, memory, executor, tts) -> str:
    """Agentic loop para Anthropic usando tool use nativo."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return "SDK de Anthropic no instalada. Usa Ollama o instala: pip install anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "ANTHROPIC_API_KEY no configurada."

    client = Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": task}]
    tts.say("Entendido. Déjame trabajar en eso.")

    step = 0
    start_time = time.time()

    while step < MAX_STEPS:
        step += 1
        elapsed = time.time() - start_time

        if elapsed > cfg.get("agent_timeout_s", 300):
            log.warning("[Agente] Timeout global alcanzado")
            return "Me tomó demasiado tiempo. Tarea cancelada."

        log.info(f"[Agente Anthropic] Paso {step}/{MAX_STEPS} | Tiempo: {elapsed:.1f}s")

        try:
            response = client.messages.create(
                model=cfg.get("agent_model", "claude-haiku-4-5"),
                max_tokens=AGENT_MAX_TOKENS,
                system=AGENT_SYSTEM_PROMPT,
                tools=AGENT_TOOLS,
                messages=messages,
            )
        except Exception as e:
            log.error(f"[Agente] Error LLM: {e}")
            return f"Error en el agente: {str(e)[:100]}"

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    final_text = block.text.strip()
                    log.info(f"[Agente] Tarea completada: {final_text[:100]}")
                    memory.add_assistant({
                        "respuesta_voz": final_text,
                        "accion": "AGENTE"
                    })
                    return final_text
            return "Tarea completada sin mensaje."

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if not hasattr(block, "type") or block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                log.info(f"[Agente] Herramienta: {tool_name} | Input: {str(tool_input)[:80]}")

                try:
                    result_str = executor.run_silent(tool_name, tool_input)
                    result_str = (result_str or "OK (sin output)").strip()
                    if len(result_str) > 2000:
                        result_str = result_str[:2000] + "\n... (truncado)"
                except Exception as e:
                    result_str = f"Error ejecutando {tool_name}: {e}"

                log.debug(f"[Agente] Resultado: {result_str[:200]}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_str,
                })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            continue

        log.warning(f"[Agente] stop_reason inesperado: {response.stop_reason}")
        break

    return "Alcancé el límite de pasos. Tarea incompleta."


def _build_tools_description() -> str:
    """Construye descripción textual de herramientas para proveedores sin tool use nativo."""
    lines = ["HERRAMIENTAS DISPONIBLES:\n"]
    for tool in AGENT_TOOLS:
        name = tool["name"]
        desc = tool["description"]
        props = tool["input_schema"].get("properties", {})
        params = ", ".join(props.keys())
        lines.append(f"- {name}({params}): {desc}")
    return "\n".join(lines)


def _run_agent_generic(task: str, cfg: dict, memory, executor, tts) -> str:
    """Agentic loop para Ollama/otros proveedores usando JSON parsing manual."""
    from .llm import consultar_llm

    tts.say("Entendido. Déjame trabajar en eso.")

    # Construir prompt con herramientas descritas
    tools_desc = _build_tools_description()
    system_prompt = f"""{AGENT_SYSTEM_PROMPT}

{tools_desc}

INSTRUCCIONES DE RESPUESTA JSON:
Responde SIEMPRE con JSON puro (sin markdown, sin comentarios):
{{
    "accion": "NOMBRE_HERRAMIENTA",
    "parametros": {{"param1": "valor1", "param2": valor2}},
    "pensamiento": "Por qué estoy haciendo esto",
    "listo": false
}}

Si la tarea está completa, usa:
{{
    "accion": "CONVERSAR",
    "parametros": {{}},
    "respuesta_voz": "Resumen final de qué hiciste",
    "listo": true
}}
"""

    # Historial conversacional para el prompt
    conversation = []
    start_time = time.time()

    for step in range(MAX_STEPS):
        elapsed = time.time() - start_time

        if elapsed > cfg.get("agent_timeout_s", 300):
            log.warning("[Agente-Ollama] Timeout global alcanzado")
            return "Me tomó demasiado tiempo. Tarea cancelada."

        log.info(f"[Agente-Ollama] Paso {step + 1}/{MAX_STEPS} | Tiempo: {elapsed:.1f}s")

        # Construir prompt para esta iteración
        if step == 0:
            prompt = f"Tarea: {task}"
        else:
            prompt = "\n".join(conversation)

        # Llamar al LLM
        try:
            # Usar la función de consulta existente pero con system_prompt personalizado
            messages = [{"role": "user", "content": prompt}]

            # Llamada directa según proveedor
            provider = cfg.get("provider", "ollama").lower()

            if provider == "ollama":
                raw_response = _call_ollama(prompt, system_prompt, cfg)
            elif provider == "gemini":
                raw_response = _call_gemini(prompt, system_prompt, cfg)
            elif provider == "deepseek":
                raw_response = _call_deepseek(prompt, system_prompt, cfg)
            else:
                return f"Proveedor no soportado en modo agente: {provider}"

            log.debug(f"[Agente] Raw response: {raw_response[:200]}")

            # Parsear JSON
            try:
                json_str = _extract_json(raw_response)
                resp = json.loads(json_str)
            except json.JSONDecodeError:
                log.error(f"[Agente] JSON parsing falló: {raw_response[:200]}")
                return f"Error parseando respuesta del LLM. Respuesta: {raw_response[:200]}"

            accion = resp.get("accion", "CONVERSAR").upper()
            params = resp.get("parametros", {})
            pensamiento = resp.get("pensamiento", "")
            listo = resp.get("listo", False)

            log.info(f"[Agente] Acción: {accion} | Listo: {listo}")

            if pensamiento:
                log.debug(f"[Agente] Pensamiento: {pensamiento}")

            # Si está listo, retornar
            if listo or accion == "CONVERSAR":
                respuesta_final = resp.get("respuesta_voz", "Tarea completada.")
                memory.add_assistant({
                    "respuesta_voz": respuesta_final,
                    "accion": "AGENTE"
                })
                return respuesta_final

            # Ejecutar herramienta
            try:
                resultado = executor.run_silent(accion, params)
                resultado = (resultado or "OK (sin output)").strip()
                if len(resultado) > 1000:
                    resultado = resultado[:1000] + "\n... (truncado)"
            except Exception as e:
                resultado = f"Error: {e}"

            log.info(f"[Agente] Resultado ({accion}): {resultado[:100]}")

            # Agregar al historial para siguiente iteración
            conversation.append(f"[RICK ejecutó {accion}]: {resultado}")

        except Exception as e:
            log.error(f"[Agente] Error en iteración {step + 1}: {e}")
            return f"Error en el agente: {str(e)[:100]}"

    return "Alcancé el límite de pasos. Tarea incompleta."


def _call_ollama(prompt: str, system_prompt: str, cfg: dict) -> str:
    """Llama a Ollama directamente."""
    import requests

    payload = {
        "model": cfg.get("model", "llama2"),
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.75,
            "num_predict": 1024,
            "top_p": 0.9,
        },
    }

    try:
        r = requests.post(
            cfg.get("ollama_url", "http://localhost:11434/api/generate"),
            json=payload,
            timeout=cfg.get("ollama_timeout", 120),
        )
        r.raise_for_status()
        return r.json()["response"].strip()
    except Exception as e:
        log.error(f"[Agente-Ollama] Error: {e}")
        raise


def _call_gemini(prompt: str, system_prompt: str, cfg: dict) -> str:
    """Llama a Gemini."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai not installed")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=cfg.get("model", "gemini-2.0-flash"),
            system_instruction=system_prompt,
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        log.error(f"[Agente-Gemini] Error: {e}")
        raise


def _call_deepseek(prompt: str, system_prompt: str, cfg: dict) -> str:
    """Llama a DeepSeek."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai not installed")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        response = client.chat.completions.create(
            model=cfg.get("model", "deepseek-chat"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.75,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"[Agente-DeepSeek] Error: {e}")
        raise
