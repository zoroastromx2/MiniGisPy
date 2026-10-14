"""Tests de la lógica de datos: apertura de fuentes vectoriales."""

from __future__ import annotations

from pathlib import Path

import pytest

from minigis.layers import LayerOpenError, VectorInfo, load_vector_layer


def test_abre_shapefile_de_poligonos(qgis_app, samples):
    layer = load_vector_layer(samples["poligonos"])
    assert layer.isValid()
    assert layer.name() == "poligonos"
    assert layer.featureCount() == 4
    assert layer.crs().authid() == "EPSG:4326"
    assert layer.geometryType() == 2  # polígono


def test_abre_shapefile_de_puntos_y_lineas(qgis_app, samples):
    puntos = load_vector_layer(samples["puntos"])
    lineas = load_vector_layer(samples["lineas"])
    assert (puntos.featureCount(), puntos.geometryType()) == (6, 0)
    assert (lineas.featureCount(), lineas.geometryType()) == (4, 1)


def test_nombre_personalizado(qgis_app, samples):
    layer = load_vector_layer(samples["puntos"], layer_name="POIs del barrio")
    assert layer.name() == "POIs del barrio"


def test_archivo_inexistente(qgis_app, tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_vector_layer(tmp_path / "no_existe.shp")


def test_archivo_no_vectorial(qgis_app, tmp_path: Path):
    basura = tmp_path / "cualquiera.shp"
    basura.write_text("esto no es un shapefile", encoding="utf-8")
    with pytest.raises(LayerOpenError):
        load_vector_layer(basura)


def test_vector_info_resume_la_capa(qgis_app, samples):
    info = VectorInfo.from_layer(load_vector_layer(samples["poligonos"]))
    assert info.feature_count == 4
    # OGR puede devolver Polygon o MultiPolygon según cómo venga el shapefile.
    assert "Polygon" in info.geometry_type
    assert info.crs == "EPSG:4326"
    assert info.extent is not None
    xmin, ymin, xmax, ymax = info.extent
    assert xmin < xmax and ymin < ymax


def test_lee_atributos_utf8(qgis_app, samples):
    """Los shapefiles de ejemplo tienen acentos; GDAL debe devolverlos intactos."""
    layer = load_vector_layer(samples["puntos"])
    nombres = {feature["nombre"] for feature in layer.getFeatures()}
    assert "Estación Central" in nombres
    assert "educación" in {feature["categoria"] for feature in layer.getFeatures()}
