# RICK — Asistente de IA Conversacional Agentic

Un asistente de voz inteligente con capacidades de agente autónomo, soporte multi-proveedor LLM y ejecución de acciones del sistema.

## ✨ Características

- 🎤 **Reconocimiento de voz en tiempo real** — Whisper + VAD inteligente (detección de silencio)
- 🧠 **Agente agentic** — Loop de razonamiento y ejecución de tareas complejas
- 🌐 **Multi-proveedor LLM** — Anthropic Claude, Google Gemini, DeepSeek, Ollama local
- 🔊 **Síntesis de voz** — pyttsx3 con fallback a espeak
- 💾 **Memoria conversacional** — Contexto persistente multi-turno
- 📝 **Notas y recordatorios** — Almacenamiento en tiempo real
- ⚡ **Ejecución de acciones** — Control del sistema, archivos, aplicaciones
- 🔌 **Arquitectura modular** — Fácil de extender y personalizar
- 🗣️ **Totalmente en español** — Interfaz y respuestas en ES

## 🚀 Instalación Rápida

### Requisitos
- Python 3.9+
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
# Editar .env con tus API keys
nano .env
```

**Proveedores soportados:**
- `ANTHROPIC_API_KEY` — [Claude API](https://console.anthropic.com/)
- `GEMINI_API_KEY` — [Google AI Studio](https://ai.google.dev/)
- `DEEPSEEK_API_KEY` — [DeepSeek API](https://platform.deepseek.com/)
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
# Realtime (recomendado) — Escucha continua, responde automáticamente
python jarvis.py --realtime

# Push-to-talk — Presiona Enter para grabar
python jarvis.py --push
```

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
2. **Evalúa** si es una tarea simple (respuesta directa) o compleja (requiere acciones)
3. **Razona** sobre qué acciones tomar (agentic loop)
4. **Ejecuta** acciones del sistema (abrir apps, crear archivos, etc.)
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
| **Sistema** | `ABRIR_APP`, `EJECUTAR_CMD`, `SISTEMA_INFO`, `PROCESO_INFO` |
| **Web** | `ABRIR_URL`, `BUSCAR_WEB` |
| **Audio** | `VOLUMEN_SUBIR`, `VOLUMEN_BAJAR`, `VOLUMEN_MUTE` |
| **Teclado** | `ESCRIBIR`, `ATAJO`, `NUEVA_PESTANA`, `CERRAR_VENTANA` |
| **Archivos** | `CREAR_ARCHIVO`, `LEER_ARCHIVO`, `BORRAR_ARCHIVO`, `MOVER_ARCHIVO`, `COPIAR_ARCHIVO`, `CREAR_CARPETA`, `RENOMBRAR`, `BUSCAR_ARCHIVO` |
| **Navegación** | `IR`, `PWD`, `LISTAR_DIR`, `INFO_DIR`, `LEER_DIR_RECURSIVO` |
| **Marcadores** | `IR --save nombre`, `IR --list`, `IR --delete nombre`, `IR nombre` (atajo) |
| **Pila** | `IR --back` / `IR -` (vuelve al dir anterior), `IR --stack` (historial) |
| **Clipboard** | `CLIPBOARD_LEER`, `CLIPBOARD_ESCRIBIR` |
| **Notas** | `NOTA_GUARDAR`, `NOTA_LEER`, `NOTA_BORRAR` |
| **Recordatorios** | `RECORDATORIO` (timer en background) |

## ⚙️ Configuración

Editar `rick/config.py`:

```python
{
    "provider": "anthropic",           # "anthropic" | "gemini" | "deepseek" | "ollama"
    "model": "claude-haiku-4-5",       # Modelo según proveedor
    "whisper_model": "small",          # tiny | base | small | medium | large
    "language": "es",                  # Idioma (es | en | fr | ...)
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

~/.rick/bookmarks.json       # Marcadores de directorios (se crea automáticamente)
~/.rick/rick.log             # Log en modo daemon
```

## 🔧 Configuración Avanzada

### Cambiar proveedor LLM por defecto

En `rick/config.py`:

```python
"provider": "gemini",        # Cambiar a Gemini
"model": "gemini-2.0-flash",
```

### Usar Ollama local (sin internet)

```python
"provider": "ollama",
"model": "llama2",           # o qwen, mistral, etc
"ollama_url": "http://localhost:11434/api/generate",
```

Luego iniciar Ollama:
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
# Luego editar config.py con el device ID
```

**Llama pero no responde**
- Verificar API key en `.env`: `echo $ANTHROPIC_API_KEY`
- Revisar logs: `python jarvis.py --realtime --debug`
- Probar con Ollama local (sin internet)

**Sin sonido (TTS)**
```bash
# Instalar espeak como fallback
sudo pacman -S espeak-ng  # Arch
sudo apt install espeak-ng  # Debian/Ubuntu
```

**Wayland no funciona**
```bash
# Verificar wtype
which wtype
# Instalar: sudo pacman -S wtype  (Arch)  |  sudo apt install wtype (Debian)
```

## 📊 Comparativa de Modos

| Modo | Activación | Ventajas | Desventajas |
|------|------------|----------|------------|
| **realtime** | VAD automático | Natural, conversacional | Falsos positivos posibles |
| **push-to-talk** | Presiona Enter | Control total | Manual, menos fluido |

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repo
2. Crea una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'Add amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para más detalles.

## 📝 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para detalles.

## 👤 Autor

Creado por **Eder** como proyecto personal de asistente IA conversacional.

## ⭐ Reconocimientos

- [OpenAI Whisper](https://github.com/openai/whisper) — Speech-to-text
- [Anthropic Claude](https://www.anthropic.com/) — LLM principal
- [Google Gemini](https://ai.google.dev/) — LLM alternativo
- [DeepSeek](https://www.deepseek.com/) — LLM alternativo
- Comunidad open-source de Python

---

**¿Tienes preguntas?** Abre un [issue](https://github.com/tu-usuario/rick/issues) o consulta la [documentación del agente](AGENTIC_GUIDE.md).
