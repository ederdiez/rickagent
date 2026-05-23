from rick.skills.base import Skill, register
from rick.system_utils import obtener_clima, traducir


class ClimaSkill(Skill):
    name = "CLIMA"
    description = "Consulta el clima de una ciudad"
    prompt_line = 'CLIMA{"ciudad":"Bilbao"}'
    input_schema = {"type": "object", "properties": {
        "ciudad": {"type": "string", "description": "Nombre de la ciudad"}
    }, "required": ["ciudad"]}

    def run(self, executor, params):
        return executor.say(obtener_clima(params.get("ciudad", "Madrid")))

register(ClimaSkill())


class TraducirSkill(Skill):
    name = "TRADUCIR"
    description = "Traduce texto a otro idioma"
    prompt_line = 'TRADUCIR{"texto":"...","idioma_destino":"es"}'
    input_schema = {"type": "object", "properties": {
        "texto": {"type": "string", "description": "Texto a traducir"},
        "idioma_destino": {"type": "string", "description": "Idioma destino (ej: es, en, fr)"}
    }, "required": ["texto", "idioma_destino"]}

    def run(self, executor, params):
        return executor.say(traducir(
            params.get("texto", ""),
            params.get("idioma_destino", "es"))
        )

register(TraducirSkill())
