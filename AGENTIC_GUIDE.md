# Rick: Guía del Sistema Agentic

## Descripción General

Rick ha sido transformado de un asistente de voz reactivo a un **agente autónomo con capacidad de programación**. El sistema detecta automáticamente si una tarea es compleja y activa el modo agente cuando es necesario.

## Características Principales

### 1. **Detección Inteligente de Tareas**
El sistema clasifica automáticamente cada comando:
- **Tareas simples** (modo reactivo): "abre firefox", "cuál es la hora"
- **Tareas complejas** (modo agente): "escribe un script que...", "genera código para..."

### 2. **Agentic Loop con Tool Use Nativo**
El agente utiliza la API de Anthropic con tool use nativo:
- El LLM decide qué herramientas usar en cada paso
- Los resultados se inyectan automáticamente en el contexto
- Máximo 20 pasos por tarea (configurable)
- Timeout global de 5 minutos

### 3. **Herramientas Disponibles**

#### Ejecución de Código
- **EJECUTAR_PYTHON** — Ejecuta código Python inline, captura stdout/stderr
- **ESCRIBIR_Y_EJECUTAR** — Escribe un script a /tmp y lo ejecuta (Python, bash, etc.)
- **EJECUTAR_CMD** — Ejecuta comandos shell arbitrarios

#### Manipulación de Archivos
- **CREAR_ARCHIVO** — Crea o sobreescribe un archivo
- **LEER_ARCHIVO** — Lee el contenido de un archivo
- **MOVER_ARCHIVO** / **COPIAR_ARCHIVO** / **BORRAR_ARCHIVO**
- **CREAR_CARPETA** / **LISTAR_DIR** / **LEER_DIR_RECURSIVO**
- **BUSCAR_ARCHIVO** / **BUSCAR_EN_ARCHIVOS** — Búsqueda en proyectos

#### Control de Versiones
- **GIT_CMD** — Comandos git seguros (status, log, diff, add, commit, push, pull, etc.)

#### Sistema
- **SISTEMA_INFO** — Información del sistema (CPU, RAM, disco)
- **ABRIR_URL** — Abre URLs en el navegador
- **SCREENSHOT** — Toma captura de pantalla

## Ejemplos de Uso

### Ejemplo 1: Generar y Ejecutar Código
```bash
$ rick
> "Escribe un script Python que calcula los primeros 10 números de Fibonacci"

[RICK]
Entendido. Déjame trabajar en eso.
[Agente procesa...]
Aquí está el código de Fibonacci. Salida: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34
```

### Ejemplo 2: Analizar Proyecto
```bash
$ rick
> "Explora el directorio ~/proyectos/backend y busca todos los archivos .py"

[RICK]
Entendido. Déjame trabajar en eso.
[Agente examina estructura...]
Encontré 24 archivos Python en el proyecto. Los principales están en src/ y tests/.
```

### Ejemplo 3: Crear y Validar Código
```bash
$ rick
> "Crea una función Python que valida emails y pruébala con test_case"

[RICK]
Entendido. Déjame trabajar en eso.
[Agente escribe, ejecuta, valida...]
Función creada y validada. Todos los tests pasaron correctamente.
```

## Arquitectura del Sistema

```
processo_command(texto)
    |
    +--[¿Es tarea compleja?]
         |
         | NO → Modo Reactivo (legacy)
         |      Una acción, respuesta inmediata
         |
         | SÍ → run_agent_task() ← NUEVO
              |
              +--[Agentic Loop]
                  - init: messages = [user_input]
                  - loop (max 20 pasos):
                    * LLM call con tools
                    * si tool_use: ejecuta, inyecta resultado
                    * si end_turn: extrae respuesta final
                  - return: resultado a TTS
```

## Configuración

Todas las opciones están en `rick/config.py`:

```python
# Modo agente (funciona con TODOS los proveedores)
CFG["provider"]            = "anthropic"      # o "ollama", "gemini", "deepseek"
CFG["agent_enabled"]       = True              # Activar/desactivar
CFG["agent_model"]         = "claude-haiku-4-5" # o "qwen3:8b" para Ollama
CFG["agent_max_steps"]     = 20               # Máximo de pasos
CFG["agent_timeout_s"]     = 300              # Timeout global (5 min)
CFG["max_tokens_reactive"] = 1024             # Tokens en modo reactivo
```

### Usar Ollama Local (Gratis)

