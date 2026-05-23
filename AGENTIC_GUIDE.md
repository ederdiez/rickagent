# Rick: Guía del Sistema Agentic

## Descripción General

Rick es un **agente autónomo con capacidad de programación**. El sistema detecta automáticamente si una tarea es compleja y activa el modo agente cuando es necesario.

## Características Principales

### 1. **Detección Inteligente de Tareas**
El sistema clasifica automáticamente cada comando:
- **Tareas simples** (modo reactivo): "abre firefox", "cuál es la hora"
- **Tareas complejas** (modo agente): "escribe un script que...", "genera código para...", "navega a proyectos/src"
- **Navegación**: "ve a", "busca carpeta", "encuentra el directorio" también activan el agente

### 2. **Agentic Loop**
El agente funciona con todos los proveedores:
- **Anthropic**: usa tool use nativo (API de herramientas)
- **DeepSeek, Gemini, Ollama**: parsing JSON con descripción de herramientas en el prompt
- Máximo 20 pasos por tarea (configurable)
- Timeout global de 5 minutos

### 3. **Herramientas Disponibles**

#### Ejecución de Código
- **EJECUTAR_PYTHON** — Ejecuta código Python inline, captura stdout/stderr
- **ESCRIBIR_Y_EJECUTAR** — Escribe un script a /tmp y lo ejecuta (Python, bash, etc.)
- **EJECUTAR_CMD** — Ejecuta comandos shell arbitrarios

#### Manipulación de Archivos
- **CREAR_ARCHIVO** / **LEER_ARCHIVO**
- **MOVER_ARCHIVO** / **COPIAR_ARCHIVO** / **BORRAR_ARCHIVO**
- **CREAR_CARPETA** / **LISTAR_DIR** / **LEER_DIR_RECURSIVO**
- **BUSCAR_ARCHIVO** / **BUSCAR_EN_ARCHIVOS**

#### Control de Versiones
- **GIT_CMD** — Comandos git seguros (status, log, diff, add, commit, push, pull, etc.)

#### Navegación
- **IR** — Navegación con búsqueda fuzzy automática (case-insensitive + fuzzy match + home)
- **PWD** / **INFO_DIR** / **LISTAR_DIR** / **LEER_DIR_RECURSIVO**

#### Sistema
- **SISTEMA_INFO** / **ABRIR_URL** / **SCREENSHOT**

## Ejemplos de Uso

### Ejemplo 1: Generar y Ejecutar Código
```bash
$ python jarvis.py --push
[~] $ escribe un script Python que calcula los primeros 10 números de Fibonacci

[RICK]
Entendido. Déjame trabajar en eso.
Aquí está el código de Fibonacci. Salida: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34
```

### Ejemplo 2: Navegación Inteligente
```bash
[~] $ ve a descargas
[RICK navega automáticamente a ~/Descargas]
[~/Descargas] $ ve a fotos
[RICK encuentra "Fotos" aunque se lo hayas dicho en minúsculas]
```

### Ejemplo 3: Analizar Proyecto
```bash
[~] $ explora el proyecto y busca archivos .py
[RICK]
Entendido. Déjame trabajar en eso.
Encontré 24 archivos Python en el proyecto.
```

## Arquitectura del Sistema

```
process_command(texto)
    |
    +--[¿Es tarea compleja?]
         |
         | NO → Modo Reactivo (legacy)
         |      consultar_llm() → acción única
         |
         | SÍ → run_agent_task()
              |
              +--[Agentic Loop]
                  - loop (max 20 pasos):
                    * LLM call con herramientas
                    * ejecuta herramienta, inyecta resultado
                    * si listo: extrae respuesta final
                  - return: resultado a TTS
```

## Configuración

Todas las opciones en `rick/config.py`:

```python
CFG["provider"]            = "deepseek"       # deepseek | anthropic | gemini | ollama
CFG["agent_enabled"]       = True             # Activar/desactivar
CFG["agent_model"]         = "deepseek-v4-flash"
CFG["agent_max_steps"]     = 20               # Máximo de pasos
CFG["agent_timeout_s"]     = 300              # Timeout global (5 min)
```

### Usar DeepSeek (por defecto)

```python
# Ya está configurado por defecto
export DEEPSEEK_API_KEY="sk-..."
python jarvis.py --realtime
```

### Usar Anthropic (tool use nativo, más robusto)

```python
# En config.py:
CFG["provider"] = "anthropic"
CFG["model"] = "claude-haiku-4-5"

export ANTHROPIC_API_KEY="sk-ant-..."
python jarvis.py --realtime
```

### Usar Ollama Local (gratis)

```bash
ollama serve
ollama pull qwen3:8b

# En config.py:
CFG["provider"] = "ollama"
CFG["model"] = "qwen3:8b"

python jarvis.py --realtime
```

## Cambios Técnicos

### Archivos Modificados
- **config.py** — Opciones de agente + SYSTEM_PROMPT optimizado (40% más corto)
- **llm.py** — `consultar_llm()` acepta `system_prompt`, `raw`, `model`, `max_tokens`
- **executor.py** — `_ir()` con búsqueda fuzzy 3 niveles, `BOOKMARK_*` como acciones separadas, helper `_say()`
- **main.py** — Input por teclado (`/cd`, `/ls`, texto libre), `_handle_command()`, `_check_stdin()`
- **agent.py** — Eliminados providers duplicados, ahora usa `consultar_llm()` directamente

### Archivos Nuevos
- **agent.py** — Núcleo del agentic loop (~300 líneas)
  - `AGENT_TOOLS` — 20+ tool definitions
  - `_is_complex_task()` — Clasificador heurístico (incluye navegación)
  - `run_agent_task()` — Enruta a Anthropic (nativo) o genérico (JSON)

## Seguridad

- **Comandos shell**: El agente puede ejecutar cualquier comando. Limitado por permisos del usuario.
- **Rutas sensibles**: Bloqueadas por `_es_ruta_segura()` (`/etc`, `/proc`, `.ssh`, etc.)
- **Git**: Whitelist de subcomandos seguros

## Comparativa de Proveedores

| Proveedor | Ventajas | Desventajas |
|-----------|----------|-------------|
| **DeepSeek** | Muy económico, buena calidad | Latencia de red, parsing manual |
| **Anthropic** | Tool use nativo, más robusto | Requiere API key, más caro |
| **Ollama (local)** | Gratis, privado, sin latencia | Modelos menos capaces |
| **Gemini** | Buena relación calidad/precio | Latencia de red |

## Troubleshooting

### El agente entra en bucle infinito
- Aumenta `agent_timeout_s` si es legítimo
- Reduce `agent_max_steps` si es un patrón espurio

### Modo reactivo no responde bien
- Aumenta `max_tokens_reactive` en config (default 6144)

## Debugging

```bash
python jarvis.py --realtime --debug
```

Todos los pasos del agente se registran con prefix `[Agente]`.

---

**Rick ahora es un programador autónomo. Úsalo bien.**
