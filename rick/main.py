#!/usr/bin/env python3

import sys
import os
import signal
import argparse
import logging
import threading
import time

import requests
import numpy as np
import sounddevice as sd

from .logging_setup import setup_logging, log
from .config import CFG
from .audio import VADRecorder, load_whisper, transcribir
from .llm import consultar_llm
from .tts import TTS
from .memory import ConversationMemory, NotesManager
from .reminders import ReminderManager
from .executor import ActionExecutor
from .agent import run_agent_task, _is_complex_task


class JARVIS:
    def __init__(self, cfg: dict, args):
        self.cfg      = cfg
        self.args     = args
        self.tts      = TTS(cfg)
        self.vad      = VADRecorder(cfg)
        self.memory   = ConversationMemory(cfg["history_file"], cfg["max_ctx_turns"])
        self.notes    = NotesManager(cfg["notes_file"])
        self.reminders= ReminderManager(self.tts.say)
        self.executor = ActionExecutor(cfg, self.notes, self.reminders)
        self.executor.set_hablar(self.tts.say)
        self.whisper_model = None
        self.silent_mode = False

    def _load_whisper(self):
        device = "cuda" if self._has_cuda() else "cpu"
        self.whisper_model = load_whisper(self.cfg["whisper_model"], device)
        if self.whisper_model is None:
            log.error("No se pudo cargar Whisper")
            sys.exit(1)
        log.info("Whisper listo")

    @staticmethod
    def _has_cuda() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False

    def _check_ollama(self):
        for _ in range(3):
            try:
                r = requests.get(
                    self.cfg["ollama_url"].replace("/generate", "/tags"),
                    timeout=4,
                )
                modelos = [m["name"] for m in r.json().get("models", [])]
                log.info(f"Ollama OK — modelos: {modelos}")
                return
            except Exception:
                time.sleep(1)
        log.error("Ollama no responde. Ejecuta: ollama serve")
        sys.exit(1)

    def _check_mic(self):
        try:
            info = sd.query_devices(self.cfg["mic_device"], "input")
            log.info(f"Micrófono: {info['name']}")
        except Exception as e:
            log.error(f"Error micrófono: {e}. Prueba: python -m rick.main --list-mics")
            sys.exit(1)

    def process_command(self, texto: str):
        log.info(f"Tú: {texto}")

        # Detectar comandos de silencio
        texto_lower = texto.lower().strip()
        if "callate" in texto_lower or "cállate" in texto_lower:
            self.silent_mode = True
            log.info("Modo silencio activado")
            return

        if "hola rick" in texto_lower and self.silent_mode:
            self.silent_mode = False
            log.info("Modo silencio desactivado")
            return

        # Si está en modo silencio, no procesar nada
        if self.silent_mode:
            log.debug("En modo silencio, ignorando: " + texto)
            return

        self.memory.add_user(texto)

        # Modo dual: detectar si es tarea compleja para activar agente
        if self.cfg.get("agent_enabled", True) and _is_complex_task(texto):
            log.info("[main] Modo agente activado para tarea compleja")
            respuesta = run_agent_task(texto, self.cfg, self.memory, self.executor, self.tts)
            self.tts.say(respuesta)
            return

        # Flujo legacy (modo reactivo simple)
        log.info("[main] Modo reactivo")
        prompt = self.memory.build_prompt(texto)

        resp   = consultar_llm(prompt, self.cfg)
        accion = resp.get("accion", "CONVERSAR")
        params = resp.get("parametros", {})
        voz    = resp.get("respuesta_voz", "Hecho.")

        log.info(f"Acción: {accion} | Params: {params}")
        if resp.get("pensamiento"):
            log.debug(f"Pensamiento: {resp['pensamiento']}")

        self.tts.say(voz)
        self.executor.run(accion, params)
        self.memory.add_assistant(resp)

    def run_push(self):
        self.tts.say("RICK listo. Enter para hablar, Enter para parar.")
        print("\n\033[0;36m  Enter = grabar/parar  |  Ctrl+C = salir\033[0m\n")

        while True:
            try:
                input("\033[2m>> Enter para EMPEZAR...\033[0m")
            except KeyboardInterrupt:
                self.tts.say("Hasta pronto.")
                sys.exit(0)

            print("\033[0;31m🔴 Grabando... (Enter para PARAR)\033[0m")

            parar  = threading.Event()
            buf    = []

            def _grabar():
                chunk_n = int(self.cfg["sample_rate"] * 0.08)
                max_n   = int(self.cfg["max_record_s"] / 0.08)
                try:
                    with sd.InputStream(
                        device=self.cfg["mic_device"],
                        samplerate=self.cfg["sample_rate"],
                        channels=self.cfg["channels"],
                        dtype="int16",
                    ) as st:
                        for _ in range(max_n):
                            if parar.is_set():
                                break
                            chunk, _ = st.read(chunk_n)
                            buf.append(chunk.copy())
                except sd.PortAudioError as e:
                    log.error(f"Audio: {e}")

            hilo = threading.Thread(target=_grabar, daemon=True)
            hilo.start()

            try:
                input()
            except KeyboardInterrupt:
                self.tts.say("Hasta pronto.")
                sys.exit(0)

            parar.set()
            hilo.join()
            print("\033[0;33m⏹  Parado\033[0m")

            if not buf:
                continue
            audio = np.concatenate(buf).flatten().astype(np.float32) / 32768.0
            if len(audio) < int(self.cfg["sample_rate"] * 0.3):
                print("  ⚠  Audio demasiado corto")
                continue

            texto = transcribir(self.whisper_model, audio, self.cfg["language"])
            if not texto:
                log.warning("Whisper no transcribió nada.")
                continue

            try:
                self.process_command(texto)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.error(f"Error: {e}")
                self.tts.say("Error inesperado.")

    def run_realtime(self):
        self.tts.say("Modo conversación activado. Hablo cuando quieras.")
        print("\n\033[0;36m🎤 Escuchando en tiempo real... (Ctrl+C para salir)\033[0m\n")

        silence_count = 0
        max_silence = 0.5

        while True:
            audio = self.vad.record()
            if audio is None:
                silence_count += 1
                if silence_count % 10 == 0:
                    print(".", end="", flush=True)
                if silence_count > max_silence * 12:
                    silence_count = 0
                continue

            silence_count = 0
            print("\n🔴 Procesando...", end="", flush=True)

            texto = transcribir(self.whisper_model, audio, self.cfg["language"])
            if not texto:
                print(" (vacío)")
                continue

            print()
            try:
                self.process_command(texto)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.error(f"Error: {e}")
                self.tts.say("Error inesperado. Continuando.")

    def start(self):
        log.info("Iniciando RICK v2...")
        self._load_whisper()
        if self.cfg.get("provider", "ollama") == "ollama":
            self._check_ollama()
        self._check_mic()

        def _signal_handler(sig, frame):
            print()
            log.info("Saliendo...")
            self.reminders.cancel_all()
            self.tts.say("Hasta pronto, amo.")
            sys.exit(0)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        if self.args.realtime:
            self.run_realtime()
        elif self.args.push:
            self.run_push()
        else:
            self.run_realtime()


