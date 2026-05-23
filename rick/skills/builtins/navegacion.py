import os
import datetime
import shlex
from difflib import get_close_matches

from rick.skills.base import Skill, register
from rick.system_utils import buscar_archivo, ejecutar_cmd, resolver_ruta, tamaño_legible


class IrSkill(Skill):
    name = "IR"
    description = "Navega a un directorio (.. para subir, - para volver, busca automáticamente)"
    prompt_line = 'IR{"directorio":"nombre"} (.. subir, - volver, busca auto)'
    input_schema = {"type": "object", "properties": {
        "directorio": {"type": "string", "description": "Directorio destino"}
    }, "required": ["directorio"]}

    def _find_dir_in(self, parent: str, name: str, executor) -> str | None:
        try:
            candidates = [d for d in os.listdir(parent)
                         if os.path.isdir(os.path.join(parent, d))]
        except PermissionError:
            return None
        if not candidates:
            return None
        for c in candidates:
            if c == name:
                return os.path.join(parent, c)
        name_lower = name.lower()
        for c in candidates:
            if c.lower() == name_lower:
                return os.path.join(parent, c)
        matches = get_close_matches(name, candidates, n=1, cutoff=0.5)
        if matches:
            return os.path.join(parent, matches[0])
        return None

    def run(self, executor, params):
        raw = (params.get("directorio") or ".").strip()

        if raw in ("--back", "-", "..-"):
            if not executor.dir_stack:
                return executor.say("No hay directorios anteriores.")
            prev = executor.dir_stack.pop()
            if not os.path.isdir(prev):
                return executor.say("El directorio anterior ya no existe.")
            executor.cwd = prev
            return executor.say(f"De vuelta en {executor.cwd_pretty()}.")

        if raw in executor.bookmarks:
            return executor._cd(executor.bookmarks[raw])

        destino = executor.resolve(raw)
        if os.path.isdir(destino):
            return executor._cd(destino)

        parent = os.path.dirname(destino)
        if parent and os.path.isdir(parent):
            match = self._find_dir_in(parent, os.path.basename(destino), executor)
            if match:
                return executor._cd(match)

        match = self._find_dir_in(executor.cwd, raw, executor)
        if match:
            return executor._cd(match)

        home = os.path.expanduser("~")
        if executor.cwd != home:
            match = self._find_dir_in(home, raw, executor)
            if match:
                return executor._cd(match)

        if os.path.isfile(destino):
            return executor._cd(os.path.dirname(destino))

        return executor.say(f"No encontré el directorio {raw}.")

register(IrSkill())


class PwdSkill(Skill):
    name = "PWD"
    description = "Muestra el directorio actual"
    prompt_line = 'PWD{}'
    input_schema = {"type": "object", "properties": {}}

    def run(self, executor, params):
        executor.hablar(f"Estoy en {executor.cwd_pretty()}.")
        return f"PWD: {executor.cwd}"

register(PwdSkill())


