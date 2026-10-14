@echo off
rem ===========================================================================
rem  MiniGIS - lanzador
rem  Prepara el entorno de QGIS (GDAL/OGR + Qt6 + bindings de Python) y arranca
rem  la aplicacion. No requiere instalar nada: reutiliza el QGIS que ya esta en
rem  el equipo. Si QGIS esta en otra carpeta, cambia OSGEO4W_ROOT aqui abajo.
rem ===========================================================================
setlocal EnableExtensions EnableDelayedExpansion

rem --- 1) Ubicar la instalacion de QGIS --------------------------------------
if not defined OSGEO4W_ROOT set "OSGEO4W_ROOT=e:\Program Files\QGIS 4.2.3\"

if not exist "!OSGEO4W_ROOT!\bin\o4w_env.bat" (
    for /d %%D in ("C:\Program Files\QGIS*") do (
        if exist "%%D\bin\o4w_env.bat" set "OSGEO4W_ROOT=%%D"
    )
)
if not exist "!OSGEO4W_ROOT!\bin\o4w_env.bat" (
    echo [MiniGIS] No se encontro una instalacion de QGIS.
    echo [MiniGIS] Defini la variable OSGEO4W_ROOT, por ejemplo:
    echo [MiniGIS]   set "OSGEO4W_ROOT=C:\Program Files\QGIS 4.2.2"
    exit /b 1
)

rem --- 2) Entorno base de OSGeo4W y Qt6 --------------------------------------
call "!OSGEO4W_ROOT!\bin\o4w_env.bat"
call "!OSGEO4W_ROOT!\bin\qt6_env.bat"

path !OSGEO4W_ROOT!\apps\qgis\bin;!PATH!
set "QGIS_PREFIX_PATH=!OSGEO4W_ROOT!\apps\qgis"
set "PYTHONPATH=!OSGEO4W_ROOT!\apps\qgis\python;!PYTHONPATH!"
set "QT_PLUGIN_PATH=!OSGEO4W_ROOT!\apps\qgis\qtplugins;!OSGEO4W_ROOT!\apps\Qt6\plugins"
set "GDAL_FILENAME_IS_UTF8=YES"
set "VSI_CACHE=TRUE"
set "VSI_CACHE_SIZE=1000000"

rem --- 3) Elegir interprete y ejecutar ---------------------------------------
set "MINIGIS_DIR=%~dp0"
set "MINIGIS_PYTHON=!OSGEO4W_ROOT!\apps\Python312\python.exe"
if exist "!OSGEO4W_ROOT!\bin\python3.exe" set "MINIGIS_PYTHON=!OSGEO4W_ROOT!\bin\python3.exe"

"!MINIGIS_PYTHON!" "!MINIGIS_DIR!main.py" %*
set "MINIGIS_EXIT=!ERRORLEVEL!"

endlocal & exit /b %MINIGIS_EXIT%
