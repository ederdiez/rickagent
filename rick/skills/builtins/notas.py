from rick.skills.base import Skill, register


class NotaGuardarSkill(Skill):
    name = "NOTA_GUARDAR"
    description = "Guarda una nota en la memoria persistente"
    prompt_line = 'NOTA_GUARDAR{"titulo":"...","contenido":"..."}'
    input_schema = {"type": "object", "properties": {
        "titulo": {"type": "string", "description": "Título de la nota"},
        "contenido": {"type": "string", "description": "Contenido de la nota"}
    }, "required": ["titulo", "contenido"]}

    def run(self, executor, params):
        return executor.say(executor.notes.save(
            params.get("titulo", "sin título"),
            params.get("contenido", ""))
        )

register(NotaGuardarSkill())


class NotaLeerSkill(Skill):
    name = "NOTA_LEER"
    description = "Lee una nota guardada (omitir título = listar todas)"
    prompt_line = 'NOTA_LEER{"titulo":"..."}'
    input_schema = {"type": "object", "properties": {
        "titulo": {"type": "string", "description": "Título de la nota (omitir = listar todas)"}
    }}

    def run(self, executor, params):
        return executor.say(executor.notes.read(params.get("titulo")))

register(NotaLeerSkill())


class NotaBorrarSkill(Skill):
    name = "NOTA_BORRAR"
    description = "Borra una nota guardada"
    prompt_line = 'NOTA_BORRAR{"titulo":"..."}'
    input_schema = {"type": "object", "properties": {
        "titulo": {"type": "string", "description": "Título de la nota a borrar"}
    }, "required": ["titulo"]}

    def run(self, executor, params):
        return executor.say(executor.notes.delete(params.get("titulo", "")))

register(NotaBorrarSkill())


class RecordatorioSkill(Skill):
    name = "RECORDATORIO"
    description = "Crea un recordatorio con temporizador"
    prompt_line = 'RECORDATORIO{"mensaje":"...","segundos":60}'
    input_schema = {"type": "object", "properties": {
        "mensaje": {"type": "string", "description": "Texto del recordatorio"},
        "segundos": {"type": "integer", "description": "Segundos hasta el recordatorio"}
    }, "required": ["mensaje", "segundos"]}

    def run(self, executor, params):
        return executor.say(executor.reminders.add(
            params.get("mensaje", "Recordatorio"),
            int(params.get("segundos", 60)))
        )

register(RecordatorioSkill())
