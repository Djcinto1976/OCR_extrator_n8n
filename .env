@echo off
setlocal

:: Configurações do projeto
set REPO_DIR=C:\Users\Dell\Desktop\Agente_Script\Fluxo_n8n_OCR\mcp_gdrive_hash_monitor
set COMMIT_MSG=Atualização automática do projeto
set BRANCH=main

:: Ir para o diretório do repositório
cd /d "%REPO_DIR%"

:: Verificar se é um repositório Git
if not exist ".git" (
    echo Este diretório não é um repositório Git. Abortando.
    pause
    exit /b 1
)

:: Adiciona todos os arquivos alterados
git add .

:: Faz commit com a mensagem padrão
git commit -m "%COMMIT_MSG%"

:: Faz push para o GitHub
git push origin %BRANCH%

:: Mensagem final
echo Projeto enviado com sucesso para o GitHub!
pause
