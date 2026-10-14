"""MiniGIS - un SIG de escritorio mínimo construido sobre GDAL / OGR y QGIS.

El paquete está separado en tres capas para que crezca de a poco:

* :mod:`minigis.bootstrap`  -> inicializa el entorno QGIS (complementos, rutas, GDAL).
* :mod:`minigis.layers`     -> lógica de datos: abrir fuentes vectoriales (shapefiles).
* :mod:`minigis.app`        -> interfaz gráfica: canvas, árbol de capas y menús.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
