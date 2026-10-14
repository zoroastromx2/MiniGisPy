@echo off
rem ===========================================================================
rem  MiniGIS - entorno de desarrollo
rem  Abre una consola con el entorno de QGIS cargado y el interprete de Python
rem  de QGIS listo, para correr scripts y tests:
rem
rem      dev-env.bat tests\run-tests.bat
rem      dev-env.bat scripts\crear_datos_ejemplo.py
rem      dev-env.bat            (solo abre la consola)
rem ===========================================================================
setlocal EnableExtensions EnableDelayedExpansion

if not defined OSGEO4W_ROOT set "OSGEO4W_ROOT=C:\Program Files\QGIS 4.2.2"
if not exist "!OSGEO4W_ROOT!\bin\o4w_env.bat" (
    echo [MiniGIS] No se encontro QGIS en "!OSGEO4W_ROOT!".
    exit /b 1
)

call "!OSGEO4W_ROOT!\bin\o4w_env.bat"
call "!OSGEO4W_ROOT!\bin\qt6_env.bat"
path !OSGEO4W_ROOT!\apps\qgis\bin;!PATH!
set "QGIS_PREFIX_PATH=!OSGEO4W_ROOT!\apps\qgis"
set "PYTHONPATH=!OSGEO4W_ROOT!\apps\qgis\python;%~dp0;!PYTHONPATH!"
set "QT_PLUGIN_PATH=!OSGEO4W_ROOT!\apps\qgis\qtplugins;!OSGEO4W_ROOT!\apps\Qt6\plugins"
set "GDAL_FILENAME_IS_UTF8=YES"
set "VSI_CACHE=TRUE"
set "VSI_CACHE_SIZE=1000000"
set "MINIGIS_ROOT=%~dp0"
cd /d "%~dp0"

echo [MiniGIS] QGIS: !OSGEO4W_ROOT!
echo [MiniGIS] Python: !OSGEO4W_ROOT!\apps\Python312\python.exe

if "%~1"=="" (
    cmd /k
) else (
    "!OSGEO4W_ROOT!\apps\Python312\python.exe" %*
    set "MINIGIS_EXIT=!ERRORLEVEL!"
    endlocal & exit /b %MINIGIS_EXIT%
)

endlocal
