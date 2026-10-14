# MiniGIS

Visor SIG de escritorio mínimo, construido sobre las mismas librerías que usa
QGIS: **GDAL/OGR** para leer los datos y los **bindings de QGIS + Qt6** para
dibujar el mapa. Es el primer paso de un QGIS propio: por ahora sólo carga
shapefiles (y otras fuentes vectoriales OGR) sobre un *canvas*, los lista en un
árbol de capas con casilla de encendido/apagado y ofrece un menú para abrir
archivos.

No hay que instalar nada especial: la aplicación **reutiliza el QGIS instalado
en el equipo** (probado con QGIS 4.2.2).

---

## 1. Cómo se ejecuta

```
mini-gis.bat                                        # ventana vacía
mini-gis.bat samples\poligonos.shp                  # con una capa ya cargada
mini-gis.bat samples\*.shp                          # con todas las de ejemplo
```

`mini-gis.bat` arma el entorno (`o4w_env.bat` + `qt6_env.bat`, `QGIS_PREFIX_PATH`,
`PYTHONPATH`, `QT_PLUGIN_PATH`) y llama al `python.exe` de QGIS. Si tu QGIS está
en otra carpeta, editá la primera línea de entorno del `.bat` o definí la
variable:

```bat
set "OSGEO4W_ROOT=D:\Program Files\QGIS 4.2.2"
```

Opciones de línea de comandos:

| Opción | Para qué sirve |
| --- | --- |
| `ruta\al\archivo.shp` | Carga esa capa al arrancar (se pueden pasar varias). |
| `--check` | Muestra las versiones de QGIS/GDAL/Qt/PyQt y sale, sin abrir ventana. |
| `--captura [ruta.png]` | Abre la ventana, guarda una captura y se cierra. |

## 2. Qué hace hoy

- **Archivo ▸ Abrir capa vectorial…** (`Ctrl+O`): diálogo de archivos filtrado a
  `.shp`, con el resto de formatos OGR disponibles en el segundo filtro.
- **Canvas**: dibuja las capas visibles, con rueda del mouse para zoom,
  arrastrar para mover, y herramientas *Zoom -*, *Zoom +*, *Mover* y
  *Vista completa* (`Ctrl+Shift+F`).
- **Panel Capas**: árbol con una entrada por capa y **casilla para activar o
  desactivar**; se sincroniza solo con el canvas. Incluye zoom a la capa, quitar
  capa, renombrar, mostrar/ocultar todo, expandir/contraer y menú contextual
  (clic derecho). Doble clic sobre una capa hace zoom a ella.
- **Etiquetado y simbología automáticos**: color según el tipo de geometría
  (punto/título/línea) y etiquetas si hay un campo `nombre`/`name`.
- **Arrastrar y soltar**: se pueden soltar archivos vectoriales sobre la ventana.
- **Barra de estado**: coordenada del cursor, escala actual y SRC del proyecto.
- **Ayuda ▸ Acerca de**: versiones de las librerías en uso.

## 3. Estructura del código

```
mini-gis/
├─ mini-gis.bat              lanzador listo para el usuario
├─ dev-env.bat               consola con el entorno de QGIS cargado
├─ main.py                   punto de entrada (argparse casero + arranque)
├─ minigis/
│  ├─ bootstrap.py           inicializa QGIS/GDAL y el perfil de usuario
│  ├─ layers.py              LEER datos: abre fuentes vectoriales con OGR
│  ├─ symbols.py             simbología y etiquetas por defecto
│  ├─ canvas.py              el canvas y la barra de navegación
│  ├─ layer_tree.py          panel de capas (modelo, vista y puente con el canvas)
│  └─ app.py                 ventana principal: menús, acciones y flujo de carga
├─ scripts/
│  ├─ crear_datos_ejemplo.py genera samples/*.shp con OGR
│  ├─ verificar_app.py       verificación de extremo a extremo + capturas
│  └─ verificar_clics.py     verificación con clics reales (QtTest)
├─ tests/                    suite de pytest (corre sin pantalla)
└─ samples/                  poligonos.shp, lineas.shp, puntos.shp
```

La separación es a propósito: **`layers.py` es la única parte que toca GDAL/OGR**.
La interfaz no sabe de dónde vienen los datos, así que agregar rásters, GPKG,
PostGIS o WFS no obliga a tocar la UI.

## 4. Cómo se prueba

```
tests\run-tests.bat                       # toda la suite (pytest, sin pantalla)
dev-env.bat scripts\verificar_app.py      # recorrido completo + capturas en artifacts\
dev-env.bat scripts\verificar_clics.py    # clics reales sobre la casilla del árbol
```

Las capturas quedan en `artifacts/` y sirven para revisar el resultado sin abrir
la ventana. Para probarlo a mano:

```
dev-env.bat scripts\crear_datos_ejemplo.py   # regenera los shapefiles de ejemplo
mini-gis.bat samples\poligonos.shp samples\lineas.shp samples\puntos.shp
```

## 5. Detalles de implementación que vale la pena conocer

- **`QgsApplication` en PyQt6 pide `bytes`**: por eso `create_application()`
  codifica el `argv` a UTF-8 antes de construir la aplicación.
- **La vista del árbol necesita dos llamadas**: `setLayerTreeModel()` deja el
  modelo "de QGIS", pero hasta llamar antes a `setModel()` Qt no construye su
  modelo de ítems y las casillas no responden a los clics ni se puede calcular
  la geometría de las filas. Está documentado en `layer_tree.py`.
- **El encuadre inicial se hace en dos tiempos**: al agregar la capa y otra vez
  en el siguiente ciclo del bucle de eventos (`QTimer.singleShot(0, …)`), porque
  durante la apertura el canvas todavía no tiene su tamaño definitivo.
- **El perfil de usuario es propio** (`%LOCALAPPDATA%\MiniGIS\perfil`) para no
  ensuciar la configuración del QGIS instalado; si esa carpeta no se puede
  escribir, cae a la carpeta temporal.
- **`QgsLayerTreeMapCanvasBridge`** es quien conecta las casillas del árbol con
  el canvas: no hay que refrescar a mano al activar o desactivar una capa.

## 6. Próximos pasos naturales

1. Rásters (GeoTIFF) con `QgsRasterLayer` y control de transparencia.
2. Proyecto: guardar/abrir `.qgs` o `.qgz` con `QgsProject.write()`.
3. Tabla de atributos (`QgsAttributeTableView`) y selección de entidades.
4. Reproyección al vuelo (definir el SRC del proyecto y activar la transformación).
5. Simbología editable desde la interfaz (diálogo de propiedades de capa).
