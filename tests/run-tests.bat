@echo off
rem ===========================================================================
rem  MiniGIS - tests automatizados (sin pantalla)
rem      tests\run-tests.bat                 corre toda la suite
rem      tests\run-tests.bat -k casilla      filtra por nombre
rem      tests\run-tests.bat -v              verboso
rem ===========================================================================
setlocal EnableExtensions
cd /d "%~dp0.."

rem La plataforma "offscreen" permite correr la interfaz sin monitor.
set "QT_QPA_PLATFORM=offscreen"

call dev-env.bat -m pytest tests %*
endlocal & exit /b %ERRORLEVEL%
