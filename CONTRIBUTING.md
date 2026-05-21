# Guía de Contribución

¡Gracias por tu interés en contribuir a RICK! Este documento te ayudará a entender cómo puedes aportar al proyecto.

## Cómo Empezar

### 1. Fork y Clone

```bash
# Fork el repo en GitHub
# Luego clona tu fork
git clone https://github.com/TU-USUARIO/rick.git
cd rick
```

### 2. Crea una rama para tu feature

```bash
git checkout -b feature/tu-feature-nombre
```

## Tipos de Contribuciones Bienvenidas

### 🐛 Reportar Bugs

1. Abre un [issue](https://github.com/tu-usuario/rick/issues)
2. Incluye:
   - Tu SO y versión de Python (`python --version`)
   - Modelo LLM que usas
   - Pasos para reproducir
   - Logs si es posible (`python jarvis.py --debug`)
   - Comportamiento esperado vs actual

### ✨ Sugerir Features

1. Abre un [issue](https://github.com/tu-usuario/rick/issues) con etiqueta `enhancement`
2. Describe el caso de uso
3. Explica por qué es útil

### 💻 Código

- Fixes de bugs
- Nuevas acciones en el executor
- Soporte para nuevos proveedores LLM
- Mejoras de rendimiento
- Documentación

## Flujo de Desarrollo

### Configurar entorno

```bash
# Crear venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o en Windows: venv\Scripts\activate

# Instalar dependencias + dev tools (opcional)
pip install -r requirements.txt
pip install black flake8 pytest  # dev tools
```

### Hacer cambios

1. Edita los archivos en `rick/`
2. Prueba localmente: `python jarvis.py --realtime --debug`
3. Si añades acción nueva, actualiza `executor.py`

### Code Style

- Usa nombres descriptivos en español para funciones/variables del dominio
- Imports al inicio del archivo
- Máximo 100 caracteres de línea (flexible para strings largos)
- Docstrings para funciones públicas

Ejemplo:
```python
def procesar_comando(texto: str) -> dict:
    """Procesa comando en texto y retorna acción JSON."""
    # ...
```

### Testing

```bash
# Prueba manual con logs
python jarvis.py --realtime --debug

# Si hay tests (pytest)
pytest tests/
```

## Workflow para hacer un PR

1. **Commit messages claros:**
   ```
   git commit -m "Agregar soporte X" -m "Descripción detallada si es necesario"
   ```

2. **Push a tu fork:**
   ```bash
   git push origin feature/tu-feature-nombre
   ```

3. **Abre un Pull Request en GitHub:**
   - Título claro (ej: "Agregar acción EMAIL al executor")
   - Descripción con contexto
   - Referencia a issue relacionado (#123)

4. **Espera review:**
   - El maintainer revisará
   - Puede haber cambios solicitados
   - Una vez aprobado, se mergea

## Checklist Antes de hacer PR

- [ ] Código funciona localmente
- [ ] No hay imports no usados
- [ ] Actualizaste documentación si corresponde
- [ ] Commit messages son claros
- [ ] No incluiste archivos temporales (`.pyc`, `__pycache__`)
- [ ] Tu rama está actualizada con `main`

## Estructura para agregar una nueva acción

1. Define en `executor.py`:
```python
def action_NOMBRE(self, params):
    """Descripción de qué hace."""
    # ... implementación
```

2. Registra en `self.acciones` dict:
```python
"NOMBRE": self.action_NOMBRE,
```

3. Documenta en README.md

4. Prueba:
```bash
# Pedir a RICK que ejecute la acción
python jarvis.py --realtime --no-voice
# > "haz la acción X"
```

## Para agregar nuevo proveedor LLM

1. Edita `llm.py`:
```python
def _proveedor_nuevo(prompt, context):
    # implementación usando API del proveedor
    return respuesta_formateada
```

2. Actualiza `config.py` con settings nuevos

3. Documenta en README.md en sección de proveedores

4. Prueba:
```bash
python jarvis.py --provider nuevo --realtime
```

## Preguntas?

- Abre un [discussion](https://github.com/tu-usuario/rick/discussions) para preguntas
- Para bugs, abre un [issue](https://github.com/tu-usuario/rick/issues)

## Código de Conducta

Sé respetuoso, inclusivo y constructivo. Queremos una comunidad amigable.

---

¡Gracias por contribuir! 🎉