class ListarDirSkill(Skill):
    name = "LISTAR_DIR"
    description = "Lista el contenido de un directorio"
    prompt_line = 'LISTAR_DIR{"ruta":"."}'
    input_schema = {"type": "object", "properties": {
        "ruta": {"type": "string", "description": "Ruta del directorio a listar"}
    }}

    def run(self, executor, params):
        ruta = executor.resolve(params.get("ruta", "."))
        try:
            items = sorted(os.listdir(ruta), key=lambda x: (not os.path.isdir(os.path.join(ruta, x)), x.lower()))
            if not items:
                return executor.say("La carpeta está vacía.")

            C_DIR = "\033[0;34m"
            C_EXE = "\033[0;32m"
            C_LNK = "\033[0;36m"
            C_HID = "\033[2m"
            C_RST = "\033[0m"
            C_DIM = "\033[2m"
            C_BOLD = "\033[1m"

            home = os.path.expanduser("~")
            header_path = ruta.replace(home, "~")
            lines = [f"{C_BOLD}📂 {header_path}{C_RST}\n"]

            for name in items:
                full = os.path.join(ruta, name)
                is_hidden = name.startswith(".")
                try:
                    stat_info = os.stat(full)
                    size = tamaño_legible(stat_info.st_size)
                    mtime = datetime.datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    size = "?"
                    mtime = ""

                is_dir = os.path.isdir(full)
                is_lnk = os.path.islink(full)
                is_exe = os.access(full, os.X_OK) and not is_dir

                if is_dir:
                    color, icon, display = C_DIR, "📁", f"{name}/"
                elif is_lnk:
                    color, icon, display = C_LNK, "🔗", name
                elif is_exe:
                    color, icon, display = C_EXE, "⚡", name
                else:
                    color, icon, display = C_RST, " ", name

                if is_hidden:
                    color += C_HID

                link_target = f" → {os.readlink(full)}" if is_lnk else ""
                size_str = f"{size:>8}" if not is_dir else "       " + C_DIM + "DIR" + C_RST
                lines.append(f"{color}{icon} {display}{link_target}{C_RST}  {C_DIM}{size_str}  {mtime}{C_RST}")

            output = "\n".join(lines)
            dirs_n = sum(1 for n in items if os.path.isdir(os.path.join(ruta, n)))
            files_n = len(items) - dirs_n
            executor.hablar(f"{dirs_n} carpetas, {files_n} archivos.")
            return output
        except PermissionError:
            return executor.say(f"Sin permiso para listar {ruta}.")
        except Exception as e:
            return executor.say(f"No pude listar: {e}")

register(ListarDirSkill())


class InfoDirSkill(Skill):
    name = "INFO_DIR"
    description = "Muestra estadísticas detalladas de un directorio"
    prompt_line = 'INFO_DIR{"ruta":"."}'
    input_schema = {"type": "object", "properties": {
        "ruta": {"type": "string", "description": "Ruta del directorio"}
    }}

    def run(self, executor, params):
        ruta = executor.resolve(params.get("ruta", "."))
        if not os.path.isdir(ruta):
            return executor.say("Eso no es un directorio.")
        try:
            home = os.path.expanduser("~")
            header_path = ruta.replace(home, "~")
            total_size = 0
            file_count = 0
            dir_count = 0
            largest = []
            by_ext = {}
            for root, dirs, files in os.walk(ruta):
                dir_count += len(dirs)
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        s = os.stat(fp)
                        total_size += s.st_size
                        file_count += 1
                        ext = os.path.splitext(f)[1].lower() or "(sin ext)"
                        by_ext[ext] = by_ext.get(ext, 0) + 1
                        largest.append((s.st_size, fp))
                    except Exception:
                        pass
            largest.sort(reverse=True, key=lambda x: x[0])
            top5 = "\n".join(f"  {tamaño_legible(s)}  {p}" for s, p in largest[:5])
            exts = sorted(by_ext.items(), key=lambda x: -x[1])[:8]
            ext_str = ", ".join(f"{ext}: {n}" for ext, n in exts)
            voice = f"{file_count} archivos, {dir_count} carpetas, {tamaño_legible(total_size)} en total."
            executor.hablar(voice)
            return (
                f"\033[1m📊 {header_path}\033[0m\n"
                f"  Archivos: {file_count}  Carpetas: {dir_count}\n"
                f"  Tamaño total: {tamaño_legible(total_size)}\n"
                f"  Tipos: {ext_str}\n"
                f"  Top 5 más grandes:\n{top5}"
            )
        except PermissionError:
            return executor.say(f"Sin permiso para analizar {ruta}.")
        except Exception as e:
            return executor.say(f"Error analizando directorio: {e}")

register(InfoDirSkill())


