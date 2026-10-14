"""Corredor de tests mínimo, sin dependencias externas.

La suite de ``tests/`` está escrita para pytest, pero instalar pytest en el
Python de QGIS requiere red y permisos de administrador. Este script ejecuta los
mismos archivos de test con un mini-fixture propio, así las pruebas se pueden
correr siempre:

    dev-env.bat scripts\\correr_tests.py
    dev-env.bat scripts\\correr_tests.py -k casilla -v
"""

from __future__ import annotations

import argparse
import inspect
import os
import sys
import time
import traceback
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

MODULOS_DE_TEST = ("tests.test_layers", "tests.test_app")


def _instalar_pytest_de_mentira() -> None:
    """Si no hay pytest, los tests igual lo importan (para ``raises``).

    Se registra un módulo mínimo con las dos cosas que usan los tests, así el
    corredor propio puede ejecutarlos sin dependencias externas.
    """
    try:
        import pytest  # noqa: F401

        return
    except ImportError:
        pass

    class _Raises:
        def __init__(self, excepcion):
            self.excepcion = excepcion
            self.valor = None

        def __enter__(self):
            return self

        def __exit__(self, tipo, valor, traza):
            if tipo is None:
                raise AssertionError(f"No se lanzó la excepción esperada {self.excepcion.__name__}")
            if not issubclass(tipo, self.excepcion):
                return False
            self.valor = valor
            return True

    def _fixture_sin_efecto(*_args, **_kwargs):
        return lambda funcion: funcion

    modulo = types.ModuleType("pytest")
    modulo.raises = lambda excepcion, **_kwargs: _Raises(excepcion)
    modulo.fail = lambda mensaje="": (_ for _ in ()).throw(AssertionError(mensaje))
    modulo.fixture = _fixture_sin_efecto
    modulo.mark = types.SimpleNamespace()
    sys.modules["pytest"] = modulo


class QtBot:
    """Sustituto mínimo de la fixture ``qtbot`` de pytest-qt."""

    def __init__(self):
        from qgis.PyQt.QtWidgets import QApplication

        self._app = QApplication.instance()

    def addWidget(self, widget):  # noqa: N802 - nombre tomado de pytest-qt
        # En pytest-qt esto registra el widget para cerrarlo al final; acá no
        # hace falta, pero se mantiene la firma para no tocar los tests.
        return widget

    def waitExposed(self, widget, timeout=5000):  # noqa: N802
        widget.show()
        self._app.processEvents()

    def wait(self, ms: int) -> None:  # noqa: N802
        from tests.helpers import process_events

        process_events(ms)


def _constructor_de_fixtures():
    """Devuelve las fixtures por nombre, con el mismo alcance que en conftest."""
    from tests import conftest

    cache: dict[str, object] = {}

    def qgis_app():
        if "qgis_app" not in cache:
            from minigis.bootstrap import create_application, setup_environment

            setup_environment(profile_dir=conftest.ARTIFACTS_DIR / "perfil-qgis")
            app = create_application(["correr_tests"])
            app.setApplicationName("MiniGIS")
            cache["qgis_app"] = app
        return cache["qgis_app"]

    def preparado():
        qgis_app()
        from qgis.core import QgsProject

        QgsProject.instance().removeAllMapLayers()
        return None

    def window():
        from qgis.core import QgsProject

        from minigis.app import MainWindow
        from tests.helpers import process_events

        preparado()
        win = MainWindow()
        bot.addWidget(win)
        win.resize(1200, 800)
        win.show()
        process_events(200)
        cache["window"] = win
        return win

    def samples():
        conftest.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        if not (conftest.SAMPLES_DIR / "poligonos.shp").exists():
            from scripts.crear_datos_ejemplo import main as generar

            assert generar() == 0
        return {
            "poligonos": conftest.SAMPLES_DIR / "poligonos.shp",
            "lineas": conftest.SAMPLES_DIR / "lineas.shp",
            "puntos": conftest.SAMPLES_DIR / "puntos.shp",
        }

    def artifacts_dir():
        conftest.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        return conftest.ARTIFACTS_DIR

    bot = QtBot()
    return {
        "qgis_app": qgis_app,
        "prepared_qgis": preparado,
        "_prepared_qgis": preparado,
        "window": window,
        "samples": samples,
        "artifacts_dir": artifacts_dir,
        "qtbot": lambda: bot,
    }


def _limpiar_ventana(fixtures) -> None:
    ventana = fixtures.get("window")
    if ventana is None:
        return
    from qgis.core import QgsProject

    from tests.helpers import process_events

    try:
        QgsProject.instance().removeAllMapLayers()
        ventana.close()
        process_events(100)
    except Exception:  # noqa: BLE001 - la limpieza no debe tapar el resultado
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Corre la suite de tests de MiniGIS")
    parser.add_argument("-k", dest="filtro", default="", help="sólo tests cuyo nombre contenga este texto")
    parser.add_argument("-v", dest="verboso", action="store_true", help="mostrar cada test")
    args = parser.parse_args()

    import importlib

    from tests.helpers import process_events

    _instalar_pytest_de_mentira()
    fixtures = _constructor_de_fixtures()
    resultados: list[tuple[str, bool, float, str]] = []

    for nombre_modulo in MODULOS_DE_TEST:
        modulo = importlib.import_module(nombre_modulo)
        print(f"\n=== {nombre_modulo} ===")
        for nombre_funcion, funcion in sorted(inspect.getmembers(modulo, inspect.isfunction)):
            if not nombre_funcion.startswith("test_"):
                continue
            if args.filtro and args.filtro.lower() not in nombre_funcion.lower():
                continue

            parametros = list(inspect.signature(funcion).parameters)
            valores = []
            saltear = False
            for parametro in parametros:
                if parametro == "tmp_path":
                    destino = PROJECT_ROOT / "artifacts" / "tmp" / nombre_funcion
                    destino.mkdir(parents=True, exist_ok=True)
                    valores.append(destino)
                elif parametro in fixtures:
                    valores.append(fixtures[parametro]())
                else:
                    print(f"  SALTEADO {nombre_funcion}: fixture desconocida '{parametro}'")
                    saltear = True
                    break
            if saltear:
                continue

            inicio = time.monotonic()
            try:
                funcion(*valores)
                ok, detalle = True, ""
            except Exception:  # noqa: BLE001 - se reporta el fallo completo
                ok, detalle = False, traceback.format_exc()
            duracion = time.monotonic() - inicio
            resultados.append((nombre_funcion, ok, duracion, detalle))

            if ok:
                print(f"  [OK   ] {nombre_funcion} ({duracion:.2f}s)" if args.verboso else f"  [OK   ] {nombre_funcion}")
            else:
                print(f"  [FALLA] {nombre_funcion} ({duracion:.2f}s)")
                print("\n".join("      " + linea for linea in detalle.strip().splitlines()[-12:]))

            _limpiar_ventana(fixtures)
            process_events(50)

    fallas = [nombre for nombre, ok, _, _ in resultados if not ok]
    total = len(resultados)
    print(f"\n{'=' * 60}")
    print(f"Resultado: {total - len(fallas)}/{total} tests OK en {sum(d for _, _, d, _ in resultados):.1f}s")
    if fallas:
        print("Fallaron: " + ", ".join(fallas))
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