def parse_args():
    ap = argparse.ArgumentParser(
        description="RICK — Asistente de voz local (Wayland + Ollama)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--realtime",   action="store_true",     help="Modo conversación (escucha continua)")
    ap.add_argument("--push",       action="store_true",     help="Modo push-to-talk (Enter)")
    ap.add_argument("--history",    action="store_true",     help="Mostrar historial y salir")
    ap.add_argument("--daemon",     action="store_true",     help="Desacoplar del terminal (nohup)")
    ap.add_argument("--no-voice",   action="store_true",     help="Desactivar TTS (solo texto)")
    ap.add_argument("--debug",      action="store_true",     help="Logging verboso")
    ap.add_argument("--list-mics",  action="store_true",     help="Listar dispositivos de audio")
    ap.add_argument("--model",      default=None,            help="Modelo Whisper: tiny/base/small/medium/large")
    ap.add_argument("--llm",        default=None,            help="Modelo Ollama (ej: llama3:8b)")
    ap.add_argument("--lang",       default=None,            help="Idioma Whisper (ej: en, es, fr)")
    return ap.parse_args()


def main():
    # Cargar variables de .env si existe
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # sin python-dotenv, funciona con vars de entorno del sistema

    args = parse_args()
    setup_logging(logging.DEBUG if args.debug else logging.INFO)

    if args.history:
        mem = ConversationMemory(CFG["history_file"], CFG["max_ctx_turns"])
        mem.print_history(n=30)
        sys.exit(0)

    # Aplicar overrides de args
    if args.model:    CFG["whisper_model"] = args.model
    if args.llm:      CFG["model"]         = args.llm
    if args.lang:     CFG["language"]      = args.lang
    if args.no_voice: CFG["no_voice"]      = True

    # Modo daemon
    if args.daemon:
        log.info("Iniciando en modo daemon...")
        pid = os.fork() if hasattr(os, "fork") else -1
        if pid > 0:
            print(f"RICK daemon PID: {pid}")
            sys.exit(0)
        os.setsid()

    # Arrancar
    jarvis = JARVIS(CFG, args)
    jarvis.start()


if __name__ == "__main__":
    main()
