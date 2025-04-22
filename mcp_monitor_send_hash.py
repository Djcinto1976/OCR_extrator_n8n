
from py_zerox import ZeroxDocument


def extrair_dados_zerox(binario_pdf):
    try:
        document = ZeroxDocument(file=binario_pdf, filetype="pdf")
        resultado = document.extract()
        return resultado.to_dict()
    except Exception as e:
        print("[ERRO] ao extrair com Zerox:", e)
        return None


import os
import time
import json
import hashlib
import requests
from io import BytesIO
import xml.etree.ElementTree as ET
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

def buscar_arquivos(service, folder_id):
    # Busca PDFs e XMLs
    query = f"'{folder_id}' in parents and (mimeType = 'application/pdf' or mimeType = 'application/xml' or mimeType = 'text/xml') and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    return results.get('files', [])

def baixar_arquivo(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()

def gerar_hash_conteudo(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()

# def extrair_texto_pdf(binario_pdf: bytes) -> str:
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

def extrair_dados_nfe(binario_xml: bytes) -> dict:
    try:
        # Decodifica o XML para texto
        xml_texto = binario_xml.decode('utf-8')
        
        # Registra os namespaces comuns em NF-e
        namespaces = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe',
        }
        
        # Parse do XML
        root = ET.fromstring(xml_texto)
        
        # Inicializa o dicionário de dados
        dados_nfe = {
            "fornecedor": {
                "nome": "",
                "cnpj": ""
            },
            "nfe": {
                "numero": "",
                "data_emissao": "",
                "valor_total": ""
            },
            "duplicatas": []
        }
        
        # Tenta extrair os dados específicos da NF-e
        try:
            # Busca o namespace correto
            for prefix, uri in root.nsmap.items() if hasattr(root, 'nsmap') else []:
                if 'nfe' in uri.lower():
                    namespaces['nfe'] = uri
                    break
            
            # Extrai dados do emitente (fornecedor)
            emit = root.find('.//emit') or root.find('.//*[local-name()="emit"]')
            if emit is not None:
                nome = emit.find('./xNome') or emit.find('.//*[local-name()="xNome"]')
                cnpj = emit.find('./CNPJ') or emit.find('.//*[local-name()="CNPJ"]')
                
                if nome is not None and nome.text:
                    dados_nfe["fornecedor"]["nome"] = nome.text.strip()
                if cnpj is not None and cnpj.text:
                    dados_nfe["fornecedor"]["cnpj"] = cnpj.text.strip()
            
            # Extrai dados da NF-e
            ide = root.find('.//ide') or root.find('.//*[local-name()="ide"]')
            if ide is not None:
                numero = ide.find('./nNF') or ide.find('.//*[local-name()="nNF"]')
                data = ide.find('./dhEmi') or ide.find('.//*[local-name()="dhEmi"]')
                
                if numero is not None and numero.text:
                    dados_nfe["nfe"]["numero"] = numero.text.strip()
                if data is not None and data.text:
                    dados_nfe["nfe"]["data_emissao"] = data.text.strip()
            
            # Extrai valor total
            total = root.find('.//total/ICMSTot/vNF') or root.find('.//*[local-name()="vNF"]')
            if total is not None and total.text:
                dados_nfe["nfe"]["valor_total"] = total.text.strip()
            
            # Extrai duplicatas/parcelas
            cobr = root.find('.//cobr') or root.find('.//*[local-name()="cobr"]')
            if cobr is not None:
                dups = cobr.findall('./dup') or cobr.findall('.//*[local-name()="dup"]')
                for dup in dups:
                    num_parcela = dup.find('./nDup') or dup.find('.//*[local-name()="nDup"]')
                    valor_parcela = dup.find('./vDup') or dup.find('.//*[local-name()="vDup"]')
                    data_vencimento = dup.find('./dVenc') or dup.find('.//*[local-name()="dVenc"]')
                    
                    parcela = {}
                    if num_parcela is not None and num_parcela.text:
                        parcela["numero"] = num_parcela.text.strip()
                    if valor_parcela is not None and valor_parcela.text:
                        parcela["valor"] = valor_parcela.text.strip()
                    if data_vencimento is not None and data_vencimento.text:
                        parcela["vencimento"] = data_vencimento.text.strip()
                    
                    if parcela:
                        dados_nfe["duplicatas"].append(parcela)
        
        except Exception as e:
            print(f"Erro ao extrair dados específicos da NF-e: {e}")
            # Tenta uma abordagem alternativa para extrair os dados
            try:
                # Busca por texto em todo o XML
                texto_completo = xml_texto.lower()
                
                # Tenta encontrar CNPJ do emitente
                if not dados_nfe["fornecedor"]["cnpj"]:
                    import re
                    cnpj_match = re.search(r'<cnpj>([0-9]{14})</cnpj>', texto_completo)
                    if cnpj_match:
                        dados_nfe["fornecedor"]["cnpj"] = cnpj_match.group(1)
                
                # Outras tentativas de extração podem ser adicionadas aqui
                
            except Exception as e2:
                print(f"Erro na extração alternativa: {e2}")
        
        return {
            "texto": xml_texto,  # Mantém o texto completo
            "dados_nfe": dados_nfe  # Dados específicos da NF-e
        }
    
    except Exception as e:
        print(f"Erro ao processar XML: {e}")
        return {
            "texto": binario_xml.decode('utf-8', errors='replace'),
            "dados_nfe": {},
            "erro": str(e)
        }

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
            arquivos = buscar_arquivos(service, DRIVE_FOLDER_ID)
            print(f"[DEBUG] 🔍 Encontrados {len(arquivos)} arquivos (PDF/XML) na pasta do Drive.")

            for arquivo in arquivos:
                file_id = arquivo['id']
                file_name = arquivo['name']
                mime_type = arquivo['mimeType']
                conteudo = baixar_arquivo(service, file_id)
                hash_conteudo = gerar_hash_conteudo(conteudo)

                if hash_conteudo in hashes_processados:
                    continue

                # Prepara o payload básico
                payload = {
                    "file_id": file_id,
                    "filename": file_name,
                    "mime_type": mime_type,
                    "hash_conteudo": hash_conteudo,
                }

                # Processa de acordo com o tipo de arquivo
                if mime_type == 'application/pdf':
                    texto_extraido = extrair_texto_pdf(conteudo)
                    payload["texto"] = texto_extraido
                    print(f"[DEBUG] Trecho do texto extraído do PDF:\n{texto_extraido[:500]}")

                elif mime_type in ['application/xml', 'text/xml']:
                    resultado_xml = extrair_dados_nfe(conteudo)
                    payload["texto"] = resultado_xml["texto"]
                    payload["dados_nfe"] = resultado_xml["dados_nfe"]
                    print(f"[DEBUG] XML processado. Dados da NF-e extraídos.")
                    print(f"[DEBUG] Fornecedor: {payload['dados_nfe']['fornecedor']['nome']}")
                    print(f"[DEBUG] NF-e: {payload['dados_nfe']['nfe']['numero']}")
                    print(f"[DEBUG] Valor Total: {payload['dados_nfe']['nfe']['valor_total']}")
                    print(f"[DEBUG] Duplicatas: {len(payload['dados_nfe']['duplicatas'])}")

                # Envia os dados para o webhook
                if MCP_TRIGGER_URL:
                    response = requests.post(MCP_TRIGGER_URL, json=payload)
                    print(f"✅ Enviado: {file_name} | Hash: {hash_conteudo} | Status: {response.status_code}")
                else:
                    print(f"📦 Dados extraídos (sem envio):\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

                hashes_processados.add(hash_conteudo)
                mover_arquivo_para_processados(service, file_id, DRIVE_FOLDER_ID, DRIVE_FOLDER_PROCESSED_ID)

        except Exception as e:
            print(f"❌ Erro: {e}")

        print(f"⏱️ Aguardando {CHECK_INTERVAL} segundos para a próxima verificação...\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()