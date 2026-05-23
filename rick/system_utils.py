import shlex
import subprocess
import shutil
import os
import pathlib
import datetime
import urllib.parse
import psutil
import requests

from .logging_setup import log

_has = lambda cmd: shutil.which(cmd) is not None

_DIR_ALIASES = {
    "escritorio": "Desktop",
    "desktop": "Desktop",
    "descargas": "Downloads",
    "downloads": "Downloads",
    "documentos": "Documents",
    "documents": "Documents",
    "música": "Music",
    "musica": "Music",
    "music": "Music",
    "vídeos": "Videos",
    "videos": "Videos",
    "imágenes": "Pictures",
    "imagenes": "Pictures",
    "pictures": "Pictures",
    "imagens": "Pictures",
    "imagen": "Pictures",
    "descarga": "Downloads",
    "documento": "Documents",
    "descargar": "Downloads",
}

_SENSITIVE_PATHS = [
    "/etc", "/proc", "/sys", "/dev", "/boot", "/root",
    ".ssh", ".gnupg", ".config/opencode",
]


def _es_ruta_segura(resolved: str) -> bool:
    home = os.path.expanduser("~")
    resolved = os.path.normpath(os.path.realpath(resolved) if os.path.exists(resolved) else resolved)
    normalized = os.path.normpath(resolved)
    if normalized.startswith("/tmp/") or normalized == "/tmp":
        return True
    if not normalized.startswith(home + os.sep) and normalized != home:
        return False
    rel = os.path.relpath(normalized, home)
    for sensitive in _SENSITIVE_PATHS:
        if rel == sensitive or rel.startswith(sensitive + os.sep) or sensitive.startswith("/") and normalized.startswith(sensitive):
            return False
    return True


def resolver_ruta(ruta: str = "", cwd: str = "~") -> str:
    if not ruta or not ruta.strip():
        return os.path.expanduser(cwd)
    ruta = ruta.strip()
    if ruta.startswith("/"):
        return os.path.normpath(os.path.expanduser(ruta))
    ruta_lower = ruta.lower()
    if ruta_lower == "..":
        padre = os.path.dirname(os.path.expanduser(cwd))
        return padre if padre else os.path.expanduser(cwd)
    if ruta_lower in _DIR_ALIASES:
        ruta = _DIR_ALIASES[ruta_lower]
    for alias, real in _DIR_ALIASES.items():
        if ruta_lower.startswith(alias + "/") or ruta_lower.startswith(alias + os.sep):
            ruta = real + ruta[len(alias):]
            break
    base = os.path.expanduser(cwd)
    resolved = os.path.normpath(os.path.join(base, ruta))
    if not _es_ruta_segura(resolved):
        log.warning(f"Ruta bloqueada por seguridad: {resolved}")
        return os.path.expanduser(cwd)
    return resolved

