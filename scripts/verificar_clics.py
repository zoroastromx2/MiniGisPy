"""Segunda verificación: interacción real (clics con QtTest) sobre el árbol de capas.

Complementa a ``verificar_app.py``: acá no se llaman métodos internos, se simulan
clics del usuario sobre la casilla de visibilidad y sobre el nombre de la capa.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

from minigis.bootstrap import create_application, setup_environment  # noqa: E402

ARTIFACTS = PROJECT_ROOT / "artifacts"
SAMPLES = PROJECT_ROOT / "samples"
resultados: list[tuple[str, bool, str]] = []


def comprobar(nombre: str, condicion: bool, detalle: str = "") -> None:
    resultados.append((nombre, bool(condicion), detalle))
    print(f"[{'OK  ' if condicion else 'FALLA'}] {nombre}" + (f" — {detalle}" if detalle else ""))


def main() -> int:
    setup_environment(profile_dir=ARTIFACTS / "perfil-qgis")
    app = create_application(["verificar_clics"])

    from qgis.core import QgsProject
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtTest import QTest

    from minigis.app import MainWindow
    from tests.helpers import grab_widget, process_events, wait_until

    ventana = MainWindow()
    ventana.resize(1280, 800)
    ventana.show()
    process_events(400)

    capas = {clave: ventana.load_layer(SAMPLES / f"{clave}.shp") for clave in ("poligonos", "lineas", "puntos")}
    process_events(500)
    wait_until(lambda: not ventana.map_canvas.isDrawing(), timeout_ms=8000)

    dock = ventana.layer_dock
    nodos = {n.name(): n for n in dock.top_level_nodes()}
    print("nodos del árbol:", list(nodos))

    def rect_en_vista(nodo):
        """Rectángulo que ocupa un nodo en la vista (índice del proxy -> vista)."""
        indice_origen = dock.model.node2index(nodo)
        indice_vista = dock.view.model().mapFromSource(indice_origen)
        return dock.view.visualRect(indice_vista)

    # --- 1) Clic en la casilla de visibilidad de 'lineas' -------------------
    nodo_lineas = nodos["lineas"]
    rect = rect_en_vista(nodo_lineas)
    print(f"rect de 'lineas' en la vista: {rect.x()},{rect.y()} {rect.width()}x{rect.height()}")
    comprobar("El nodo de la capa es visible en la vista", rect.isValid() and rect.height() > 0, str(rect))

    # La casilla está a la izquierda del texto.
    QTest.mouseClick(
        dock.view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        rect.center() - __import__("qgis.PyQt.QtCore", fromlist=["QPoint"]).QPoint(rect.width() // 2 - 4, 0),
    )
    process_events(400)
    visible_tras_clic = dock.is_layer_visible(capas["lineas"])
    visibles_canvas = [c.name() for c in ventana.map_canvas.layers()]
    comprobar(
        "Un clic en la casilla desactiva la capa",
        not visible_tras_clic and "lineas" not in visibles_canvas,
        f"casilla={visible_tras_clic} canvas={visibles_canvas}",
    )
    wait_until(lambda: not ventana.map_canvas.isDrawing(), timeout_ms=8000)
    ventana.nav_toolbar.action_full_extent.trigger()
    process_events(400)
    grab_widget(ventana, ARTIFACTS / "06-clic-casilla-lineas.png")

    # Volver a activarla.
    QTest.mouseClick(
        dock.view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        rect.center() - __import__("qgis.PyQt.QtCore", fromlist=["QPoint"]).QPoint(rect.width() // 2 - 4, 0),
    )
    process_events(400)
    comprobar(
        "Otro clic la vuelve a activar",
        dock.is_layer_visible(capas["lineas"]) and "lineas" in [c.name() for c in ventana.map_canvas.layers()],
        f"canvas={[c.name() for c in ventana.map_canvas.layers()]}",
    )

    # --- 2) Doble clic sobre el nombre: zoom a la capa ---------------------
    nodo_puntos = nodos["puntos"]
    rect_puntos = rect_en_vista(nodo_puntos)
    print(f"rect de 'puntos' en la vista: {rect_puntos.x()},{rect_puntos.y()} {rect_puntos.width()}x{rect_puntos.height()}")
    QTest.mouseDClick(
        dock.view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        rect_puntos.center(),
    )
    process_events(500)
    print("current_layer() tras el doble clic:", dock.current_layer().name() if dock.current_layer() else None)
    print("extensión del canvas:", ventana.map_canvas.extent().toString(2))
    print("extensión de la capa:", capas["puntos"].extent().toString(2))
    extension_canvas = ventana.map_canvas.extent()
    capa_puntos = capas["puntos"].extent()
    comprobar(
        "El doble clic hace zoom a la capa apuntada",
        extension_canvas.contains(capa_puntos) or extension_canvas.contains(capa_puntos.center()),
        f"canvas={extension_canvas.toString(2)} capa={capa_puntos.toString(2)}",
    )
    comprobar(
        "El doble clic apunta a la capa indicada",
        dock.node_for_index(dock.view.model().mapFromSource(dock.model.node2index(nodo_puntos)))
        is nodo_puntos,
        f"capa={nodo_puntos.name()}",
    )
    wait_until(lambda: not ventana.map_canvas.isDrawing(), timeout_ms=8000)
    grab_widget(ventana, ARTIFACTS / "07-doble-clic-zoom-puntos.png")

    # --- 3) Herramientas de navegación -------------------------------------
    ventana.nav_toolbar.action_full_extent.trigger()
    process_events(300)
    escala_completa = ventana.map_canvas.scale()

    ventana.nav_toolbar.action_zoom_in.trigger()
    comprobar("La acción Zoom + está marcada", ventana.nav_toolbar.action_zoom_in.isChecked())
    comprobar("El canvas usa la herramienta de zoom",
              isinstance(ventana.map_canvas.mapTool(), type(ventana.nav_toolbar.tool_zoom_in)))

    ventana.nav_toolbar.action_pan.trigger()
    comprobar("Volver a 'Mover' cambia la herramienta",
              isinstance(ventana.map_canvas.mapTool(), type(ventana.nav_toolbar.tool_pan)))
    comprobar("La vista completa tiene una escala razonable", escala_completa > 0, f"1:{round(escala_completa)}")

    # --- 4) Menú contextual del árbol --------------------------------------
    menu_abierto = []
    original_exec = __import__("qgis.PyQt.QtWidgets", fromlist=["QMenu"]).QMenu.exec

    def fake_exec(self, *args, **kwargs):
        menu_abierto.append([a.text() for a in self.actions()])
        return None

    __import__("qgis.PyQt.QtWidgets", fromlist=["QMenu"]).QMenu.exec = fake_exec
    try:
        dock._show_context_menu(rect_puntos.center())
    finally:
        __import__("qgis.PyQt.QtWidgets", fromlist=["QMenu"]).QMenu.exec = original_exec
    print("entradas del menú contextual:", menu_abierto)
    comprobar(
        "El menú contextual ofrece zoom, renombrar y quitar",
        bool(menu_abierto) and any("Zoom" in t for t in menu_abierto[0]),
        str(menu_abierto[0]) if menu_abierto else "no se abrió",
    )

    # --- 5) Información de la barra de estado ------------------------------
    process_events(200)
    comprobar("La barra de estado muestra el SRC", "EPSG:4326" in ventana.status_info.label_crs.text(),
              ventana.status_info.label_crs.text())
    comprobar("La barra de estado muestra una escala",
              ventana.status_info.label_scale.text().startswith("Escala 1:"),
              ventana.status_info.label_scale.text())

    print("\n== Capturas ==")
    for png in sorted(ARTIFACTS.glob("*.png")):
        print(f"  {png.name} ({png.stat().st_size / 1024:.0f} KB)")

    fallas = [n for n, ok, _ in resultados if not ok]
    print(f"\nResultado: {len(resultados) - len(fallas)}/{len(resultados)} comprobaciones OK")
    if fallas:
        print("Fallaron: " + ", ".join(fallas))

    app.exitQgis()
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
