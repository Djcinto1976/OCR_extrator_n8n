FROM python:3.12-slim

WORKDIR /usr/local/mcp

COPY . .

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils

# ✅ Instala o git antes do pip para permitir instalação via GitHub
RUN apt-get update && apt-get install -y git

# ✅ Instala todas as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "mcp_monitor_send_hash.py"]

EXPOSE 5679


