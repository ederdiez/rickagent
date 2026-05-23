import os
import shutil

from rick.skills.base import Skill, register


class CrearArchivoSkill(Skill):
    name = "CREAR_ARCHIVO"
    description = "Crea o sobrescribe un archivo con contenido"
    prompt_line = 'CREAR_ARCHIVO{"ruta":"...","contenido":"..."}'
    input_schema = {"type": "object", "properties": {
        "ruta": {"type": "string", "description": "Ruta del archivo"},
        "contenido": {"type": "string", "description": "Contenido del archivo"}
    }, "required": ["ruta", "contenido"]}

    def run(self, executor, params):
        ruta = executor.resolve(params.get("ruta", "~/nuevo.txt"))
        try:
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(params.get("contenido", ""))
            return executor.say(f"Archivo creado: {os.path.basename(ruta)}.")
        except Exception as e:
            return executor.say(f"No pude crear el archivo: {e}")

register(CrearArchivoSkill())


class LeerArchivoSkill(Skill):
    name = "LEER_ARCHIVO"
    description = "Lee el contenido de un archivo"
    prompt_line = 'LEER_ARCHIVO{"ruta":"..."}'
    input_schema = {"type": "object", "properties": {
        "ruta": {"type": "string", "description": "Ruta del archivo"}
    }, "required": ["ruta"]}

    def run(self, executor, params):
        ruta = executor.resolve(params.get("ruta", ""))
        try:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
            resumen = contenido[:600] if contenido else "El archivo está vacío."
            executor.hablar(resumen)
            return contenido
        except FileNotFoundError:
            return executor.say("No encontré ese archivo.")
        except Exception as e:
            return executor.say(f"Error al leer: {e}")

register(LeerArchivoSkill())


class MoverArchivoSkill(Skill):
    name = "MOVER_ARCHIVO"
    description = "Mueve o renombra un archivo"
    prompt_line = 'MOVER_ARCHIVO{"origen":"...","destino":"..."}'
    input_schema = {"type": "object", "properties": {
        "origen": {"type": "string"},
        "destino": {"type": "string"}
    }, "required": ["origen", "destino"]}

    def run(self, executor, params):
        origen = executor.resolve(params.get("origen", ""))
        destino = executor.resolve(params.get("destino", ""))
        try:
            os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
            shutil.move(origen, destino)
            return executor.say(f"Movido a {os.path.basename(destino)}.")
        except Exception as e:
            return executor.say(f"No pude mover: {e}")

register(MoverArchivoSkill())


class CopiarArchivoSkill(Skill):
    name = "COPIAR_ARCHIVO"
    description = "Copia un archivo"
    prompt_line = 'COPIAR_ARCHIVO{"origen":"...","destino":"..."}'
    input_schema = {"type": "object", "properties": {
        "origen": {"type": "string"},
        "destino": {"type": "string"}
    }, "required": ["origen", "destino"]}

    def run(self, executor, params):
        origen = executor.resolve(params.get("origen", ""))
        destino = executor.resolve(params.get("destino", ""))
        try:
            os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
            shutil.copy2(origen, destino)
            return executor.say(f"Copiado a {os.path.basename(destino)}.")
        except Exception as e:
            return executor.say(f"No pude copiar: {e}")

register(CopiarArchivoSkill())


class BorrarArchivoSkill(Skill):
    name = "BORRAR_ARCHIVO"
    description = "Borra un archivo o directorio"
    prompt_line = 'BORRAR_ARCHIVO{"ruta":"..."}'
    input_schema = {"type": "object", "properties": {
        "ruta": {"type": "string", "description": "Ruta del archivo a borrar"}
    }, "required": ["ruta"]}

    def run(self, executor, params):
        ruta = executor.resolve(params.get("ruta", ""))
        try:
            if os.path.isdir(ruta):
                shutil.rmtree(ruta)
            else:
                os.remove(ruta)
            return executor.say(f"Eliminado {os.path.basename(ruta)}.")
        except FileNotFoundError:
            return executor.say("No encontré ese archivo.")
        except Exception as e:
            return executor.say(f"No pude eliminar: {e}")

register(BorrarArchivoSkill())


class CrearCarpetaSkill(Skill):
    name = "CREAR_CARPETA"
    description = "Crea un directorio"
    prompt_line = 'CREAR_CARPETA{"ruta":"..."}'
    input_schema = {"type": "object", "properties": {
        "ruta": {"type": "string", "description": "Ruta de la carpeta a crear"}
    }, "required": ["ruta"]}

    def run(self, executor, params):
        ruta = executor.resolve(params.get("ruta", ""))
        try:
            os.makedirs(ruta, exist_ok=True)
            return executor.say(f"Carpeta creada: {os.path.basename(ruta)}.")
        except Exception as e:
            return executor.say(f"No pude crear la carpeta: {e}")

register(CrearCarpetaSkill())
