"""Ventana principal de MiniGIS: menús, canvas y panel de capas."""

from __future__ import annotations

from pathlib import Path

from qgis.core import Qgis, QgsMessageLog, QgsProject
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QAction, QKeySequence
from qgis.PyQt.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QWidget,
)

from . import __version__
from .bootstrap import application_info
from .canvas import MapCanvas, NavigationToolbar, StatusInfoWidget
from .layer_tree import LayerTreeDock
from .layers import VECTOR_EXTENSIONS, LayerOpenError, load_vector_layer
from .symbols import apply_default_style

#: Filtro del diálogo de apertura (los mismos formatos que acepta el arrastre).
VECTOR_FILTER = "Fuentes vectoriales ({})".format(
    " ".join(f"*{extension}" for extension in VECTOR_EXTENSIONS)
)
SHAPEFILE_FILTER = "Shapefiles (*.shp)"


class MainWindow(QMainWindow):
    """Ventana con menú Archivo, canvas central y árbol de capas acoplado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"MiniGIS {__version__}")
        self.resize(1100, 720)
        self.setAcceptDrops(True)
        self.setDockNestingEnabled(True)

        self.project = QgsProject.instance()

        # --- widgets principales -------------------------------------------
        self.map_canvas = MapCanvas(self)
        self.setCentralWidget(self.map_canvas)

        self.layer_dock = LayerTreeDock(self.map_canvas, self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.layer_dock)

        self.nav_toolbar = NavigationToolbar(self.map_canvas, self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.nav_toolbar)

        self.status_info = StatusInfoWidget(self.map_canvas, self)
        self.statusBar().addPermanentWidget(self.status_info)
        self.statusBar().showMessage("Listo. Abrí un shapefile con Archivo ▸ Abrir capa vectorial…")

        # --- acciones y menús ----------------------------------------------
        self._create_actions()
        self._create_menus()

        # Al agregar o quitar capas actualizamos títulos y la vista completa.
        self.project.layersAdded.connect(self._on_layers_changed)
        self.project.layersRemoved.connect(self._on_layers_removed)

    # ------------------------------------------------------------- acciones

    def _create_actions(self) -> None:
        self.action_open = QAction("Abrir capa vectorial…", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.setStatusTip("Abrir un shapefile u otra fuente vectorial")
        self.action_open.triggered.connect(self.open_vector_dialog)

        self.action_close_all = QAction("Cerrar todas las capas", self)
        self.action_close_all.triggered.connect(self.close_all_layers)

        self.action_exit = QAction("Salir", self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)

        self.action_remove_layer = QAction("Quitar capa seleccionada", self)
        self.action_remove_layer.setShortcut(Qt.Key.Key_Delete)
        self.action_remove_layer.triggered.connect(self.layer_dock.remove_selected_layers)

        self.action_zoom_layer = QAction("Zoom a la capa seleccionada", self)
        self.action_zoom_layer.triggered.connect(self.layer_dock.zoom_to_selected_layer)

        self.action_about = QAction("Acerca de MiniGIS", self)
        self.action_about.triggered.connect(self.show_about)

    def _create_menus(self) -> None:
        menu_file = self.menuBar().addMenu("&Archivo")
        menu_file.addAction(self.action_open)
        menu_file.addSeparator()
        menu_file.addAction(self.action_close_all)
        menu_file.addSeparator()
        menu_file.addAction(self.action_exit)

        menu_view = self.menuBar().addMenu("&Ver")
        menu_view.addAction(self.nav_toolbar.action_zoom_in)
        menu_view.addAction(self.nav_toolbar.action_zoom_out)
        menu_view.addAction(self.nav_toolbar.action_pan)
        menu_view.addSeparator()
        menu_view.addAction(self.nav_toolbar.action_full_extent)
        menu_view.addSeparator()
        menu_view.addAction(self.layer_dock.toggleViewAction())

        menu_layer = self.menuBar().addMenu("&Capa")
        menu_layer.addAction(self.action_zoom_layer)
        menu_layer.addAction(self.action_remove_layer)
        menu_layer.addSeparator()
        menu_layer.addAction(self.action_close_all)

        menu_help = self.menuBar().addMenu("A&yuda")
        menu_help.addAction(self.action_about)

    # ------------------------------------------------------------ operaciones

    def open_vector_dialog(self) -> int:
        """Muestra el diálogo 'Abrir' y carga lo elegido.

        Devuelve la cantidad de capas cargadas (0 si el usuario canceló), lo que
        hace verificable el flujo desde un test automatizado.
        """
        start_dir = self._default_directory()
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "Abrir capa vectorial",
            start_dir,
            f"{SHAPEFILE_FILTER};;{VECTOR_FILTER};;Todos los archivos (*)",
        )
        if not paths:
            return 0

        loaded = 0
        errors: list[str] = []
        for raw_path in paths:
            try:
                self.load_layer(raw_path)
                loaded += 1
            except (LayerOpenError, FileNotFoundError) as error:
                errors.append(str(error))

        if errors:
            QMessageBox.warning(self, "No se pudieron abrir algunas capas", "\n".join(errors))
        return loaded

    def load_layer(self, path: str | Path) -> "QgsVectorLayer":
        """Carga una fuente vectorial, le da estilo, la agrega al proyecto.

        El canvas se encuadra a la extensión de las capas visibles.
        """
        layer = load_vector_layer(path)
        color_index = len(self.project.mapLayers())
        style_description = apply_default_style(layer, color_index=color_index)
        self.project.addMapLayer(layer)
        self.statusBar().showMessage(
            f"Capa '{layer.name()}' cargada: {layer.featureCount()} entidades ({style_description})",
            8000,
        )
        QgsMessageLog.logMessage(
            f"Capa cargada: {layer.source()} — {style_description}", "MiniGIS", Qgis.MessageLevel.Info
        )
        return layer

    def close_all_layers(self) -> None:
        self.project.removeAllMapLayers()
        self.statusBar().showMessage("Se quitaron todas las capas", 5000)

    def show_about(self) -> None:
        info = application_info()
        details = "\n".join(f"{key}: {value}" for key, value in info.items())
        QMessageBox.about(
            self,
            "Acerca de MiniGIS",
            "<h3>MiniGIS</h3>"
            "<p>Visor SIG mínimo construido sobre GDAL/OGR y las librerías de QGIS.</p>"
            f"<pre>{details}</pre>",
        )

    # ------------------------------------------------------------- auxiliares

    def _default_directory(self) -> str:
        """Carpeta de inicio del diálogo: la de la última capa o ``samples/``."""
        layers = list(self.project.mapLayers().values())
        if layers:
            return str(Path(layers[-1].source()).parent)
        samples = Path(__file__).resolve().parent.parent / "samples"
        return str(samples if samples.is_dir() else Path.home())

    def _on_layers_changed(self, layers) -> None:
        if not layers:
            return
        self._update_window_title()
        # Encuadrar mirando las capas *visibles* (las destildadas no cuentan).
        extent = self.map_canvas.fullExtent()
        if extent is not None and not extent.isEmpty():
            self.map_canvas.setExtent(extent)
            # Al abrir hay que esperar a que la ventana tenga su tamaño final:
            # si no, el canvas todavía mide 100x30 y la vista queda mal encuadrada.
            QTimer.singleShot(0, self._fit_pending_layers)
        self.map_canvas.refresh()

    def _fit_pending_layers(self) -> None:
        extent = self.map_canvas.fullExtent()
        if extent is not None and not extent.isEmpty():
            self.map_canvas.setExtent(extent)
            self.map_canvas.refresh()

    def _on_layers_removed(self, layer_ids) -> None:
        self._update_window_title()
        self.map_canvas.refresh()
        if not self.project.mapLayers():
            self.status_info.reset_coordinates()
            self.statusBar().showMessage("No hay capas en el proyecto", 5000)

    def _update_window_title(self) -> None:
        count = len(self.project.mapLayers())
        suffix = f" — {count} capa{'s' if count != 1 else ''}"
        self.setWindowTitle(f"MiniGIS {__version__}{suffix if count else ''}")

    # ------------------------------------------------- arrastrar y soltar

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if not paths:
            return
        event.acceptProposedAction()
        errors: list[str] = []
        for path in paths:
            try:
                self.load_layer(path)
            except (LayerOpenError, FileNotFoundError) as error:
                errors.append(str(error))
        if errors:
            QMessageBox.warning(self, "No se pudieron abrir algunos archivos", "\n".join(errors))


def run(argv: list[str] | None = None) -> int:
    """Crea la aplicación, muestra la ventana y entra en el bucle de eventos."""
    from .bootstrap import create_application, setup_environment, shutdown_application

    setup_environment()
    app = create_application(argv)
    window = MainWindow()
    window.show()
    try:
        return app.exec()
    finally:
        shutdown_application(app)


__all__ = ["MainWindow", "run", "QApplication"]
