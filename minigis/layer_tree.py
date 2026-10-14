"""Panel 'Capas': árbol de capas con casillas para activar/desactivar."""

from __future__ import annotations

from qgis.core import QgsLayerTreeModel, QgsMapLayer, QgsProject
from qgis.gui import QgsLayerTreeMapCanvasBridge, QgsLayerTreeView, QgsLayerTreeViewDefaultActions
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QMenu,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class LayerTreeDock(QDockWidget):
    """QDockWidget con el árbol de capas del proyecto.

    La sincronización con el canvas se delega en ``QgsLayerTreeMapCanvasBridge``,
    que ya trae QGIS: al destildar la casilla de una capa, el puente actualiza
    automáticamente el conjunto de capas visibles del canvas.
    """

    def __init__(self, canvas, parent: QWidget | None = None) -> None:
        super().__init__("Capas", parent)
        self.setObjectName("dockCapas")
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        self._project = QgsProject.instance()
        self._root = self._project.layerTreeRoot()

        # Modelo + vista + puente con el canvas: la tríada estándar de QGIS.
        self._model = QgsLayerTreeModel(self._root, self)
        # Permite tildar/destildar capas, reordenarlas y renombrarlas.
        self._model.setFlags(
            QgsLayerTreeModel.Flag.AllowNodeChangeVisibility
            | QgsLayerTreeModel.Flag.AllowNodeReorder
            | QgsLayerTreeModel.Flag.AllowNodeRename
            | QgsLayerTreeModel.Flag.AllowLegendChangeState
        )

        self.view = QgsLayerTreeView(self)
        self.view.setHeaderHidden(True)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._show_context_menu)
        self.view.doubleClicked.connect(self._on_double_click)

        # OJO: ``setLayerTreeModel()`` solo deja el modelo "de QGIS" en la vista.
        # Para que Qt construya además el modelo de ítems (selección, geometría
        # de filas, casillas clicables) hay que llamar antes a ``setModel()``,
        # que es lo que hace QGIS internamente al crear el proxy.
        self.view.setModel(self._model)
        self.view.setLayerTreeModel(self._model)

        # El puente mantiene el canvas sincronizado con las casillas del árbol.
        self.bridge = QgsLayerTreeMapCanvasBridge(self._root, canvas, self)
        self.actions = QgsLayerTreeViewDefaultActions(self.view)

        self.toolbar = self._build_toolbar()

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.view)
        self.setWidget(container)

        # La selección puede cambiar sin que haya una capa "actual" (por ejemplo
        # al agregar nodos), así que escuchamos todas las señales relevantes.
        self.view.currentLayerChanged.connect(lambda *_: self._update_actions())
        selection_model = self.view.selectionModel()
        if selection_model is not None:
            selection_model.selectionChanged.connect(lambda *_: self._update_actions())
        # El puente avisa cuando cambia el conjunto de capas del canvas.
        self.bridge.canvasLayersChanged.connect(lambda *_: self._update_actions())
        self._update_actions()

    # ------------------------------------------------------------------ API

    @property
    def model(self):
        """Modelo del árbol (expuesto para tests)."""
        return self._model

    def root(self):
        """Raíz del árbol de capas del proyecto."""
        return self._root

    def selected_layers(self) -> list[QgsMapLayer]:
        """Capas seleccionadas en el árbol (una o varias)."""
        layers = [layer for layer in self.view.selectedLayers() if layer is not None]
        if layers:
            return layers
        return [node.layer() for node in self.view.selectedNodes() if node.layer() is not None]

    def current_layer(self) -> QgsMapLayer | None:
        """Capa "activa": la última sobre la que se hizo clic o la seleccionada."""
        layer = self.view.currentLayer()
        if layer is not None:
            return layer
        layers = self.selected_layers()
        return layers[0] if layers else None

    def top_level_nodes(self):
        """Nodos de primer nivel: una entrada por capa cargada."""
        return list(self._root.children())

    def set_layer_visible(self, layer: QgsMapLayer, visible: bool) -> bool:
        """Marca/desmarca la casilla de una capa. Devuelve el estado resultante."""
        node = self._root.findLayer(layer.id())
        if node is None:
            return False
        node.setItemVisibilityChecked(visible)
        return node.itemVisibilityChecked()

    def is_layer_visible(self, layer: QgsMapLayer) -> bool:
        node = self._root.findLayer(layer.id())
        return bool(node is not None and node.itemVisibilityChecked())

    # --------------------------------------------------------------- toolbar

    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Capas", self)
        toolbar.setObjectName("toolbarCapas")

        self.action_zoom_to_layer = QAction("Zoom a la capa", self)
        self.action_zoom_to_layer.setToolTip("Acercar la vista a la extensión de la capa seleccionada")
        self.action_zoom_to_layer.triggered.connect(self.zoom_to_selected_layer)
        toolbar.addAction(self.action_zoom_to_layer)

        self.action_remove_layer = QAction("Quitar capa", self)
        self.action_remove_layer.setToolTip("Quitar del proyecto la capa seleccionada (Supr)")
        self.action_remove_layer.setShortcut(Qt.Key.Key_Delete)
        self.action_remove_layer.triggered.connect(self.remove_selected_layers)
        toolbar.addAction(self.action_remove_layer)

        toolbar.addSeparator()
        self.action_show_all = QAction("Mostrar todo", self)
        self.action_show_all.setToolTip("Tildar todas las capas")
        self.action_show_all.triggered.connect(self.show_all_layers)
        toolbar.addAction(self.action_show_all)

        self.action_hide_all = QAction("Ocultar todo", self)
        self.action_hide_all.setToolTip("Destildar todas las capas")
        self.action_hide_all.triggered.connect(self.hide_all_layers)
        toolbar.addAction(self.action_hide_all)

        toolbar.addSeparator()
        self.action_expand_all = QAction("Expandir", self)
        self.action_expand_all.setToolTip("Expandir todos los nodos del árbol")
        self.action_expand_all.triggered.connect(self.view.expandAll)
        toolbar.addAction(self.action_expand_all)

        self.action_collapse_all = QAction("Contraer", self)
        self.action_collapse_all.setToolTip("Contraer todos los nodos del árbol")
        self.action_collapse_all.triggered.connect(self.view.collapseAll)
        toolbar.addAction(self.action_collapse_all)

        toolbar.addSeparator()
        self.action_rename_layer = QAction("Renombrar", self)
        self.action_rename_layer.setToolTip("Renombrar la capa seleccionada")
        self.action_rename_layer.triggered.connect(self.rename_selected_layer)
        toolbar.addAction(self.action_rename_layer)

        return toolbar

    def _update_actions(self) -> None:
        has_selection = bool(self.selected_layers())
        self.action_zoom_to_layer.setEnabled(has_selection)
        self.action_remove_layer.setEnabled(has_selection)
        self.action_rename_layer.setEnabled(has_selection)

    def _show_context_menu(self, position) -> None:
        """Menú contextual del árbol, con las acciones más usadas."""
        node = self.node_for_index(self.view.indexAt(position))
        menu = QMenu(self)

        if node is not None and node.layer() is not None:
            capa = node.layer()
            accion_zoom = QAction("Zoom a la capa", menu)
            accion_zoom.triggered.connect(lambda _checked=False, l=capa: self.zoom_to_layer(l))
            menu.addAction(accion_zoom)
            menu.addAction(self.action_rename_layer)
            menu.addAction(self.action_remove_layer)
            menu.addSeparator()
        menu.addAction(self.action_show_all)
        menu.addAction(self.action_hide_all)
        menu.addSeparator()
        menu.addAction(self.action_expand_all)
        menu.addAction(self.action_collapse_all)
        menu.exec(self.view.viewport().mapToGlobal(position))

    # -------------------------------------------------------- visibilidad

    def show_all_layers(self) -> None:
        """Tilda todas las casillas del árbol."""
        for capa in self._project.mapLayers().values():
            self.set_layer_visible(capa, True)

    def hide_all_layers(self) -> None:
        """Destilda todas las casillas del árbol."""
        for capa in self._project.mapLayers().values():
            self.set_layer_visible(capa, False)

    # -------------------------------------------------------------- acciones

    def _on_double_click(self, index) -> None:
        """Doble clic sobre una capa: hace zoom a esa capa.

        El índice viene del modelo de ítems (proxy), así que se traduce al nodo
        del árbol y de ahí a la capa. Es más fiable que depender de la selección.
        """
        node = self.node_for_index(index)
        if node is None or node.layer() is None:
            self.zoom_to_selected_layer()
            return
        self.zoom_to_layer(node.layer())

    def node_for_index(self, index):
        """Nodo del árbol correspondiente a un índice de la vista (o ``None``)."""
        if index is None or not index.isValid():
            return None
        model = self.view.model()
        source_index = model.mapToSource(index) if hasattr(model, "mapToSource") else index
        return self._model.index2node(source_index)

    def zoom_to_selected_layer(self) -> None:
        """Centra el canvas en la extensión de la capa seleccionada."""
        layer = self.current_layer()
        self.zoom_to_layer(layer)

    def zoom_to_layer(self, layer: QgsMapLayer | None) -> None:
        """Centra el canvas en la extensión de ``layer``."""
        if layer is None or layer.extent().isEmpty():
            return
        canvas = self.bridge.mapCanvas()
        canvas.setExtent(layer.extent())
        canvas.refresh()

    def rename_selected_layer(self) -> bool:
        """Pide un nombre nuevo para la capa seleccionada."""
        from qgis.PyQt.QtWidgets import QInputDialog

        layer = self.current_layer()
        if layer is None:
            return False
        nuevo, aceptado = QInputDialog.getText(
            self, "Renombrar capa", "Nuevo nombre:", text=layer.name()
        )
        if not aceptado or not nuevo.strip():
            return False
        old_name = layer.name()
        layer.setName(nuevo.strip())
        node = self._root.findLayer(layer.id())
        if node is not None:
            node.setName(nuevo.strip())
            self._model.refreshLayerLegend(node)
        self._project.setDirty(True)
        self._project.layerNameChanged.emit(layer, old_name)
        return True

    def remove_selected_layers(self) -> None:
        """Quita del proyecto las capas seleccionadas y sus nodos del árbol."""
        layers = self.selected_layers()
        if not layers:
            return
        ids = [layer.id() for layer in layers]
        # El proyecto se encarga de sacar la capa y su nodo del árbol.
        self._project.removeMapLayers(ids)
