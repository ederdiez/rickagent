from rick.skills.base import Skill, register


class BookmarkGuardarSkill(Skill):
    name = "BOOKMARK_GUARDAR"
    description = "Guarda el directorio actual como marcador"
    prompt_line = 'BOOKMARK_GUARDAR{"nombre":"x"}'
    input_schema = {"type": "object", "properties": {
        "nombre": {"type": "string", "description": "Nombre del marcador"}
    }, "required": ["nombre"]}

    def run(self, executor, params):
        name = params.get("nombre", "").strip()
        if not name:
            return executor.say("Dime un nombre para el marcador.")
        executor.bookmarks[name] = executor.cwd
        executor.save_bookmarks()
        return executor.say(f"Guardé {executor.cwd_pretty()} como '{name}'.")

register(BookmarkGuardarSkill())


class BookmarkBorrarSkill(Skill):
    name = "BOOKMARK_BORRAR"
    description = "Elimina un marcador por nombre"
    prompt_line = 'BOOKMARK_BORRAR{"nombre":"x"}'
    input_schema = {"type": "object", "properties": {
        "nombre": {"type": "string", "description": "Nombre del marcador a eliminar"}
    }, "required": ["nombre"]}

    def run(self, executor, params):
        name = params.get("nombre", "").strip()
        if name in executor.bookmarks:
            del executor.bookmarks[name]
            executor.save_bookmarks()
            return executor.say(f"Marcador '{name}' eliminado.")
        return executor.say(f"No existe el marcador '{name}'.")

register(BookmarkBorrarSkill())


class BookmarkListarSkill(Skill):
    name = "BOOKMARK_LISTAR"
    description = "Lista todos los marcadores guardados"
    prompt_line = 'BOOKMARK_LISTAR{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        if not executor.bookmarks:
            return executor.say("No tienes marcadores guardados.")
        lines = [f"  {k} → {v}" for k, v in executor.bookmarks.items()]
        executor.hablar(f"{len(executor.bookmarks)} marcadores.")
        return "Marcadores:\n" + "\n".join(lines)

register(BookmarkListarSkill())
