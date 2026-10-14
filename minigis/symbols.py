"""Simbología por defecto para las capas cargadas.

Sin esto, todas las capas se dibujan con el mismo estilo aleatorio que QGIS
asigna según el tipo de geometría, y en un visor de prueba conviene distinguir
los polígonos de las líneas y los puntos de un vistazo.
"""

from __future__ import annotations

from qgis.core import (
    Qgis,
    QgsCategorizedSymbolRenderer,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsRendererCategory,
    QgsSingleSymbolRenderer,
    QgsSymbol,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtGui import QColor

#: Colores por familia de geometría (relleno, borde).
PALETTES: dict[str, list[tuple[str, str]]] = {
    "polygon": [
        ("#8fbc8f", "#2f4f2f"),
        ("#e8c37a", "#8a6512"),
        ("#a8bfe0", "#2d4a78"),
        ("#dba6b8", "#7d3f52"),
    ],
    "line": [
        ("#1f4e79", "#1f4e79"),
        ("#a33b20", "#a33b20"),
        ("#3b6b3b", "#3b6b3b"),
        ("#6a3d9a", "#6a3d9a"),
    ],
    "point": [
        ("#c0392b", "#7b241c"),
        ("#2471a3", "#154360"),
        ("#1e8449", "#145a32"),
        ("#b7950b", "#7d6608"),
    ],
}

#: Campos que, si existen, se usan para etiquetar automáticamente.
LABEL_FIELD_CANDIDATES = ("nombre", "name", "title", "titulo", "tit", "id", "fid")


def geometry_family(layer: QgsVectorLayer) -> str:
    """Devuelve ``'point'``, ``'line'``, ``'polygon'`` o ``'unknown'``."""
    flat = QgsWkbTypes.geometryType(layer.wkbType())
    if flat == QgsWkbTypes.GeometryType.PolygonGeometry:
        return "polygon"
    if flat == QgsWkbTypes.GeometryType.LineGeometry:
        return "line"
    if flat == QgsWkbTypes.GeometryType.PointGeometry:
        return "point"
    return "unknown"


def _categorized_renderer(layer: QgsVectorLayer, family: str, field: str) -> QgsCategorizedSymbolRenderer:
    """Un color distinto por valor del campo elegido (máx. 8 categorías)."""
    values = sorted(
        {
            str(feature[field])
            for feature in layer.getFeatures()
            if feature[field] not in (None, "")
        }
    )[:8]
    palette = PALETTES[family]

    categories = []
    for index, value in enumerate(values):
        fill, border = palette[index % len(palette)]
        categories.append(QgsRendererCategory(value, _symbol(family, fill, border), value))
    categories.append(
        QgsRendererCategory(None, _symbol(family, "#b0b0b0", "#606060"), "otros")
    )
    return QgsCategorizedSymbolRenderer(field, categories)


def _symbol(family: str, color: str, border: str) -> QgsSymbol:
    if family == "polygon":
        symbol = QgsFillSymbol.createSimple(
            {"color": color, "outline_color": border, "outline_width": "0.4"}
        )
    elif family == "line":
        symbol = QgsLineSymbol.createSimple({"color": color, "width": "0.7"})
    else:
        symbol = QgsMarkerSymbol.createSimple(
            {"color": color, "outline_color": border, "size": "2.6"}
        )
    return symbol


def apply_default_style(
    layer: QgsVectorLayer, field: str | None = None, color_index: int = 0
) -> str:
    """Aplica un estilo legible a la capa y devuelve una descripción del mismo.

    :param field: campo a usar para la simbología por categorías (opcional).
    :param color_index: posición en la paleta, para que capas sucesivas del mismo
        tipo de geometría no salgan todas del mismo color.
    """
    family = geometry_family(layer)
    if family == "unknown":
        return "tipo de geometría desconocido: se deja el estilo por defecto"

    if field and layer.fields().indexOf(field) >= 0 and layer.featureCount() > 1:
        layer.setRenderer(_categorized_renderer(layer, family, field))
        description = f"simbología por categorías según '{field}'"
    else:
        fill, border = PALETTES[family][color_index % len(PALETTES[family])]
        layer.setRenderer(QgsSingleSymbolRenderer(_symbol(family, fill, border)))
        description = f"símbolo simple ({family})"

    # Etiqueta con el primer campo de texto "con nombre" que encontremos.
    label_field = _label_field(layer)
    if label_field:
        _enable_labels(layer, label_field)

    layer.triggerRepaint()
    return description


def _label_field(layer: QgsVectorLayer) -> str | None:
    for candidate in LABEL_FIELD_CANDIDATES:
        index = layer.fields().indexOf(candidate)
        if index >= 0:
            return candidate
    return None


def _enable_labels(layer: QgsVectorLayer, field: str) -> None:
    """Activa etiquetas básicas usando la API de QGIS 3.32+."""
    try:
        from qgis.core import QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling
        from qgis.PyQt.QtGui import QFont

        settings = QgsPalLayerSettings()
        settings.fieldName = field
        settings.enabled = True

        text_format = QgsTextFormat()
        text_format.setFont(QFont("Segoe UI", 8))
        text_format.setSize(8)
        text_format.setColor(QColor("#202020"))
        settings.setFormat(text_format)

        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
    except Exception as error:  # pragma: no cover - las etiquetas son opcionales
        from qgis.core import QgsMessageLog

        QgsMessageLog.logMessage(
            f"No se pudieron activar las etiquetas: {error}", "MiniGIS", Qgis.MessageLevel.Warning
        )
