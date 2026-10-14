"""Acceso a datos: abrir fuentes vectoriales con la API de QGIS/GDAL (OGR).

Todo el acceso a archivos vive acá. La interfaz gráfica nunca llama a GDAL
directamente, así que más adelante se puede agregar soporte para rásters, bases
PostGIS o servicios WFS sin tocar la UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qgis.core import QgsMapLayer, QgsVectorLayer, QgsVectorLayerExporter, QgsWkbTypes

#: Extensiones vectoriales que ofrece el diálogo y acepta el arrastrar-y-soltar.
VECTOR_EXTENSIONS: tuple[str, ...] = (
    ".shp",
    ".geojson",
    ".json",
    ".gpkg",
    ".kml",
    ".gml",
    ".tab",
    ".mif",
)


class LayerOpenError(RuntimeError):
    """La fuente existe pero QGIS/GDAL no pudo interpretarla."""


@dataclass(frozen=True)
class VectorInfo:
    """Resumen legible de una fuente vectorial, útil para tests y reportes."""

    path: str
    name: str
    geometry_type: str
    feature_count: int
    crs: str
    extent: tuple[float, float, float, float] | None

    @classmethod
    def from_layer(cls, layer: QgsVectorLayer) -> "VectorInfo":
        extent = layer.extent()
        return cls(
            path=layer.source(),
            name=layer.name(),
            geometry_type=QgsWkbTypes.displayString(layer.wkbType()),
            feature_count=layer.featureCount(),
            crs=layer.crs().authid() or layer.crs().description(),
            extent=(extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
            if not extent.isEmpty()
            else None,
        )


def is_vector_file(path: str | Path) -> bool:
    """``True`` si la ruta parece una fuente vectorial soportada."""
    return Path(path).suffix.lower() in VECTOR_EXTENSIONS


def load_vector_layer(path: str | Path, layer_name: str | None = None) -> QgsVectorLayer:
    """Abre una fuente vectorial (por ejemplo un shapefile) como capa de QGIS.

    :param path: ruta al ``.shp`` (o cualquier fuente OGR: GeoJSON, GPKG, ...).
    :param layer_name: nombre a mostrar; por defecto, el nombre del archivo.
    :raises FileNotFoundError: si la ruta no existe.
    :raises LayerOpenError: si la fuente existe pero no se puede leer.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    layer = QgsVectorLayer(str(path), layer_name or path.stem, "ogr")
    if not layer.isValid():
        raise LayerOpenError(
            f"'{path.name}' no es una fuente vectorial válida "
            "(¿está dañado o le faltan los archivos .dbf/.shx del shapefile?)."
        )
    return layer


def export_layer(layer: QgsMapLayer, destination: str | Path) -> None:
    """Exporta una capa vectorial (base para un futuro 'Guardar como')."""
    if not isinstance(layer, QgsVectorLayer):
        raise LayerOpenError("Sólo se pueden exportar capas vectoriales.")
    error, message = QgsVectorLayerExporter.exportLayer(
        layer, str(destination), "GPKG", layer.crs(), False
    )
    if error != QgsVectorLayerExporter.ErrCode.NoError:
        raise LayerOpenError(f"Error al exportar: {message}")
