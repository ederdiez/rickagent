from rick.skills.base import Skill, register
from rick.system_utils import clipboard_leer, clipboard_escribir


class ClipboardLeerSkill(Skill):
    name = "CLIPBOARD_LEER"
    description = "Lee el contenido del portapapeles"
    prompt_line = 'CLIPBOARD_LEER{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        contenido = clipboard_leer()
        executor.hablar(contenido[:400])
        return contenido

register(ClipboardLeerSkill())


class ClipboardEscribirSkill(Skill):
    name = "CLIPBOARD_ESCRIBIR"
    description = "Escribe texto en el portapapeles"
    prompt_line = 'CLIPBOARD_ESCRIBIR{"texto":"..."}'
    input_schema = {"type": "object", "properties": {
        "texto": {"type": "string", "description": "Texto a copiar"}
    }, "required": ["texto"]}

    def run(self, executor, params):
        result = clipboard_escribir(params.get("texto", ""))
        executor.hablar(result)
        return None

register(ClipboardEscribirSkill())
