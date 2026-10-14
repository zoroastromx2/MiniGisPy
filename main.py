"""Punto de entrada de MiniGIS.

Uso:
    mini-gis.bat                          # abre la ventana vacía
    mini-gis.bat samples\\poligonos.shp    # abre la ventana con esa capa cargada
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite ejecutar el archivo directamente (python main.py) además de -m.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from minigis.app import MainWindow  # noqa: E402
from minigis.bootstrap import create_application, setup_environment, shutdown_application  # noqa: E402

#: Opciones que consumen el argumento siguiente (no son rutas de capas).
OPCIONES_CON_VALOR = {"--captura"}


def _rutas_de_capas(args: list[str]) -> list[str]:
    """Extrae las rutas de capas de la línea de comandos, salteando las opciones."""
    rutas: list[str] = []
    indice = 0
    while indice < len(args):
        arg = args[indice]
        if arg in OPCIONES_CON_VALOR:
            indice += 2
            continue
        if not arg.startswith("-"):
            rutas.append(arg)
        indice += 1
    return rutas


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = _rutas_de_capas(args)

    setup_environment()
    app = create_application([sys.argv[0]])
    app.setApplicationName("MiniGIS")
    app.setOrganizationName("MiniGIS")

    # Modo diagnóstico: verifica el entorno y sale sin abrir ventana.
    if "--check" in args:
        from minigis.bootstrap import application_info

        for key, value in application_info().items():
            print(f"{key}: {value}")
        shutdown_application(app)
        return 0

    window = MainWindow()
    window.show()

    errors: list[str] = []
    for path in paths:
        try:
            window.load_layer(path)
        except Exception as error:  # se informa por consola y se sigue
            errors.append(f"{path}: {error}")

    for message in errors:
        print(f"[MiniGIS] No se pudo abrir {message}", file=sys.stderr)

    # Modo captura: útil para documentar o verificar sin intervención manual.
    if "--captura" in args:
        _tomar_captura_y_salir(window, args, Path("artifacts") / "captura-minigis.png")

    try:
        return app.exec()
    finally:
        shutdown_application(app)


def _tomar_captura_y_salir(window, args: list[str], por_defecto: Path) -> None:
    """Guarda una captura de la ventana y cierra la aplicación."""
    from qgis.PyQt.QtCore import QTimer

    destino = por_defecto
    if "--captura" in args:
        posicion = args.index("--captura")
        if posicion + 1 < len(args) and not args[posicion + 1].startswith("-"):
            destino = Path(args[posicion + 1])
    destino.parent.mkdir(parents=True, exist_ok=True)

    def capturar() -> None:
        imagen = window.grab()
        if imagen.save(str(destino)):
            print(f"[MiniGIS] Captura guardada en {destino}")
        else:
            print(f"[MiniGIS] No se pudo guardar la captura en {destino}", file=sys.stderr)
        window.close()

    # Se espera a que el canvas termine de dibujar antes de capturar.
    QTimer.singleShot(1500, capturar)


if __name__ == "__main__":
    raise SystemExit(main())
