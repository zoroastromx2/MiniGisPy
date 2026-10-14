"""Verificación de extremo a extremo.

Levanta la ventana real (sin pantalla), carga los shapefiles de ejemplo, prueba
la casilla de activar/desactivar del árbol de capas y guarda capturas en
``artifacts/``.

Uso:
    dev-env.bat scripts\\verificar_app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

from minigis.bootstrap import application_info, create_application, setup_environment  # noqa: E402

ARTIFACTS = PROJECT_ROOT / "artifacts"
SAMPLES = PROJECT_ROOT / "samples"

resultados: list[tuple[str, bool, str]] = []


def comprobar(nombre: str, condicion: bool, detalle: str = "") -> None:
    resultados.append((nombre, bool(condicion), detalle))
    marca = "OK  " if condicion else "FALLA"
    print(f"[{marca}] {nombre}" + (f" — {detalle}" if detalle else ""))


def main() -> int:
    setup_environment(profile_dir=ARTIFACTS / "perfil-qgis")
    app = create_application(["verificar_app"])

    from qgis.core import QgsProject
    from qgis.PyQt.QtWidgets import QFileDialog

    from minigis.app import MainWindow
    from tests.helpers import grab_widget, process_events, wait_until

    print("== Entorno ==")
    for clave, valor in application_info().items():
        print(f"  {clave}: {valor}")

    ventana = MainWindow()
    ventana.resize(1280, 800)
    ventana.show()
    process_events(400)

    print("\n== Estado inicial ==")
    comprobar("La ventana arranca sin capas", QgsProject.instance().mapLayers() == {})
    comprobar("El árbol de capas está vacío", ventana.layer_dock.model.rowCount() == 0)
    comprobar("Existe el menú Archivo con 'Abrir capa vectorial'", "Abrir capa vectorial" in ventana.action_open.text())
    comprobar("Hay barra de navegación y panel de capas",
              ventana.nav_toolbar.isVisible() and ventana.layer_dock.isVisible())
    grab_widget(ventana, ARTIFACTS / "01-ventana-vacia.png")

    print("\n== Carga vía diálogo (simulado) ==")
    original = QFileDialog.getOpenFileNames
    QFileDialog.getOpenFileNames = staticmethod(
        lambda *a, **k: ([str(SAMPLES / "poligonos.shp")], "Shapefiles (*.shp)")
    )
    try:
        cargadas = ventana.open_vector_dialog()
    finally:
        QFileDialog.getOpenFileNames = original
    process_events(400)
    comprobar("El diálogo cargó 1 capa", cargadas == 1, f"cargadas={cargadas}")
    comprobar("El árbol muestra 1 entrada", ventana.layer_dock.model.rowCount() == 1)

    print("\n== Carga de las tres capas y dibujo en el canvas ==")
    for clave in ("lineas", "puntos"):
        capa = ventana.load_layer(SAMPLES / f"{clave}.shp")
        print(f"  cargada: {capa.name()} ({capa.featureCount()} entidades)")
    process_events(600)

    capas_proyecto = list(QgsProject.instance().mapLayers().values())
    comprobar("El proyecto tiene 3 capas", len(capas_proyecto) == 3, str([c.name() for c in capas_proyecto]))
    comprobar("El árbol tiene 3 nodos de primer nivel", len(ventana.layer_dock.top_level_nodes()) == 3)
    comprobar("El canvas dibuja las 3 capas",
              wait_until(lambda: len(ventana.map_canvas.layers()) == 3, timeout_ms=8000),
              f"canvas={[c.name() for c in ventana.map_canvas.layers()]}")
    comprobar("La vista quedó encuadrada", not ventana.map_canvas.extent().isEmpty(),
              f"escala 1:{round(ventana.map_canvas.scale())}")

    # Esperar a que termine el primer render y capturar con la vista encuadrada.
    wait_until(lambda: not ventana.map_canvas.isDrawing(), timeout_ms=8000)
    ventana.nav_toolbar.action_full_extent.trigger()
    process_events(500)
    grab_widget(ventana, ARTIFACTS / "02-tres-capas.png")
    grab_widget(ventana.map_canvas, ARTIFACTS / "03-canvas.png")

    print("\n== Árbol de capas: activar / desactivar ==")
    poligonos = next(c for c in capas_proyecto if c.name() == "poligonos")
    comprobar("La casilla de 'poligonos' arranca tildada", ventana.layer_dock.is_layer_visible(poligonos))

    ventana.layer_dock.set_layer_visible(poligonos, False)
    process_events(300)
    visibles = [c.name() for c in ventana.map_canvas.layers()]
    comprobar("Al destildar, la capa desaparece del canvas", "poligonos" not in visibles, f"visibles={visibles}")
    wait_until(lambda: not ventana.map_canvas.isDrawing(), timeout_ms=8000)
    grab_widget(ventana, ARTIFACTS / "04-poligonos-oculto.png")

    ventana.layer_dock.set_layer_visible(poligonos, True)
    process_events(300)
    visibles = [c.name() for c in ventana.map_canvas.layers()]
    comprobar("Al volver a tildar, la capa reaparece", "poligonos" in visibles, f"visibles={visibles}")

    print("\n== Zoom a la capa y vista completa ==")
    nodo = ventana.layer_dock.root().findLayer(poligonos.id())
    ventana.layer_dock.view.setCurrentNode(nodo)
    process_events(150)
    comprobar("La capa seleccionada se detecta", ventana.layer_dock.current_layer() is poligonos)
    ventana.layer_dock.zoom_to_selected_layer()
    process_events(400)
    # QGIS ajusta la extensión respetando la relación de aspecto del canvas, así
    # que no se compara igualdad: alcanza con que la capa quede dentro de la vista.
    extension_canvas = ventana.map_canvas.extent()
    centro_capa = poligonos.extent().center()
    comprobar(
        "El zoom a la capa la deja dentro de la vista",
        extension_canvas.contains(poligonos.extent()) or extension_canvas.contains(centro_capa),
        f"canvas={extension_canvas.toString(2)} capa={poligonos.extent().toString(2)}",
    )
    wait_until(lambda: not ventana.map_canvas.isDrawing(), timeout_ms=8000)
    grab_widget(ventana, ARTIFACTS / "05-zoom-a-poligonos.png")

    ventana.nav_toolbar.action_full_extent.trigger()
    process_events(400)
    comprobar("Vista completa vuelve a encuadrar todo", not ventana.map_canvas.extent().isEmpty())

    print("\n== Quitar capas ==")
    ventana.layer_dock.remove_selected_layers()
    process_events(300)
    comprobar("Quedan 2 capas tras quitar la seleccionada", len(QgsProject.instance().mapLayers()) == 2)

    ventana.close_all_layers()
    process_events(300)
    comprobar("Cerrar todo deja el proyecto vacío",
              QgsProject.instance().mapLayers() == {} and ventana.map_canvas.layers() == [])

    print("\n== Manejo de errores ==")
    invalido = ARTIFACTS / "invalido.shp"
    invalido.parent.mkdir(parents=True, exist_ok=True)
    invalido.write_text("no soy un shapefile", encoding="utf-8")
    try:
        ventana.load_layer(invalido)
        comprobar("Un archivo inválido lanza un error controlado", False, "no lanzó excepción")
    except Exception as error:  # noqa: BLE001 - se reporta el tipo de error
        comprobar("Un archivo inválido lanza un error controlado", True, type(error).__name__)
    comprobar("Tras el error el proyecto sigue vacío", QgsProject.instance().mapLayers() == {})

    print("\n== Capturas generadas ==")
    for png in sorted(ARTIFACTS.glob("*.png")):
        print(f"  {png.relative_to(PROJECT_ROOT)}  ({png.stat().st_size / 1024:.0f} KB)")

    fallas = [nombre for nombre, ok, _ in resultados if not ok]
    print(f"\nResultado: {len(resultados) - len(fallas)}/{len(resultados)} comprobaciones OK")
    if fallas:
        print("Fallaron: " + ", ".join(fallas))

    app.exitQgis()
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
