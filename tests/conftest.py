"""Configuración de pytest: arranca una ``QgsApplication`` en modo sin pantalla.

Importante: el prefijo de QGIS y el perfil se configuran *antes* de importar
``qgis.core``; por eso los imports de QGIS viven dentro de las fixtures.

El módulo también expone las rutas del proyecto, que usa ``scripts/correr_tests.py``
(corredor alternativo para cuando pytest no está instalado en el Python de QGIS).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# pytest es opcional: el corredor propio (scripts/correr_tests.py) reutiliza este
# módulo para conocer las rutas, así que no se puede fallar si no está instalado.
try:
    import pytest
except ImportError:  # pragma: no cover - depende del entorno
    pytest = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ejecutar sin pantalla salvo que el usuario ya haya elegido plataforma.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from minigis.bootstrap import create_application, setup_environment  # noqa: E402

SAMPLES_DIR = PROJECT_ROOT / "samples"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


def _decorador_fixture(*args, **kwargs):
    """``pytest.fixture`` si está instalado; si no, un decorador neutro.

    Así este archivo se puede importar desde el corredor propio
    (``scripts/correr_tests.py``), que llama a las funciones directamente.
    """
    if pytest is not None:
        return pytest.fixture(*args, **kwargs)

    def identidad(funcion):
        return funcion

    return identidad


fixture = _decorador_fixture


@fixture(scope="session")
def qgis_app():
    """Una única ``QgsApplication`` para toda la sesión de tests."""
    profile = ARTIFACTS_DIR / "perfil-qgis"
    setup_environment(profile_dir=profile)
    app = create_application(["pytest-minigis"])
    app.setApplicationName("MiniGIS")
    yield app
    app.exitQgis()


@fixture(scope="session")
def _prepared_qgis(qgis_app):
    """Deja QGIS inicializado y limpio para cada test."""
    from qgis.core import QgsProject

    QgsProject.instance().removeAllMapLayers()
    return qgis_app


@fixture
def window(_prepared_qgis, qtbot):
    """Ventana principal lista para usar, con el proyecto vacío."""
    from qgis.core import QgsProject

    from minigis.app import MainWindow

    QgsProject.instance().removeAllMapLayers()
    win = MainWindow()
    qtbot.addWidget(win)
    win.resize(1200, 800)
    win.show()
    qtbot.waitExposed(win)
    yield win
    QgsProject.instance().removeAllMapLayers()
    win.close()


@fixture(scope="session")
def samples() -> dict[str, Path]:
    """Rutas de los shapefiles de ejemplo, generándolos si faltan."""
    if not (SAMPLES_DIR / "poligonos.shp").exists():
        from scripts.crear_datos_ejemplo import main as generar

        assert generar() == 0
    return {
        "poligonos": SAMPLES_DIR / "poligonos.shp",
        "lineas": SAMPLES_DIR / "lineas.shp",
        "puntos": SAMPLES_DIR / "puntos.shp",
    }


@fixture(scope="session")
def artifacts_dir() -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR
