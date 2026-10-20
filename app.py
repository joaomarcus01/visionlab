"""
Servidor da página de inspeção "Dano Estrutural".

Como rodar no computador:
    pip install -r requirements.txt
    python app.py
Depois abra http://localhost:5000 no navegador.

A chave do Roboflow fica no arquivo .env (que NÃO vai para o GitHub).
Na hospedagem (Render), ela é cadastrada como variável de ambiente ROBOFLOW_API_KEY.
"""

import os
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory


def carregar_env():
    """Lê o arquivo .env (se existir) e coloca os valores nas variáveis de ambiente."""
    arquivo = Path(__file__).with_name(".env")
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            nome, valor = linha.split("=", 1)
            os.environ.setdefault(nome.strip(), valor.strip().strip('"').strip("'"))


carregar_env()

# =====================================================================
#
#   ███  COLOQUE SEUS DADOS AQUI  ███
#
#   A CHAVE (API_KEY) fica no arquivo .env → ROBOFLOW_API_KEY=sua_chave
#   O modelo e a versão ficam aqui embaixo.
#
#   Exemplo de URL do modelo:  https://detect.roboflow.com/dano-estrutural/3
#                                                         └─ ENDPOINT ─┘ └ VERSION
# =====================================================================

API_KEY = os.environ.get("ROBOFLOW_API_KEY", "")   # a chave fica no .env, não aqui
MODEL_ENDPOINT = "rachadura-lmgsu"      # ID do modelo (slug do projeto)
VERSION = "2"                           # número da versão treinada

# ---------------- Ajustes opcionais ----------------
CONFIANCA_MINIMA = 40   # 0–100: valor inicial (ajustável na página)
SOBREPOSICAO = 30       # 0–100: valor inicial (ajustável na página)
API_BASE_URL = "https://detect.roboflow.com"   # endereço da API (não é o site app.roboflow.com)
PORTA = int(os.environ.get("PORT", 5000))

# =====================================================================
#   FIM DA CONFIGURAÇÃO — não é preciso alterar nada abaixo.
# =====================================================================

app = Flask(__name__, static_folder=None)


def configuracao_preenchida():
    return bool(API_KEY) and bool(MODEL_ENDPOINT) and bool(VERSION)


@app.get("/")
def pagina():
    return send_from_directory(app.root_path, "index.html")


@app.get("/logo.png")
def logo():
    return send_from_directory(app.root_path, "logo.png")


@app.get("/config")
def config():
    return jsonify(configurado=configuracao_preenchida(), confianca=CONFIANCA_MINIMA, sobreposicao=SOBREPOSICAO)


@app.post("/analisar")
def analisar():
    if not configuracao_preenchida():
        return jsonify(erro="Chave do Roboflow não configurada. Coloque ROBOFLOW_API_KEY no arquivo .env (ou nas variáveis de ambiente da hospedagem) e reinicie o servidor."), 400

    imagem_base64 = request.get_data(as_text=True)
    if not imagem_base64:
        return jsonify(erro="Nenhuma imagem foi recebida."), 400

    def percentual(nome, padrao):
        try:
            return min(100, max(0, int(request.args.get(nome, padrao))))
        except ValueError:
            return padrao

    confianca = percentual("confianca", CONFIANCA_MINIMA)
    sobreposicao = percentual("sobreposicao", SOBREPOSICAO)

    try:
        resposta = requests.post(
            f"{API_BASE_URL}/{MODEL_ENDPOINT}/{VERSION}",
            params={"api_key": API_KEY, "confidence": confianca, "overlap": sobreposicao},
            data=imagem_base64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=60,
        )
    except requests.RequestException:
        return jsonify(erro="Sem conexão com o Roboflow. Verifique sua internet e tente novamente."), 502

    if resposta.status_code in (401, 403):
        return jsonify(erro="A API_KEY não foi aceita pelo Roboflow. Confira a ROBOFLOW_API_KEY."), 502
    if resposta.status_code == 404:
        return jsonify(erro="Modelo não encontrado. Confira MODEL_ENDPOINT e VERSION no app.py."), 502
    if not resposta.ok:
        return jsonify(erro=f"O Roboflow respondeu com erro {resposta.status_code}: {resposta.text[:200]}"), 502

    return jsonify(predictions=resposta.json().get("predictions", []))


if __name__ == "__main__":
    if not configuracao_preenchida():
        print("\nAtenção: coloque ROBOFLOW_API_KEY no arquivo .env.\n")
    print(f"Abra http://localhost:{PORTA} no navegador.")
    app.run(host="0.0.0.0", port=PORTA, debug=False)
