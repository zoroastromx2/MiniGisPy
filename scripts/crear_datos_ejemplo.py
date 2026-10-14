"""Genera shapefiles de ejemplo en ``samples/`` usando la API de OGR (GDAL).

    python scripts\\crear_datos_ejemplo.py

Crea tres capas en EPSG:4326 (WGS 84) pensadas para probar el visor:
``poligonos.shp`` (manzanas), ``lineas.shp`` (calles/rutas) y ``puntos.shp`` (POIs).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from osgeo import ogr, osr

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
CRS_EPSG = 4326


def _spatial_reference() -> osr.SpatialReference:
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(CRS_EPSG)
    # Los shapefiles usan el orden clásico lon/lat.
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return srs


def _create_layer(dataset: ogr.DataSource, name: str, geometry_type: int, fields: dict[str, ogr.OFTType]):
    if dataset.GetLayerByName(name) is not None:
        dataset.DeleteLayer(name)
    layer = dataset.CreateLayer(name, _spatial_reference(), geometry_type, options=["ENCODING=UTF-8"])
    for field_name, field_type in fields.items():
        layer.CreateField(ogr.FieldDefn(field_name, field_type))
    return layer


def _add_feature(layer, geometry: ogr.Geometry, **attributes) -> None:
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(geometry)
    for key, value in attributes.items():
        feature.SetField(key, value)
    layer.CreateFeature(feature)
    feature = None


def _polygon(ring: list[tuple[float, float]]) -> ogr.Geometry:
    geometry = ogr.Geometry(ogr.wkbPolygon)
    linear_ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in ring:
        linear_ring.AddPoint_2D(x, y)
    linear_ring.AddPoint_2D(*ring[0])  # cierra el anillo
    geometry.AddGeometry(linear_ring)
    return geometry


def _line(points: list[tuple[float, float]]) -> ogr.Geometry:
    geometry = ogr.Geometry(ogr.wkbLineString)
    for x, y in points:
        geometry.AddPoint_2D(x, y)
    return geometry


def _point(x: float, y: float) -> ogr.Geometry:
    geometry = ogr.Geometry(ogr.wkbPoint)
    geometry.AddPoint_2D(x, y)
    return geometry


def crear_poligonos(dataset: ogr.DataSource) -> int:
    """Manzanas de un barrio ficticio, con uso de suelo y superficie."""
    layer = _create_layer(
        dataset,
        "poligonos",
        ogr.wkbPolygon,
        {"nombre": ogr.OFTString, "uso": ogr.OFTString, "sup_ha": ogr.OFTReal},
    )
    manzanas = [
        ("Manzana Norte", "residencial", [(-58.42, -34.60), (-58.41, -34.60), (-58.41, -34.605), (-58.42, -34.605)]),
        ("Manzana Sur", "comercial", [(-58.42, -34.61), (-58.41, -34.61), (-58.41, -34.615), (-58.42, -34.615)]),
        ("Parque Central", "espacio verde", [(-58.405, -34.605), (-58.395, -34.605), (-58.395, -34.613), (-58.405, -34.613)]),
        ("Predio Industrial", "industrial", [(-58.43, -34.615), (-58.415, -34.615), (-58.415, -34.625), (-58.43, -34.625)]),
    ]
    for nombre, uso, anillo in manzanas:
        geometry = _polygon(anillo)
        _add_feature(layer, geometry, nombre=nombre, uso=uso, sup_ha=round(geometry.GetArea() * 12_000, 2))
    return len(manzanas)


def crear_lineas(dataset: ogr.DataSource) -> int:
    """Ejes de circulación, con jerarquía y largo aproximado."""
    layer = _create_layer(
        dataset,
        "lineas",
        ogr.wkbLineString,
        {"nombre": ogr.OFTString, "jerarquia": ogr.OFTString, "km": ogr.OFTReal},
    )
    ejes = [
        ("Av. del Puerto", "primaria", [(-58.435, -34.600), (-58.425, -34.605), (-58.412, -34.608), (-58.392, -34.612)]),
        ("Calle Interna 1", "secundaria", [(-58.425, -34.598), (-58.425, -34.612), (-58.428, -34.626)]),
        ("Calle Interna 2", "secundaria", [(-58.412, -34.600), (-58.410, -34.614), (-58.418, -34.622)]),
        ("Camino Rural", "terciaria", [(-58.448, -34.630), (-58.430, -34.628), (-58.410, -34.630), (-58.392, -34.628)]),
    ]
    for nombre, jerarquia, puntos in ejes:
        geometry = _line(puntos)
        _add_feature(layer, geometry, nombre=nombre, jerarquia=jerarquia, km=round(geometry.Length() * 92, 2))
    return len(ejes)


def crear_puntos(dataset: ogr.DataSource) -> int:
    """Puntos de interés, con categoría y nombre."""
    layer = _create_layer(
        dataset,
        "puntos",
        ogr.wkbPoint,
        {"nombre": ogr.OFTString, "categoria": ogr.OFTString},
    )
    pois = [
        ("Estación Central", "transporte", -58.4210, -34.6035),
        ("Museo del Puerto", "cultura", -58.4085, -34.6072),
        ("Hospital Zonal", "salud", -58.4172, -34.6178),
        ("Escuela N. 12", "educación", -58.4265, -34.6122),
        ("Mercado de Abasto", "comercio", -58.3990, -34.6105),
        ("Plaza San Martín", "espacio verde", -58.4308, -34.6195),
    ]
    for nombre, categoria, x, y in pois:
        _add_feature(layer, _point(x, y), nombre=nombre, categoria=categoria)
    return len(pois)


def main() -> int:
    if SAMPLES_DIR.exists():
        shutil.rmtree(SAMPLES_DIR)
    SAMPLES_DIR.mkdir(parents=True)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    totales: dict[str, int] = {}
    for name, builder in (
        ("poligonos", crear_poligonos),
        ("lineas", crear_lineas),
        ("puntos", crear_puntos),
    ):
        destination = SAMPLES_DIR / f"{name}.shp"
        dataset = driver.CreateDataSource(str(destination))
        if dataset is None:
            print(f"No se pudo crear {destination}", file=sys.stderr)
            return 1
        totales[name] = builder(dataset)
        dataset = None
        print(f"Creado {destination}")

    print("Entidades por capa:", totales)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
