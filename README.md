# RICK — Asistente de IA Conversacional Agentic

Un asistente de voz inteligente con capacidades de agente autónomo, soporte multi-proveedor LLM y ejecución de acciones del sistema.

## ✨ Características

- 🎤 **Reconocimiento de voz en tiempo real** — Whisper + VAD inteligente (detección de silencio)
- ⌨️ **Input por teclado** — `/cd`, `/ls` y texto libre en el mismo prompt
- 🧠 **Agente agentic** — Loop de razonamiento y ejecución de tareas complejas
- 🌐 **Multi-proveedor LLM** — DeepSeek, Anthropic Claude, Google Gemini, Ollama local
- 🔊 **Síntesis de voz** — pyttsx3 con fallback a espeak
- 💾 **Memoria conversacional** — Contexto persistente multi-turno
- 📝 **Notas y recordatorios** — Almacenamiento en tiempo real
- 📂 **Navegación inteligente** — Búsqueda fuzzy + case-insensitive + bookmarks
- ⚡ **Ejecución de acciones** — Control del sistema, archivos, aplicaciones
- 🔌 **Arquitectura modular** — Fácil de extender y personalizar

## 🚀 Instalación Rápida

### Requisitos
- Python 3.10+
- Micrófono y altavoces
- (Opcional) CUDA para Whisper más rápido

### Paso 1: Clonar e instalar dependencias

```bash
git clone https://github.com/tu-usuario/rick.git
cd rick
pip install -r requirements.txt
```

### Paso 2: Configurar API keys (opcional)

Copiar `.env.example` a `.env` y agregar tus claves:

```bash
cp .env.example .env
nano .env
```

