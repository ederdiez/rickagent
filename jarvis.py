#!/usr/bin/env python3
"""
RICK v2 — Asistente de voz local (Wayland + Ollama)
Punto de entrada unificado para la versión modular.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rick.main import main

if __name__ == "__main__":
    main()
