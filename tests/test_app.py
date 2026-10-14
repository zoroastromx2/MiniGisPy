"""Tests de integración de la ventana: cargar, listar, activar/desactivar capas."""

from __future__ import annotations

import pytest

from qgis.core import QgsProject

from tests.helpers import grab_widget, process_events, wait_until


def _cargar(window, ruta):
    layer = window.load_layer(ruta)
    process_events(200)
    return layer


def test_ventana_arranca_vacia(window):
    assert window.windowTitle().startswith("MiniGIS")
    assert window.layer_dock.top_level_nodes() == []
    assert window.layer_dock.model.rowCount() == 0
    assert "Abrir capa vectorial" in window.action_open.text()


def test_abrir_desde_el_menu_agrega_la_capa_al_arbol(window, samples):
    """Simula el flujo real: menú Archivo ▸ Abrir capa vectorial."""
    from qgis.PyQt.QtWidgets import QFileDialog

    def fake_get_open_file_names(*_args, **_kwargs):
        return ([str(samples["poligonos"])], "Shapefiles (*.shp)")

    original = QFileDialog.getOpenFileNames
    QFileDialog.getOpenFileNames = staticmethod(fake_get_open_file_names)
    try:
        assert window.open_vector_dialog() == 1
    finally:
        QFileDialog.getOpenFileNames = original

    process_events(300)
    assert len(QgsProject.instance().mapLayers()) == 1
    # El árbol tiene una entrada: la capa cargada.
    nodos = window.layer_dock.top_level_nodes()
    assert len(nodos) == 1
    assert nodos[0].name() == "poligonos"
    assert window.layer_dock.model.rowCount() == 1


def test_la_capa_se_dibuja_en_el_canvas(window, samples):
    layer = _cargar(window, samples["lineas"])
    wait_until(lambda: window.map_canvas.layers() == [layer])
    assert [l.name() for l in window.map_canvas.layers()] == ["lineas"]
    # La vista quedó encuadrada sobre la capa (no en una extensión vacía).
    assert not window.map_canvas.extent().isEmpty()
    assert window.map_canvas.scale() > 0


def test_activar_y_desactivar_la_capa(window, samples):
    layer = _cargar(window, samples["poligonos"])
    assert window.layer_dock.is_layer_visible(layer)

    # Destildar la casilla del árbol quita la capa del canvas...
    window.layer_dock.set_layer_visible(layer, False)
    process_events(200)
    assert window.layer_dock.is_layer_visible(layer) is False
    assert window.map_canvas.layers() == []

    # ...y volver a tildarla la muestra otra vez.
    window.layer_dock.set_layer_visible(layer, True)
    process_events(200)
    assert window.layer_dock.is_layer_visible(layer) is True
    assert [l.name() for l in window.map_canvas.layers()] == ["poligonos"]


def test_visibilidad_independiente_entre_varias_capas(window, samples):
    poligonos = _cargar(window, samples["poligonos"])
    puntos = _cargar(window, samples["puntos"])
    process_events(300)
    assert window.layer_dock.model.rowCount() == 2

    window.layer_dock.set_layer_visible(poligonos, False)
    process_events(200)
    assert [l.name() for l in window.map_canvas.layers()] == ["puntos"]

    window.layer_dock.set_layer_visible(puntos, False)
    process_events(200)
    assert window.map_canvas.layers() == []


def test_quitar_capa_del_arbol(window, samples):
    layer = _cargar(window, samples["puntos"])
    nodo = window.layer_dock.root().findLayer(layer.id())
    window.layer_dock.view.setCurrentNode(nodo)
    process_events(100)

    window.layer_dock.remove_selected_layers()
    process_events(200)
    assert QgsProject.instance().mapLayers() == {}
    assert window.layer_dock.top_level_nodes() == []
    assert window.map_canvas.layers() == []


def test_zoom_a_la_capa_seleccionada(window, samples):
    layer = _cargar(window, samples["puntos"])
    nodo = window.layer_dock.root().findLayer(layer.id())
    window.layer_dock.view.setCurrentNode(nodo)
    process_events(100)
    assert window.layer_dock.current_layer() is layer

    window.layer_dock.zoom_to_selected_layer()
    process_events(200)
    # QGIS respeta la relación de aspecto del canvas, así que la capa queda
    # contenida en la vista aunque las extensiones no coincidan exactamente.
    extents = window.map_canvas.extent()
    assert extents.contains(layer.extent()) or extents.contains(layer.extent().center())


def test_cerrar_todas_las_capas(window, samples):
    _cargar(window, samples["poligonos"])
    _cargar(window, samples["puntos"])
    process_events(200)
    window.close_all_layers()
    process_events(200)
    assert window.layer_dock.top_level_nodes() == []
    assert window.map_canvas.layers() == []


def test_archivo_invalido_no_rompe_la_ventana(window, tmp_path):
    from minigis.layers import LayerOpenError

    malo = tmp_path / "malo.shp"
    malo.write_text("no soy un shapefile", encoding="utf-8")
    with pytest.raises(LayerOpenError):
        window.load_layer(malo)
    assert QgsProject.instance().mapLayers() == {}
    assert window.layer_dock.top_level_nodes() == []


def test_captura_de_pantalla(window, samples, artifacts_dir):
    """Genera artifacts/ventana-minigis.png con las tres capas cargadas."""
    for clave in ("poligonos", "lineas", "puntos"):
        _cargar(window, samples[clave])
    wait_until(lambda: len(window.map_canvas.layers()) == 3, timeout_ms=8000)
    process_events(600)

    ruta = grab_widget(window, artifacts_dir / "ventana-minigis.png")
    assert ruta.stat().st_size > 10_000, "La captura parece vacía"
