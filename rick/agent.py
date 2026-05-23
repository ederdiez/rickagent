import os
import time
import json
from typing import Optional

from .logging_setup import log
from .config import AGENT_SYSTEM_PROMPT
from .llm import _extract_json, consultar_llm

MAX_STEPS = 20
AGENT_MAX_TOKENS = 4096


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
        "description": "Ejecuta código Python, retorna output y errores.",
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
        "input_schema": {"type": "object", "properties": {
            "ruta": {"type": "string"}, "contenido": {"type": "string"}
        }, "required": ["ruta", "contenido"]}
    },
    {
        "name": "LEER_ARCHIVO",
        "input_schema": {"type": "object", "properties": {
            "ruta": {"type": "string"}
        }, "required": ["ruta"]}
    },
    {
        "name": "MOVER_ARCHIVO",
        "input_schema": {"type": "object", "properties": {
            "origen": {"type": "string"}, "destino": {"type": "string"}
        }, "required": ["origen", "destino"]}
    },
    {
        "name": "COPIAR_ARCHIVO",
        "input_schema": {"type": "object", "properties": {
            "origen": {"type": "string"}, "destino": {"type": "string"}
        }, "required": ["origen", "destino"]}
    },
    {
        "name": "RENOMBRAR",
        "input_schema": {"type": "object", "properties": {
            "origen": {"type": "string"}, "destino": {"type": "string"}
        }, "required": ["origen", "destino"]}
    },
    {
        "name": "BORRAR_ARCHIVO",
        "input_schema": {"type": "object", "properties": {
            "ruta": {"type": "string"}
        }, "required": ["ruta"]}
    },
    {
        "name": "CREAR_CARPETA",
        "input_schema": {"type": "object", "properties": {
            "ruta": {"type": "string"}
        }, "required": ["ruta"]}
    },
    {"name": "IR", "description": "Cambia el directorio de trabajo.",
     "input_schema": {"type": "object", "properties": {
         "directorio": {"type": "string"}
     }, "required": ["directorio"]}},
    {"name": "PWD", "input_schema": {"type": "object", "properties": {}}},
    {"name": "INFO_DIR", "input_schema": {"type": "object", "properties": {
        "ruta": {"type": "string"}
    }}},
    {"name": "LISTAR_DIR", "input_schema": {"type": "object", "properties": {
        "ruta": {"type": "string"}
    }}},
    {"name": "LEER_DIR_RECURSIVO", "input_schema": {"type": "object", "properties": {
        "ruta": {"type": "string"}, "profundidad": {"type": "integer", "default": 3}
    }, "required": ["ruta"]}},
    {"name": "BUSCAR_EN_ARCHIVOS", "input_schema": {"type": "object", "properties": {
        "patron": {"type": "string"}, "directorio": {"type": "string"},
        "extension": {"type": "string"}
    }, "required": ["patron", "directorio"]}},
    {"name": "BUSCAR_ARCHIVO", "input_schema": {"type": "object", "properties": {
        "nombre": {"type": "string"}, "directorio": {"type": "string"},
        "profundidad": {"type": "integer"}
    }, "required": ["nombre", "directorio"]}},
    {"name": "ESCRIBIR_Y_EJECUTAR", "input_schema": {"type": "object", "properties": {
        "nombre": {"type": "string"}, "contenido": {"type": "string"},
        "interprete": {"type": "string", "default": "python3"}, "timeout": {"type": "integer", "default": 30}
    }, "required": ["nombre", "contenido"]}},
    {"name": "GIT_CMD", "input_schema": {"type": "object", "properties": {
        "subcmd": {"type": "string"}, "directorio": {"type": "string"}
    }, "required": ["subcmd", "directorio"]}},
    {"name": "SISTEMA_INFO", "input_schema": {"type": "object", "properties": {}}},
    {"name": "ABRIR_URL", "input_schema": {"type": "object", "properties": {
        "url": {"type": "string"}
    }, "required": ["url"]}},
    {"name": "SCREENSHOT", "input_schema": {"type": "object", "properties": {}}},
    {"name": "BOOKMARK_GUARDAR", "description": "Guarda el directorio actual como marcador con un nombre.",
     "input_schema": {"type": "object", "properties": {
         "nombre": {"type": "string"}
     }, "required": ["nombre"]}},
    {"name": "BOOKMARK_BORRAR", "description": "Elimina un marcador por nombre.",
     "input_schema": {"type": "object", "properties": {
         "nombre": {"type": "string"}
     }, "required": ["nombre"]}},
    {"name": "BOOKMARK_LISTAR", "description": "Lista todos los marcadores guardados.",
     "input_schema": {"type": "object", "properties": {}}},
]


def _is_complex_task(texto: str) -> bool:
    complex_keywords = {
        "escribe", "crea", "programa", "script", "código", "implementa",
        "automatiza", "depura", "arregla el bug", "refactoriza", "analiza",
        "explora el proyecto", "busca en", "git", "ejecuta y", "prueba",
        "instala", "configura", "modifica el archivo", "proyecto",
        "función", "clase", "módulo", "test", "tests", "generador",
        "calcula", "procesa", "transforma", "convierte",
        "navega", "ve a", "busca carpeta", "explora",
        "encuentra el directorio", "abre la carpeta", "entra en",
        "métete en", "busca el archivo", "encuentra el archivo",
    }
    texto_lower = texto.lower()
    return any(kw in texto_lower for kw in complex_keywords)


