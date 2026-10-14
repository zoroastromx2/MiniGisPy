"""El lienzo (canvas) donde se dibujan las capas."""

from __future__ import annotations

from qgis.core import QgsProject
from qgis.gui import QgsMapCanvas, QgsMapTool, QgsMapToolPan, QgsMapToolZoom
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QAction, QActionGroup, QColor
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QToolBar, QWidget


class MapCanvas(QgsMapCanvas):
    """``QgsMapCanvas`` con el aspecto y los ajustes que queremos por defecto."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCanvasColor(QColor(255, 255, 255))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.enableAntiAliasing(True)
        self.setParallelRenderingEnabled(True)
        self.setDestinationCrs(QgsProject.instance().crs())
        self.refresh()

    def zoom_to_full_extent(self) -> None:
        """Ajusta la vista a la extensión de todas las capas visibles."""
        extent = self.fullExtent()
        if extent is not None and not extent.isEmpty():
            self.setExtent(extent)
            self.refresh()


class NavigationToolbar(QToolBar):
    """Barra con las herramientas de navegación (mano, zoom, vista completa).

    Es autocontenida: crea sus acciones, las agrupa en exclusiva y activa la
    herramienta de desplazamiento al arrancar, igual que QGIS.
    """

    def __init__(self, canvas: MapCanvas, parent: QWidget | None = None) -> None:
        super().__init__("Navegación", parent)
        self.setObjectName("toolbarNavegacion")
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.action_group = QActionGroup(self)
        self.action_group.setExclusive(True)

        self.action_zoom_out, self.tool_zoom_out = self._add_tool(
            canvas, "Zoom -", QgsMapToolZoom(canvas, True), "Alejar (arrastrar un rectángulo)"
        )
        self.action_zoom_in, self.tool_zoom_in = self._add_tool(
            canvas, "Zoom +", QgsMapToolZoom(canvas, False), "Acercar (arrastrar un rectángulo)"
        )
        self.action_pan, self.tool_pan = self._add_tool(
            canvas, "Mover", QgsMapToolPan(canvas), "Desplazar el mapa (mantener presionado)"
        )

        self.addSeparator()
        self.action_full_extent = QAction("Vista completa", self)
        self.action_full_extent.setToolTip("Ajustar la vista a todas las capas (Ctrl+Shift+F)")
        self.action_full_extent.setShortcut("Ctrl+Shift+F")
        self.action_full_extent.triggered.connect(canvas.zoom_to_full_extent)
        self.addAction(self.action_full_extent)

        self.action_pan.setChecked(True)
        canvas.setMapTool(self.tool_pan)

    def _add_tool(
        self, canvas: MapCanvas, text: str, tool: QgsMapTool, tooltip: str
    ) -> tuple[QAction, QgsMapTool]:
        action = QAction(text, self)
        action.setCheckable(True)
        action.setToolTip(tooltip)
        self.action_group.addAction(action)
        self.addAction(action)
        action.triggered.connect(lambda _checked=False, t=tool: canvas.setMapTool(t))
        return action, tool


class StatusInfoWidget(QWidget):
    """Etiquetas de la barra de estado: coordenada, escala y SRC del proyecto."""

    def __init__(self, canvas: MapCanvas, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(14)

        self.label_coords = QLabel("Coordenada: -")
        self.label_coords.setMinimumWidth(260)
        self.label_scale = QLabel("Escala: -")
        self.label_crs = QLabel()

        for label in (self.label_coords, self.label_scale, self.label_crs):
            layout.addWidget(label)

        canvas.xyCoordinates.connect(self._on_xy)
        canvas.scaleChanged.connect(self._on_scale)
        QgsProject.instance().crsChanged.connect(self._on_crs)

        self._on_scale(canvas.scale())
        self._on_crs()

    def _on_xy(self, point) -> None:
        self.label_coords.setText(f"Coordenada: {point.x():.2f}, {point.y():.2f}")

    def _on_scale(self, scale: float) -> None:
        self.label_scale.setText(f"Escala 1:{round(scale):,}".replace(",", "."))

    def _on_crs(self) -> None:
        crs = QgsProject.instance().crs()
        self.label_crs.setText(f"SRC: {crs.authid() or 'sin definir'}")

    def reset_coordinates(self) -> None:
        self.label_coords.setText("Coordenada: -")
