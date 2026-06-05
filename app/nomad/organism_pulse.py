"""Background organism pulse — nomad NOMAD_ORGANISM_PULSE_MS pattern."""

from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

_pulse_thread: threading.Thread | None = None
_stop = threading.Event()


def pulse_interval_sec() -> float:
    raw = os.environ.get("AUREON_ORGANISM_PULSE_SEC", "").strip()
    if raw:
        try:
            return max(5.0, min(300.0, float(raw)))
        except ValueError:
            pass
    ms = os.environ.get("AUREON_ORGANISM_PULSE_MS", "30000").strip()
    try:
        return max(5.0, min(300.0, int(ms) / 1000.0))
    except ValueError:
        return 30.0


def _pulse_loop() -> None:
    from app.organism import get_organism

    interval = pulse_interval_sec()
    logger.info("Organism background pulse started — interval=%ss", interval)
    while not _stop.wait(interval):
        try:
            organism = get_organism()
            organism.pulse()
            if not organism.is_vital() and not organism.is_learning_allowed():
                vitals = organism.get_vitals_report()
                critical = [
                    o["id"]
                    for o in vitals.get("organs", [])
                    if isinstance(o, dict) and o.get("state") == "critical"
                ]
                logger.warning(
                    "Organism pulse: not vital — critical organs: %s",
                    ", ".join(critical) if critical else vitals.get("lockdown_reason"),
                )
        except Exception:
            logger.exception("Organism background pulse failed")


def start_organism_pulse() -> None:
    global _pulse_thread
    if _pulse_thread and _pulse_thread.is_alive():
        return
    _stop.clear()
    _pulse_thread = threading.Thread(target=_pulse_loop, name="aureon-organism-pulse", daemon=True)
    _pulse_thread.start()


def stop_organism_pulse() -> None:
    _stop.set()
    if _pulse_thread:
        _pulse_thread.join(timeout=2.0)
