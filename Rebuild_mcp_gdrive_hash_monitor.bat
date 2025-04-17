@echo off
set IMAGE_NAME=mcp_gdrive_hash_monitor
set CONTAINER_NAME=monitor-container
set CONTAINER_PORT=5679
set DRIVE_FOLDER_ID=1Yc-N8rGhGq19Oir-Ovrw35rq_BOisysY

echo.
echo 🚧 Parando container antigo (se existir)...
docker stop %CONTAINER_NAME%
docker rm %CONTAINER_NAME%

echo.
echo 🔄 Rebuild da imagem %IMAGE_NAME%...
docker build -t %IMAGE_NAME% .

echo.
echo 🚀 Rodando novo container...
docker run -d ^
  -p %CONTAINER_PORT%:%CONTAINER_PORT% ^
  --name %CONTAINER_NAME% ^
  -e DRIVE_FOLDER_ID=%DRIVE_FOLDER_ID% ^
  %IMAGE_NAME%

echo.
echo ✅ Container atualizado e em execução!
pause
