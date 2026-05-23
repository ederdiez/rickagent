import importlib
import pkgutil
import logging

_registry: dict[str, "Skill"] = {}
_loaded = False

log = logging.getLogger("rick")


class Skill:
    name: str = ""
    description: str = ""
    prompt_line: str = ""
    input_schema: dict | None = None

    def run(self, executor, params: dict) -> str | None:
        raise NotImplementedError

    def to_tool_def(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema or {
                "type": "object", "properties": {}, "required": []
            },
        }


def register(skill: Skill):
    _registry[skill.name] = skill


def get_all() -> list[Skill]:
    return list(_registry.values())


def get_tool_defs() -> list[dict]:
    return [s.to_tool_def() for s in _registry.values()]


def get_prompt_block() -> str:
    lines = []
    for s in _registry.values():
        if s.prompt_line:
            lines.append(s.prompt_line)
    return "\n".join(lines)


def _import_skills(pkg_name: str):
    try:
        pkg = importlib.import_module(pkg_name)
    except Exception as e:
        log.warning(f"No se pudo cargar {pkg_name}: {e}")
        return
    for importer, modname, ispkg in pkgutil.iter_modules(pkg.__path__):
        if modname.startswith("_") or modname == "base":
            continue
        try:
            importlib.import_module(f"{pkg_name}.{modname}")
        except Exception as e:
            log.warning(f"Skill {pkg_name}.{modname} falló al cargar: {e}")


def discover():
    global _loaded
    if _loaded:
        return
    _loaded = True
    _import_skills("rick.skills")
    _import_skills("rick.skills.builtins")
