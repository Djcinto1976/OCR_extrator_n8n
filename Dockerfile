FROM python:3.12-slim

WORKDIR /usr/local/mcp

# Copia todo o conteúdo do projeto (inclusive o credentials.json)
COPY . .

# Instala dependências do sistema (OCR + PDF + git + segurança)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando principal
CMD ["python", "mcp_monitor_send_hash.py"]



