"""
Ejemplo de skill externa.
Copia este archivo a rick/skills/mi_skill.py, edítalo, y se cargará solo.
"""

from rick.skills.base import Skill, register


class SaludarSkill(Skill):
    name = "SALUDAR"
    description = "Saluda al usuario de forma personalizada"
    prompt_line = 'SALUDAR{"nombre":"..."}'
    input_schema = {
        "type": "object",
        "properties": {
            "nombre": {
                "type": "string",
                "description": "Nombre de la persona a saludar"
            }
        },
        "required": ["nombre"],
    }

    def run(self, executor, params):
        nombre = params.get("nombre", "mundo")
        executor.hablar(f"¡Hola, {nombre}!")
        return f"Saludé a {nombre}"


register(SaludarSkill())