def _build_tools_description() -> str:
    lines = ["HERRAMIENTAS DISPONIBLES:\n"]
    for tool in AGENT_TOOLS:
        name = tool["name"]
        desc = tool.get("description", "")
        props = tool["input_schema"].get("properties", {})
        params = ", ".join(props.keys())
        lines.append(f"- {name}({params}): {desc}" if desc else f"- {name}({params})")
    return "\n".join(lines)


def _truncate(text: str, max_len: int = 2000) -> str:
    if len(text) > max_len:
        return text[:max_len] + "\n... (truncado)"
    return text


def run_agent_task(task: str, cfg: dict, memory, executor, tts) -> str:
    provider = cfg.get("provider", "anthropic").lower()
    if provider == "anthropic":
        return _run_agent_anthropic(task, cfg, memory, executor, tts)
    return _run_agent_generic(task, cfg, memory, executor, tts)


def _run_agent_anthropic(task: str, cfg: dict, memory, executor, tts) -> str:
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

    start_time = time.time()
    for step in range(1, MAX_STEPS + 1):
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
                    memory.add_assistant({"respuesta_voz": final_text, "accion": "AGENTE"})
                    return final_text
            return "Tarea completada sin mensaje."

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if not hasattr(block, "type") or block.type != "tool_use":
                    continue
                log.info(f"[Agente] Herramienta: {block.name} | Input: {str(block.input)[:80]}")
                try:
                    result_str = _truncate((executor.run_silent(block.name, block.input) or "OK (sin output)").strip())
                except Exception as e:
                    result_str = f"Error ejecutando {block.name}: {e}"
                log.debug(f"[Agente] Resultado: {result_str[:200]}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result_str})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            continue

        log.warning(f"[Agente] stop_reason inesperado: {response.stop_reason}")
        break

    return "Alcancé el límite de pasos. Tarea incompleta."


def _run_agent_generic(task: str, cfg: dict, memory, executor, tts) -> str:
    tts.say("Entendido. Déjame trabajar en eso.")

    tools_desc = _build_tools_description()
    agent_system = f"""{AGENT_SYSTEM_PROMPT}

{tools_desc}

INSTRUCCIONES DE RESPUESTA JSON:
Responde SIEMPRE con JSON puro (sin markdown, sin comentarios):
{{
    "accion": "NOMBRE_HERRAMIENTA",
    "parametros": {{"param1": "valor1"}},
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

    conversation = []
    agent_model = cfg.get("agent_model") or cfg.get("model")
    agent_timeout = cfg.get("agent_timeout_s", 300)
    start_time = time.time()

    for step in range(MAX_STEPS):
        elapsed = time.time() - start_time
        if elapsed > agent_timeout:
            log.warning("[Agente] Timeout global alcanzado")
            return "Me tomó demasiado tiempo. Tarea cancelada."

        log.info(f"[Agente] Paso {step + 1}/{MAX_STEPS} | Tiempo: {elapsed:.1f}s")

        prompt = f"Tarea: {task}" if step == 0 else "\n".join(conversation)

        try:
            raw_response = consultar_llm(
                prompt, cfg,
                system_prompt=agent_system,
                raw=True,
                model=agent_model,
                max_tokens=1024,
            )
            if not raw_response:
                return "Error: respuesta vacía del proveedor LLM."
            log.debug(f"[Agente] Raw response: {raw_response[:200]}")
        except Exception as e:
            log.error(f"[Agente] Error LLM: {e}")
            return f"Error en el agente: {str(e)[:100]}"

        try:
            json_str = _extract_json(raw_response)
            resp = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            log.warning(f"[Agente] JSON falló, reintentando: {raw_response[:120]}")
            conversation.append("[ERROR]: No respondiste con JSON válido. Reintenta usando solo JSON puro sin markdown.")
            continue

        accion = resp.get("accion", "CONVERSAR").upper()
        params = resp.get("parametros", {})
        listo = resp.get("listo", False)
        log.info(f"[Agente] Acción: {accion} | Listo: {listo}")

        if resp.get("pensamiento"):
            log.debug(f"[Agente] Pensamiento: {resp['pensamiento']}")

        if listo or accion == "CONVERSAR":
            respuesta_final = resp.get("respuesta_voz", "Tarea completada.")
            memory.add_assistant({"respuesta_voz": respuesta_final, "accion": "AGENTE"})
            return respuesta_final

        try:
            resultado = _truncate((executor.run_silent(accion, params) or "OK (sin output)").strip(), max_len=1000)
        except Exception as e:
            resultado = f"Error: {e}"

        log.info(f"[Agente] Resultado ({accion}): {resultado[:100]}")
        conversation.append(f"[RICK ejecutó {accion}]: {resultado}")

    return "Alcancé el límite de pasos. Tarea incompleta."
