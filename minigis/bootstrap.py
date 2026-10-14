"""Inicialización del entorno QGIS/GDAL.

Este módulo **no** importa PyQt ni QGIS a nivel de módulo a propósito: la
variable de entorno ``QGIS_PREFIX_PATH`` tiene que estar fijada *antes* de
importar ``qgis.core``, y ``fix_qgis_prefix()`` es quien la calcula.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def fix_qgis_prefix() -> str:
    """Asegura que QGIS_PREFIX_PATH apunte a ``apps/qgis`` de la instalación.

    La variable normalmente la define el lanzador (``mini-gis.bat``). Si el
    usuario ejecuta el programa a mano, la deducimos desde el propio paquete
    Python de QGIS, que vive en ``<raíz>/apps/qgis/python/qgis``.
    """
    prefix = os.environ.get("QGIS_PREFIX_PATH")
    if prefix and Path(prefix).is_dir():
        return prefix

    try:
        import qgis  # noqa: PLC0415  (import diferido a propósito)
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise SystemExit(
            "No se pudo importar el paquete 'qgis'.\n"
            "Ejecutá la aplicación con 'mini-gis.bat' o con el intérprete de QGIS:\n"
            '  "C:\\Program Files\\QGIS 4.2.2\\bin\\python-qgis.bat" mini-gis\\main.py'
        ) from exc

    # <raíz>/apps/qgis/python/qgis/__init__.py  ->  <raíz>/apps/qgis/python
    # (el prefijo de QGIS es la carpeta que contiene a 'python/', 'bin/', etc.)
    prefix = str(Path(qgis.__file__).resolve().parents[2])
    os.environ["QGIS_PREFIX_PATH"] = prefix
    return prefix


def _perfil_utilizable(candidato: Path) -> bool:
    """Crea la carpeta de perfil y comprueba que se pueda escribir en ella."""
    try:
        candidato.mkdir(parents=True, exist_ok=True)
        prueba = candidato / ".escritura-ok"
        prueba.write_text("ok", encoding="utf-8")
        prueba.unlink()
        return True
    except OSError:
        return False


def setup_environment(profile_dir: str | os.PathLike[str] | None = None) -> Path:
    """Prepara el entorno del proceso antes de construir ``QgsApplication``.

    Devuelve la carpeta usada como perfil de usuario de QGIS, para no ensuciar
    el perfil real de la instalación con la configuración de MiniGIS. Si no se
    indica ninguna y la carpeta del usuario no es escribible, se cae a la
    carpeta temporal del sistema.
    """
    if profile_dir is not None:
        candidatos = [Path(profile_dir)]
    else:
        candidatos = [
            Path(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")) / "MiniGIS" / "perfil",
            Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "MiniGIS" / "perfil",
        ]

    elegido = next((c for c in candidatos if _perfil_utilizable(c)), None)
    if elegido is None:
        # Último recurso: dejar que QGIS use su propio perfil.
        fix_qgis_prefix()
        return Path(os.environ.get("QGIS_CUSTOM_CONFIG_PATH") or ".")
    profile_dir = elegido

    # Aísla las preferencias y la caché de autenticación del QGIS instalado.
    os.environ.setdefault("QGIS_CUSTOM_CONFIG_PATH", str(profile_dir))
    os.environ.setdefault("QGIS_AUTH_DB_DIR_PATH", str(profile_dir))
    os.environ.setdefault("GDAL_FILENAME_IS_UTF8", "YES")
    os.environ.setdefault("VSI_CACHE", "TRUE")
    os.environ.setdefault("VSI_CACHE_SIZE", "1000000")

    fix_qgis_prefix()
    return profile_dir


def create_application(argv: list[str] | None = None):
    """Crea y configura la ``QgsApplication`` (requiere PyQt6 ya disponible).

    PyQt6 exige que ``argv`` sea una lista de ``bytes``; por eso se codifica acá
    y así los llamadores pueden seguir pasando ``str`` con naturalidad.
    """
    from qgis.core import QgsApplication  # noqa: PLC0415

    args = [str(arg).encode("utf-8") for arg in (sys.argv if argv is None else argv)]
    QgsApplication.setPrefixPath(fix_qgis_prefix(), True)
    app = QgsApplication(args, True)
    app.initQgis()
    return app


def application_info() -> dict[str, str]:
    """Datos de versión para mostrar en 'Ayuda > Acerca de' y en los logs."""
    from qgis.core import Qgis  # noqa: PLC0415
    from osgeo import gdal  # noqa: PLC0415

    try:
        from qgis.PyQt.QtCore import QT_VERSION_STR, PYQT_VERSION_STR  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        QT_VERSION_STR = PYQT_VERSION_STR = "desconocida"

    return {
        "MiniGIS": "0.1.0",
        "QGIS": Qgis.version(),
        "GDAL/OGR": gdal.__version__,
        "Qt": QT_VERSION_STR,
        "PyQt": PYQT_VERSION_STR,
        "Python": sys.version.split()[0],
    }


def shutdown_application(app) -> None:
    """Cierra QGIS liberando proveedores GDAL/OGR."""
    app.exitQgis()
