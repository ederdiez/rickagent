from rick.skills.base import Skill, register
from rick.system_utils import volumen


class VolumenSubirSkill(Skill):
    name = "VOLUMEN_SUBIR"
    description = "Sube el volumen del sistema"
    prompt_line = 'VOLUMEN_SUBIR{"cantidad":10}'
    input_schema = {"type": "object", "properties": {
        "cantidad": {"type": "integer", "description": "Porcentaje a subir", "default": 10}
    }}

    def run(self, executor, params):
        volumen("subir", params.get("cantidad", 10))
        return None

register(VolumenSubirSkill())


class VolumenBajarSkill(Skill):
    name = "VOLUMEN_BAJAR"
    description = "Baja el volumen del sistema"
    prompt_line = 'VOLUMEN_BAJAR{"cantidad":10}'
    input_schema = {"type": "object", "properties": {
        "cantidad": {"type": "integer", "description": "Porcentaje a bajar", "default": 10}
    }}

    def run(self, executor, params):
        volumen("bajar", params.get("cantidad", 10))
        return None

register(VolumenBajarSkill())


class VolumenMuteSkill(Skill):
    name = "VOLUMEN_MUTE"
    description = "Silencia o reactiva el audio"
    prompt_line = 'VOLUMEN_MUTE{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        volumen("mute")
        return None

register(VolumenMuteSkill())