**Proveedores soportados:**
- `DEEPSEEK_API_KEY` — [DeepSeek API](https://platform.deepseek.com/) (por defecto)
- `ANTHROPIC_API_KEY` — [Claude API](https://console.anthropic.com/)
- `GEMINI_API_KEY` — [Google AI Studio](https://ai.google.dev/)
- `OLLAMA` — Local (sin API key)

### Paso 3: Instalar herramientas del sistema

**Linux (Arch):**
```bash
sudo pacman -S wtype xdotool grim espeak ffmpeg
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install wtype xdotool grim espeak ffmpeg
```

## 💬 Uso

### Modos de Operación

```bash
# Realtime (por defecto) — Escucha continua + input teclado
python jarvis.py --realtime

# Push-to-talk — t + Enter para grabar, /cd, /ls o texto libre
python jarvis.py --push
```

### Input por teclado (ambos modos)

En cualquier momento puedes escribir en la terminal:

| Input | Qué hace |
|-------|----------|
| `t` (o Enter) | Empieza a grabar voz (solo push) |
| `/cd Desktop` | Navega al directorio (búsqueda fuzzy automática) |
| `/ls` | Lista el directorio actual |
| `abre firefox` | Pasa por el LLM como lenguaje natural |
| `ve a descargas` | Pasa por el LLM, que ejecutará IR |

### Opciones Útiles

```bash
# Modo texto (sin síntesis de voz)
python jarvis.py --no-voice --realtime

# Con logs detallados
python jarvis.py --realtime --debug

# Listar dispositivos de audio
python jarvis.py --list-mics

# Ver historial de comandos
python jarvis.py --history

# Cambiar proveedor LLM
python jarvis.py --provider gemini --realtime
```

## 🔄 Cómo Funciona el Agente

1. **Escucha** tu comando en voz o texto
2. **Evalúa** si es tarea simple (respuesta directa) o compleja (requiere agente autónomo)
3. **Razona** sobre qué acciones tomar (agentic loop)
4. **Ejecuta** acciones del sistema (abrir apps, crear archivos, navegar, etc.)
5. **Responde** en voz o texto

**Ejemplo:**
```
Tú:  "Rick, abre Spotify y ponle música de lo-fi"
Rick: (abre Spotify) → (busca lo-fi) → "Puesto, disfruta 🎵"
```

## 🎮 Acciones Disponibles

RICK ejecuta acciones JSON respondidas por el LLM:

| Categoría | Acciones |
|-----------|----------|
| **Sistema** | `ABRIR_APP`, `EJECUTAR_CMD`, `SISTEMA_INFO`, `PROCESO_INFO`, `APAGAR`, `REINICIAR` |
| **Web** | `ABRIR_URL`, `BUSCAR_WEB`, `CLIMA`, `TRADUCIR`, `MUSICA` |
| **Audio** | `VOLUMEN_SUBIR`, `VOLUMEN_BAJAR`, `VOLUMEN_MUTE` |
| **Teclado** | `ESCRIBIR`, `ATAJO`, `NUEVA_PESTANA`, `CERRAR_VENTANA`, `MINIMIZAR`, `MAXIMIZAR` |
| **Archivos** | `CREAR_ARCHIVO`, `LEER_ARCHIVO`, `BORRAR_ARCHIVO`, `MOVER_ARCHIVO`, `COPIAR_ARCHIVO`, `CREAR_CARPETA`, `RENOMBRAR`, `BUSCAR_ARCHIVO` |
| **Navegación** | `IR`, `PWD`, `LISTAR_DIR`, `INFO_DIR`, `LEER_DIR_RECURSIVO`, `BUSCAR_EN_ARCHIVOS` |
| **Marcadores** | `BOOKMARK_GUARDAR`, `BOOKMARK_BORRAR`, `BOOKMARK_LISTAR` |
| **Clipboard** | `CLIPBOARD_LEER`, `CLIPBOARD_ESCRIBIR` |
| **Notas** | `NOTA_GUARDAR`, `NOTA_LEER`, `NOTA_BORRAR` |
| **Recordatorios** | `RECORDATORIO` (timer en background) |
| **Agente** | `EJECUTAR_PYTHON`, `ESCRIBIR_Y_EJECUTAR`, `GIT_CMD` |

### Navegación Inteligente

`IR` busca automáticamente el directorio en múltiples niveles si no existe exactamente:

1. **Case-insensitive** — `IR {"directorio":"fotos"}` encuentra `Fotos`
2. **Fuzzy match** — `IR {"directorio":"docu"}` encuentra `Documentos`
3. **Búsqueda en home** — Si no está en el CWD, busca en `~`
4. **Bookmarks** — Nombres cortos para rutas frecuentes

## ⚙️ Configuración

Editar `rick/config.py`:

```python
{
    "provider": "deepseek",            # "deepseek" | "anthropic" | "gemini" | "ollama"
    "model": "deepseek-chat",          # Modelo según proveedor
    "whisper_model": "small",          # tiny | base | small | medium | large
    "language": "es",                  # Idioma Whisper
    "voice_rate": 190,                 # Velocidad de voz (wpm)
    "voice_volume": 1.0,               # Volumen (0.0 - 1.0)
    "agent_enabled": True,             # Habilitar agente agentic
    "agent_max_steps": 20,             # Pasos máx antes de timeout
    "agent_timeout_s": 300,            # Timeout en segundos
}
```

## 📁 Estructura del Proyecto

```
rick/
├── __init__.py              # Metadata del package
├── config.py                # Configuración global + prompts
├── main.py                  # JARVIS class + punto de entrada
├── audio.py                 # VADRecorder + Whisper integration
├── llm.py                   # LLM abstraction (multi-proveedor)
├── tts.py                   # Text-to-Speech (pyttsx3 + espeak)
├── memory.py                # ConversationMemory + NotesManager
├── reminders.py             # ReminderManager
├── executor.py              # ActionExecutor (ejecuta acciones)
├── agent.py                 # Agente agentic + loop
├── system_utils.py          # Utilidades del sistema
└── logging_setup.py         # Sistema de logs con colores

jarvis.py                    # Punto de entrada ejecutable
requirements.txt             # Dependencias Python
.env.example                 # Template para API keys

~/.rick/bookmarks.json       # Marcadores de directorios
~/.rick/rick.log             # Log en modo daemon
```

## 🔧 Configuración Avanzada

### Cambiar proveedor LLM por defecto

En `rick/config.py`:

```python
"provider": "anthropic",
"model": "claude-haiku-4-5",
```

### Usar Ollama local (sin internet)

```python
"provider": "ollama",
"model": "qwen3:8b",            # o llama3, mistral, etc
"ollama_url": "http://localhost:11434/api/generate",
```

Iniciar Ollama:
```bash
ollama serve
```

### Optimizar para baja latencia

```python
"whisper_model": "tiny",          # Más rápido, menos preciso
"agent_max_steps": 5,             # Menos pasos de razonamiento
"max_record_s": 10,               # Timeout de grabación
```

## 🐛 Troubleshooting

**"ModuleNotFoundError: No module named 'X'"**
```bash
pip install -r requirements.txt
```

**Micrófono no funciona**
```bash
python jarvis.py --list-mics
```

**Llama pero no responde**
- Verificar API key en `.env`
- Revisar logs: `python jarvis.py --realtime --debug`
- Probar con Ollama local

**Sin sonido (TTS)**
```bash
sudo pacman -S espeak-ng  # Arch
sudo apt install espeak-ng  # Debian/Ubuntu
```

**Wayland no funciona**
```bash
which wtype
sudo pacman -S wtype  # Arch
sudo apt install wtype  # Debian
```

## 📊 Comparativa de Modos

| Modo | Activación | Input | Ventajas |
|------|------------|-------|----------|
| **realtime** | VAD automático | Voz + teclado | Natural, conversacional |
| **push-to-talk** | t + Enter | Voz + teclado + comandos | Control total, híbrido |

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Consulta [CONTRIBUTING.md](CONTRIBUTING.md).

## 📝 Licencia

MIT. Ver [LICENSE](LICENSE).

## 👤 Autor

Creado por **Eder** como proyecto personal de asistente IA conversacional.

## ⭐ Reconocimientos

- [OpenAI Whisper](https://github.com/openai/whisper)
- [DeepSeek](https://www.deepseek.com/)
- [Anthropic Claude](https://www.anthropic.com/)
- [Google Gemini](https://ai.google.dev/)
- Comunidad open-source de Python

---

**¿Tienes preguntas?** Abre un [issue](https://github.com/tu-usuario/rick/issues) o consulta [AGENTIC_GUIDE.md](AGENTIC_GUIDE.md).
