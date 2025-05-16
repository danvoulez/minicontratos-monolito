import os
import hmac
import hashlib
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv
import requests
from time import time, sleep

# --- Configuração de logging detalhado ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# --- Carregamento de variáveis de ambiente ---
load_dotenv()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 20))  # segundos
LLM_RETRIES = int(os.getenv("LLM_RETRIES", 2))

app = Flask(__name__)

def verificar_assinatura(secret, payload, signature_header):
    """
    Verifica a assinatura HMAC SHA256 do payload do webhook.
    """
    if not secret or not signature_header:
        logging.warning("Assinatura ausente ou segredo não configurado.")
        return False
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    resultado = hmac.compare_digest(expected, signature_header)
    if not resultado:
        logging.warning("Assinatura inválida.")
    return resultado

def chamar_llm(event_name, payload):
    """
    Chama o modelo LLM da API GitHub Models para gerar a LogLine.
    Tenta até LLM_RETRIES vezes em caso de erro/transient.
    """
    url = "https://api.github.com/models/copilot-chat"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    messages = [
        {
            "role": "system",
            "content": (
                "Você é um agente institucional. Gere uma LogLine JSON para registrar eventos do GitHub. "
                "Formato obrigatório:\n"
                '{\n'
                '  "who": "github_app",\n'
                '  "did": "registrar_evento",\n'
                '  "this": "<resumo do evento>",\n'
                '  "status": "executed",\n'
                '  "confirmed_by": ["PromptOS"],\n'
                '  "emitted_at": "<timestamp UTC ISO>"\n'
                '}\n'
                "Responda SOMENTE com o JSON."
            )
        },
        {
            "role": "user",
            "content": f"Evento {event_name}:\n{json.dumps(payload, ensure_ascii=False)}"
        }
    ]
    data = {"messages": messages}

    for tentativa in range(1, LLM_RETRIES + 1):
        try:
            logging.info(f"Chamando LLM (tentativa {tentativa}/{LLM_RETRIES})")
            ini = time()
            resp = requests.post(url, headers=headers, json=data, timeout=LLM_TIMEOUT)
            dur = time() - ini
            logging.info(f"Tempo de resposta LLM: {dur:.2f}s Status: {resp.status_code}")
            if resp.status_code == 200:
                text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                first_brace = text.find("{")
                last_brace = text.rfind("}")
                logline = json.loads(text[first_brace:last_brace+1])
                return logline, "copilot-chat"
            else:
                logging.warning(f"LLM falhou: {resp.status_code} {resp.text}")
        except Exception as e:
            logging.error(f"Erro ao chamar LLM: {e}")
        sleep(0.8)  # pequena pausa entre tentativas
    return None, "local-fallback"

def gerar_logline_fallback(event_name, payload, erro="LLM indisponível"):
    """
    Fallback local: gera logline padrão robusta.
    """
    return {
        "who": "github_app",
        "did": "registrar_evento",
        "this": f"Evento {event_name} recebido. (fallback local: {erro})",
        "status": "executed",
        "confirmed_by": ["PromptOS"],
        "emitted_at": datetime.utcnow().isoformat() + "Z",
        "erro": erro,
        "payload_excerpt": str(payload)[:250]
    }

def salvar_logline(logline):
    """
    Imprime a LogLine no console e salva como arquivo JSON se loglines/ existir.
    """
    print(json.dumps(logline, ensure_ascii=False, indent=2))
    if os.path.isdir("loglines"):
        ts = logline.get("emitted_at", datetime.utcnow().isoformat())
        fname = ts.replace(":", "-").replace(".", "-") + ".json"
        fpath = os.path.join("loglines", fname)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(logline, f, ensure_ascii=False, indent=2)
            logging.info(f"LogLine salva em: {fpath}")
        except Exception as e:
            logging.error(f"Falha ao salvar logline: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    # Verifica assinatura do webhook do GitHub
    signature = request.headers.get("X-Hub-Signature-256")
    raw_body = request.get_data()
    if not verificar_assinatura(WEBHOOK_SECRET, raw_body, signature):
        return jsonify({"erro": "Assinatura inválida ou ausente."}), 401

    event_name = request.headers.get("X-GitHub-Event", "unknown_event")
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"erro": "Payload ausente ou inválido."}), 400

    logline, origem = chamar_llm(event_name, payload)
    if not logline or not isinstance(logline, dict) or "who" not in logline:
        logline = gerar_logline_fallback(event_name, payload)

    salvar_logline(logline)
    return jsonify({
        "logline": logline,
        "llm_usado": origem
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
