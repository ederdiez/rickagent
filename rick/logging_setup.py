import logging
import sys
import datetime


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\033[2;37m",   # gris tenue
        logging.INFO:     "\033[0;36m",   # cian
        logging.WARNING:  "\033[0;33m",   # amarillo
        logging.ERROR:    "\033[0;31m",   # rojo
        logging.CRITICAL: "\033[1;35m",   # magenta brillante
    }
    RESET = "\033[0m"
    ICONS = {
        logging.DEBUG:    "·",
        logging.INFO:     "▸",
        logging.WARNING:  "⚠",
        logging.ERROR:    "✗",
        logging.CRITICAL: "☠",
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        icon  = self.ICONS.get(record.levelno, " ")
        ts    = datetime.datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        msg   = record.getMessage()
        return f"{color}{icon} [{ts}] {msg}{self.RESET}"


def setup_logging(level=logging.INFO):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


log = logging.getLogger("rick")
