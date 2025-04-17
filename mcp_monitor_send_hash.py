import os
import time
import json
import hashlib
import requests
from io import BytesIO
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Configurações
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")  # Pasta A-Processar
DRIVE_FOLDER_PROCESSED_ID = os.getenv("DRIVE_FOLDER_PROCESSED_ID")  # Pasta Processados
MCP_TRIGGER_URL = os.getenv("MCP_TRIGGER_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "50"))

def autenticar_drive():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def buscar_pdfs(service, folder_id):
    query = f"'{folder_id}' in parents and mimeType = 'application/pdf' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

def baixar_pdf(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()

def gerar_hash_pdf(conteudo_pdf: bytes) -> str:
    return hashlib.sha256(conteudo_pdf).hexdigest()

def extrair_texto_pdf(binario_pdf: bytes) -> str:
    texto = ""
    with fitz.open(stream=binario_pdf, filetype="pdf") as doc:
        for page in doc:
            texto += page.get_text()

    if texto.strip():
        return texto.strip()

    print("[OCR] Nenhum texto extraído via PyMuPDF. Aplicando OCR com pytesseract...")
    imagens = convert_from_bytes(binario_pdf)
    texto_ocr = ""
    for i, imagem in enumerate(imagens):
        texto_ocr += f"\n--- Página {i+1} ---\n"
        texto_ocr += pytesseract.image_to_string(imagem, lang='por')
    return texto_ocr.strip()

def mover_arquivo_para_processados(service, file_id, pasta_origem_id, pasta_destino_id):
    service.files().update(
        fileId=file_id,
        addParents=pasta_destino_id,
        removeParents=pasta_origem_id,
        fields='id, parents'
    ).execute()
    print(f"📁 Arquivo {file_id} movido para pasta processados.")

def main():
    print("Iniciando monitoramento da pasta com verificação por hash...")
    print(f"[DEBUG] ID da pasta: {DRIVE_FOLDER_ID}")
    hashes_processados = set()

    while True:
        try:
            service = autenticar_drive()
            arquivos = buscar_pdfs(service, DRIVE_FOLDER_ID)
            print(f"[DEBUG] 🔍 Encontrados {len(arquivos)} arquivos PDF na pasta do Drive.")

            for arquivo in arquivos:
                file_id = arquivo['id']
                file_name = arquivo['name']
                conteudo = baixar_pdf(service, file_id)
                hash_pdf = gerar_hash_pdf(conteudo)

                if hash_pdf in hashes_processados:
                    continue

                texto_extraido = extrair_texto_pdf(conteudo)
                print(f"[DEBUG] Trecho do texto extraído:\n{texto_extraido[:500]}")

                payload = {
                    "file_id": file_id,
                    "filename": file_name,
                    "hash_conteudo": hash_pdf,
                    "texto": texto_extraido,
                }

                if MCP_TRIGGER_URL:
                    response = requests.post(MCP_TRIGGER_URL, json=payload)
                    print(f"✅ Enviado: {file_name} | Hash: {hash_pdf} | Status: {response.status_code}")
                else:
                    print(f"📦 Dados extraídos (sem envio):\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

                hashes_processados.add(hash_pdf)
                mover_arquivo_para_processados(service, file_id, DRIVE_FOLDER_ID, DRIVE_FOLDER_PROCESSED_ID)

        except Exception as e:
            print(f"❌ Erro: {e}")

        print(f"⏱️ Aguardando {CHECK_INTERVAL} segundos para a próxima verificação...\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