class LeerDirRecursivoSkill(Skill):
    name = "LEER_DIR_RECURSIVO"
    description = "Lista el árbol de archivos de un directorio"
    prompt_line = 'LEER_DIR_RECURSIVO{"ruta":".","profundidad":3}'
    input_schema = {"type": "object", "properties": {
        "ruta": {"type": "string", "description": "Ruta del directorio"},
        "profundidad": {"type": "integer", "description": "Profundidad máxima", "default": 3}
    }, "required": ["ruta"]}

    def run(self, executor, params):
        ruta = executor.resolve(params.get("ruta", "."))
        profundidad = params.get("profundidad", 3)
        if not os.path.isdir(ruta):
            return f"El directorio no existe: {ruta}"
        try:
            resultado = []
            home = os.path.expanduser("~")
            resultado.append(f"📂 {ruta.replace(home, '~')}/")
            for root, dirs, files in os.walk(ruta):
                depth = root.replace(ruta, "").count(os.sep)
                if depth >= profundidad:
                    dirs.clear()
                    continue
                if depth == 0:
                    continue
                rel = root[len(ruta) + 1:]
                parts = rel.split(os.sep)
                prefix = "│   " * (len(parts) - 1) + "├── "
                resultado.append(f"{prefix}{os.path.basename(root)}/")
                files_sorted = sorted(files)[:20]
                for i, f in enumerate(files_sorted):
                    try:
                        sz = tamaño_legible(os.stat(os.path.join(root, f)).st_size)
                    except Exception:
                        sz = "?"
                    file_prefix = prefix.replace("├── ", "│   ") + ("└── " if i == len(files_sorted) - 1 else "├── ")
                    resultado.append(f"{file_prefix}{f}  ({sz})")
                if len(files) > 20:
                    resultado.append(f"{prefix.replace('├── ', '│   ')}└── ... y {len(files) - 20} archivos más")
            return "\n".join(resultado[:300]) or "Directorio vacío."
        except Exception as e:
            return f"Error listando directorio: {e}"

register(LeerDirRecursivoSkill())


class BuscarArchivoSkill(Skill):
    name = "BUSCAR_ARCHIVO"
    description = "Busca archivos por nombre"
    prompt_line = 'BUSCAR_ARCHIVO{"nombre":"*.py","directorio":".","profundidad":3}'
    input_schema = {"type": "object", "properties": {
        "nombre": {"type": "string", "description": "Patrón de nombre"},
        "directorio": {"type": "string"},
        "profundidad": {"type": "integer"}
    }, "required": ["nombre", "directorio"]}

    def run(self, executor, params):
        result = buscar_archivo(
            params.get("nombre", "*"),
            executor.resolve(params.get("directorio", ".")),
            params.get("profundidad", 3),
        )
        return executor.say(result)

register(BuscarArchivoSkill())


class BuscarEnArchivosSkill(Skill):
    name = "BUSCAR_EN_ARCHIVOS"
    description = "Busca texto (grep) en archivos de un directorio"
    prompt_line = 'BUSCAR_EN_ARCHIVOS{"patron":"...","directorio":".","extension":".py"}'
    input_schema = {"type": "object", "properties": {
        "patron": {"type": "string", "description": "Texto a buscar"},
        "directorio": {"type": "string", "description": "Directorio donde buscar"},
        "extension": {"type": "string", "description": "Extensión de archivos (ej: .py)"}
    }, "required": ["patron", "directorio"]}

    def run(self, executor, params):
        patron = params.get("patron", "")
        directorio = executor.resolve(params.get("directorio", "."))
        extension = params.get("extension", "")
        if not patron.strip():
            return "Error: patrón vacío."
        try:
            ext_flag = f"--include={shlex.quote('*' + extension)}" if extension else ""
            cmd = f"grep -rn {ext_flag} {shlex.quote(patron)} {shlex.quote(directorio)} 2>/dev/null | head -50"
            result = ejecutar_cmd(cmd, timeout=15)
            return result or "No se encontraron coincidencias."
        except Exception as e:
            return f"Error buscando en archivos: {e}"

register(BuscarEnArchivosSkill())


class RenombrarSkill(Skill):
    name = "RENOMBRAR"
    description = "Renombra un archivo o directorio"
    prompt_line = 'RENOMBRAR{"origen":"...","destino":"..."}'
    input_schema = {"type": "object", "properties": {
        "origen": {"type": "string"},
        "destino": {"type": "string"}
    }, "required": ["origen", "destino"]}

    def run(self, executor, params):
        origen = executor.resolve(params.get("origen", ""))
        destino = executor.resolve(params.get("destino", ""))
        try:
            os.rename(origen, destino)
            return executor.say(f"Renombrado a {os.path.basename(destino)}.")
        except Exception as e:
            return executor.say(f"No pude renombrar: {e}")

register(RenombrarSkill())