```bash
# Terminal 1: Inicia Ollama
ollama serve

# Terminal 2: Descarga un modelo (ej: Qwen 8B)
ollama pull qwen2:7b

# Terminal 3: Configura Rick
export OLLAMA_URL="http://localhost:11434/api/generate"
cat > ~/.env << 'EOF'
PROVIDER=ollama
MODEL=qwen2:7b
AGENT_ENABLED=true
EOF

python -m rick.main --realtime
```

### Usar Anthropic (Recomendado para Calidad)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Rick detecta Anthropic automáticamente y usa tool use nativo
python -m rick.main --realtime
```

### Usar Gemini o DeepSeek

```bash
# Gemini
export GEMINI_API_KEY="AIza..."
export PROVIDER=gemini

# DeepSeek
export DEEPSEEK_API_KEY="sk-..."
export PROVIDER=deepseek

python -m rick.main --realtime
```

## Cambios Técnicos

### Archivos Modificados
- **config.py** — Agregadas opciones de agente + AGENT_SYSTEM_PROMPT
- **executor.py** — Nuevo método `run_silent()`, 5 nuevos handlers de programación
- **llm.py** — max_tokens mejorado
- **memory.py** — Nuevo método `build_messages()` para Anthropic API
- **main.py** — Integración de modo dual

### Archivos Nuevos
- **agent.py** — Núcleo del agentic loop (600+ líneas)
  - `AGENT_TOOLS` — 17 tool definitions
  - `_is_complex_task()` — Clasificador heurístico
  - `run_agent_task()` — Función principal (enruta a proveedor)
  - `_run_agent_anthropic()` — Loop con tool use nativo
  - `_run_agent_generic()` — Loop con JSON parsing (Ollama/Gemini/DeepSeek)
  - `_call_ollama()`, `_call_gemini()`, `_call_deepseek()` — Adaptadores de API

## Seguridad

- **Comandos shell**: El agente puede ejecutar cualquier comando. Está limitado por permisos del usuario.
- **Edición de archivos**: El agente puede crear/modificar archivos en el home del usuario.
- **Git**: Whitelist de subcomandos seguros (no permite `git reset --hard`, etc.)
- **Inteligencia Claude**: Claude tiene incentivo de no destruir el sistema del usuario.

## Comparativa de Proveedores en Modo Agente

| Proveedor | Ventajas | Desventajas | Mejor para |
|-----------|----------|-------------|-----------|
| **Anthropic** | Tool use nativo, mejor razonamiento, más robusto | Requiere API key, costo por token | Tareas complejas, producción |
| **Ollama (local)** | Gratis, sin API, privado, sin latencia | Modelos menos capaces, JSON parsing manual | Desarrollo local, sin conexión |
| **Gemini** | Buena relación calidad/precio | Latencia de red, parsing manual | Balance costo-calidad |
| **DeepSeek** | Muy económico, buena calidad | Latencia, parsing manual | Presupuesto limitado |

**Recomendación:** 
- Desarrollo local → Ollama (qwen2:7b o llama2)
- Producción → Anthropic Claude
- Budget → DeepSeek o Gemini

## Limitaciones y Futuro

### v1 (Actual - Actualizado)
- ✅ Agente programación básica (Python, shell)
- ✅ Análisis de proyectos
- ✅ Integración git
- ✅ Modo reactivo intacto
- ✅ **NUEVO:** Soporte multi-proveedor (Anthropic, Ollama, Gemini, DeepSeek)

### v2 (Próximo)
- 📋 Integración con Sophos/IDE
- 📋 Depuración automática con debuggers
- 📋 Ejecución en sandboxes/contenedores
- 📋 Memoria long-term entre sesiones
- 📋 Aprendizaje de preferencias del usuario

## Troubleshooting

### "No tengo ANTHROPIC_API_KEY"
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python -m rick.main --realtime
```

### El agente entra en bucle infinito
- Aumenta `agent_timeout_s` en config si es legítimo (grandes clones de git)
- O reduce `agent_max_steps` si es un patrón espurio

### Mode reactivo no responde bien
- Aumenta `max_tokens_reactive` en config (era 600, ahora 1024)
- O cambia el modelo a Sonnet: `CFG["model"] = "claude-sonnet-4-6"`

## Cambios Visibles para el Usuario

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| "abre firefox" | ✓ Instantáneo | ✓ Igual |
| "escribe un script" | ✗ No disponible | ✓ Agente lo hace |
| Calidad respuestas | 600 tokens | 1024 tokens |
| Modo razonamiento | N/A | Multi-paso inteligente |

## Debugging

Activar logs detallados:
```bash
export RUST_LOG=debug
python -m rick.main --realtime
```

Todos los pasos del agente se registran con prefix `[Agente]`.

---

**Rick ahora es un programador autónomo. Úsalo bien. 🤖**