def tamaño_legible(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024 ** 2:
        return f"{bytes_ / 1024:.1f} KB"
    elif bytes_ < 1024 ** 3:
        return f"{bytes_ / 1024 ** 2:.1f} MB"
    else:
        return f"{bytes_ / 1024 ** 3:.2f} GB"


def run_cmd(cmd: list[str], timeout: float = 5.0, capture: bool = False) -> str | None:
    """Ejecuta un comando con timeout. Retorna stdout si capture=True."""
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        if capture:
            return r.stdout.decode("utf-8", errors="replace").strip()
        return "" if r.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
        log.debug(f"run_cmd error: {e}")
        return None


def hotkey(combo: str):
    if _has("wtype"):
        parts = combo.split("+")
        if len(parts) > 1:
            modifiers = parts[:-1]
            key = parts[-1]
            mods_down = " ".join(f"-M {m}" for m in modifiers)
            mods_up = " ".join(f"-m {m}" for m in modifiers)
            run_cmd(["wtype"] + mods_down.split() + [key] + mods_up.split())
        else:
            run_cmd(["wtype", "-k", combo])
    elif _has("xdotool"):
        run_cmd(["xdotool", "key", combo])
    else:
        log.warning("wtype/xdotool no instalados — atajo no ejecutado")


def wayland_type(texto: str):
    if _has("wtype"):
        run_cmd(["wtype", texto])
    elif _has("xdotool"):
        run_cmd(["xdotool", "type", texto])
    else:
        log.warning("wtype/xdotool no instalados — texto no escrito")


def screenshot(ruta: str) -> bool:
    if _has("grim"):
        return run_cmd(["grim", ruta]) is not None
    if _has("gnome-screenshot"):
        run_cmd(["gnome-screenshot", "-f", ruta])
        return True
    if _has("scrot"):
        run_cmd(["scrot", ruta])
        return True
    return False


def volumen(accion: str, pct: int = 10):
    if _has("wpctl"):
        sink = "@DEFAULT_AUDIO_SINK@"
        cmds = {
            "subir": ["wpctl", "set-volume", "-l", "1.5", sink, f"{pct}%+"],
            "bajar": ["wpctl", "set-volume", sink, f"{pct}%-"],
            "mute":  ["wpctl", "set-mute", sink, "toggle"],
        }
        if accion in cmds:
            run_cmd(cmds[accion])
    elif _has("amixer"):
        m = {"subir": f"{pct}%+", "bajar": f"{pct}%-", "mute": "toggle"}
        run_cmd(["amixer", "-D", "pulse", "sset", "Master", m.get(accion, "toggle")])


def sistema_info() -> str:
    cpu  = psutil.cpu_percent(interval=0.5)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.datetime.now() - boot
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m = rem // 60
    return (
        f"CPU {cpu}%, RAM {ram.percent}% "
        f"({ram.used // (1024**3)}/{ram.total // (1024**3)} GB), "
        f"disco libre {disk.free // (1024**3)} GB, "
        f"uptime {h}h {m}min."
    )


def proceso_info(nombre: str) -> str:
    found = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            if nombre.lower() in p.info["name"].lower():
                found.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if not found:
        return f"No encontré ningún proceso llamado '{nombre}'."
    lines = []
    for p in found[:4]:
        lines.append(
            f"PID {p['pid']} ({p['name']}): CPU {p['cpu_percent']:.1f}%, "
            f"RAM {p['memory_percent']:.1f}%, estado {p['status']}"
        )
    return ". ".join(lines) + "."


def buscar_archivo(nombre: str, directorio: str = "~", profundidad: int = 3) -> str:
    base = pathlib.Path(directorio).expanduser()
    try:
        results = []
        for p in base.rglob(nombre):
            depth = len(p.relative_to(base).parts)
            if depth <= profundidad:
                results.append(str(p))
            if len(results) >= 10:
                break
        if not results:
            return f"No encontré ningún archivo '{nombre}' en {base}."
        return f"Encontré {len(results)} archivo(s): " + ", ".join(results[:5])
    except PermissionError:
        return f"Sin permiso para buscar en {base}."


def ejecutar_cmd(cmd: str, timeout: int = 10) -> str:
    try:
        parts = shlex.split(cmd)
        safe_cmd = ' '.join(shlex.quote(p) for p in parts)
    except ValueError:
        safe_cmd = cmd
    try:
        r = subprocess.run(
            safe_cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = (r.stdout + r.stderr).strip()
        if not out:
            return f"Comando ejecutado (código {r.returncode})."
        return out[:800]
    except subprocess.TimeoutExpired:
        return f"Timeout al ejecutar: {cmd}"
    except Exception as e:
        return f"Error: {e}"


def obtener_clima(ciudad: str) -> str:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(ciudad)}?format=3&lang=es"
        r = requests.get(url, timeout=8)
        return r.text.strip() if r.ok else f"No pude obtener el clima de {ciudad}."
    except Exception:
        return f"Sin conexión para consultar el clima de {ciudad}."


def traducir(texto: str, idioma_destino: str = "es") -> str:
    """Traducción via Google Translate (sin clave API)."""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": idioma_destino,
            "dt": "t",
            "q": texto,
        }
        r = requests.get(url, params=params, timeout=8)
        if r.ok:
            data = r.json()
            return "".join(seg[0] for seg in data[0] if seg[0])
        return "Error de traducción."
    except Exception as e:
        return f"No pude traducir: {e}"


def clipboard_leer() -> str:
    try:
        import pyperclip
        try:
            return pyperclip.paste() or "El portapapeles está vacío."
        except Exception:
            pass
    except ImportError:
        pass

    for cmd in [["wl-paste"], ["xclip", "-o"], ["xsel", "--output"]]:
        out = run_cmd(cmd, capture=True)
        if out:
            return out
    return "No pude leer el portapapeles."


def clipboard_escribir(texto: str) -> str:
    try:
        import pyperclip
        try:
            pyperclip.copy(texto)
            return "Texto copiado al portapapeles."
        except Exception:
            pass
    except ImportError:
        pass

    for cmd_tmpl in [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
        try:
            r = subprocess.run(cmd_tmpl, input=texto.encode(), timeout=3)
            if r.returncode == 0:
                return "Texto copiado al portapapeles."
        except Exception:
            pass
    return "No pude escribir en el portapapeles."
