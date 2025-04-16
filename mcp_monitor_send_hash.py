import os
import time
import json
import hashlib
import requests
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Configurações
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'credentials.json'
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
MCP_TRIGGER_URL = os.getenv("MCP_TRIGGER_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

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

def main():
    print("Iniciando monitoramento da pasta com verificação por hash...")
    hashes_processados = set()

    while True:
        try:
            service = autenticar_drive()
            arquivos = buscar_pdfs(service, DRIVE_FOLDER_ID)

            for arquivo in arquivos:
                file_id = arquivo['id']
                file_name = arquivo['name']
                conteudo = baixar_pdf(service, file_id)
                hash_pdf = gerar_hash_pdf(conteudo)

                if hash_pdf in hashes_processados:
                    continue

                payload = {
                    "file_id": file_id,
                    "filename": file_name,
                    "hash_conteudo": hash_pdf
                }

                response = requests.post(MCP_TRIGGER_URL, json=payload)
                print(f"Enviado: {file_name} | Hash: {hash_pdf} | Status: {response.status_code}")
                hashes_processados.add(hash_pdf)

        except Exception as e:
            print(f"Erro: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
