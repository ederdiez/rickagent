# Proveedores LLM en RICK

RICK ahora soporta múltiples proveedores de LLMs: locales (Ollama) y cloud (Gemini, DeepSeek, Anthropic).

## Configuración

### 1. Copiar `.env.example` a `.env`
```bash
cp .env.example .env
```

### 2. Editar `config.py`
En `rick/config.py`, cambia:
```python
CFG = {
    "provider": "ollama",  # Cambiar a: "gemini", "deepseek", o "anthropic"
    "model": "qwen3:8b",   # Cambiar según el proveedor
    ...
}
```

### 3. Configurar API keys en `.env`
Edita `.env` con tus API keys reales:
```
GEMINI_API_KEY=tu_key_aqui
DEEPSEEK_API_KEY=tu_key_aqui
ANTHROPIC_API_KEY=tu_key_aqui
```

---

## Proveedores

### Ollama (Local)
**Instalación:** [ollama.ai](https://ollama.ai)  
**Modelos populares:** `qwen3:8b`, `llama3:8b`, `neural-chat:7b`  
**Config:**
```python
"provider": "ollama",
"model": "qwen3:8b",
```

### Gemini (Google)
**API Key:** [Google AI Studio](https://aistudio.google.com)  
**Instalación:**
```bash
pip install google-generativeai
```
**Modelos:**
- `gemini-2.0-flash` (recomendado — rápido)
- `gemini-1.5-pro` (más potente)
- `gemini-2.0-pro` (experimental)

**Config:**
```python
"provider": "gemini",
"model": "gemini-2.0-flash",
```

### DeepSeek
**API Key:** [DeepSeek OpenPlatform](https://platform.deepseek.com)  
**Instalación:**
```bash
pip install openai
```
**Modelos:**
- `deepseek-chat` (estándar)
- `deepseek-reasoner` (razonamiento avanzado)

**Config:**
```python
"provider": "deepseek",
"model": "deepseek-chat",
```

### Anthropic (Claude)
**API Key:** [Anthropic Console](https://console.anthropic.com)  
**Instalación:**
```bash
pip install anthropic
```
**Modelos:**
- `claude-haiku-4-5-20251001` (rápido, gratuito con algunos límites)
- `claude-sonnet-4` (balanceado)
- `claude-opus-4` (más potente)

**Config:**
```python
"provider": "anthropic",
"model": "claude-haiku-4-5-20251001",
```

---

## Instalación de dependencias

Solo instala lo que necesites:

```bash
# Gemini
pip install google-generativeai

# DeepSeek (usa SDK de OpenAI)
pip install openai

# Anthropic
pip install anthropic

# python-dotenv (opcional, para cargar .env)
pip install python-dotenv
```

---

## Prueba rápida

```bash
# Modo push-to-talk (Enter para grabar, Enter para parar)
python -m rick.main --push --no-voice

# Modo realtime (escucha continua)
python -m rick.main --realtime --no-voice

# Con modo debug
python -m rick.main --push --no-voice --debug
```

---

## Troubleshooting

### "SDK no instalada"
El error dice cuál SDK instalar. Ejemplo:
```
Error: SDK de Gemini no instalada. Ejecuta: pip install google-generativeai
```

### "API_KEY no configurada"
Comprueba:
1. Que el `.env` exista y tenga la key
2. Que la key sea válida (no vacía)
3. Que hayas ejecutado en la carpeta del proyecto

### "Proveedor desconocido"
Comprueba que en `config.py` el `provider` sea uno de:
- `"ollama"`
- `"gemini"`
- `"deepseek"`
- `"anthropic"`

### Ollama sin conexión
```bash
# Arranca Ollama en otra terminal
ollama serve

# Luego en otra terminal
python -m rick.main --push --no-voice
```
