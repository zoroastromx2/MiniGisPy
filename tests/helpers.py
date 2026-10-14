"""Utilidades para los tests: procesar eventos y capturar pantallas."""

from __future__ import annotations

import time
from pathlib import Path

from qgis.PyQt.QtCore import QEventLoop, QTimer
from qgis.PyQt.QtWidgets import QApplication


def process_events(ms: int = 250) -> None:
    """Deja correr el bucle de eventos un rato (para que el canvas se dibuje)."""
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        time.sleep(0.01)


def grab_widget(widget, path: str | Path) -> Path:
    """Guarda una captura de un widget (funciona con la plataforma 'offscreen')."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    process_events(200)
    pixmap = widget.grab()
    assert not pixmap.isNull(), "El widget no se pudo capturar"
    assert pixmap.save(str(path)), f"No se pudo escribir {path}"
    return path


def wait_until(predicate, timeout_ms: int = 5000, interval_ms: int = 25) -> bool:
    """Espera activa hasta que ``predicate()`` sea verdadero o venza el tiempo."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if predicate():
            return True
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, interval_ms)
        time.sleep(interval_ms / 1000)
    return bool(predicate())
