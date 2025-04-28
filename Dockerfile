# Use uma imagem base Python
FROM python:3.12-slim

# Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala dependências do sistema (OCR + PDF + git + segurança)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo requirements.txt e instala as dependências Python
# Copiar apenas o requirements.txt antes de instalar as dependências
# aproveita o cache do Docker se apenas o requirements.txt mudar.
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia o script Python principal e outros arquivos de código necessários
# Copie apenas os arquivos de código fonte e outros arquivos essenciais
COPY mcp_monitor_send_hash.py /app/
# Se houver outros arquivos .py ou módulos que seu script importa, copie-os também.
# Exemplo: COPY your_module.py /app/

# O credentials.json será montado via volume, não precisa ser copiado aqui.
# O .env será carregado via env_file no docker-compose, não precisa ser copiado aqui.

# Comando principal
CMD ["python", "mcp_monitor_send_hash.py"]



