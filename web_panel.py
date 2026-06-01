import logging
import os

from flask import Flask, Response, render_template_string

from output_stream import fila_web

logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)

_HTML_HACKER = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VIGILANTE MASTER // CORE TERMINAL</title>
    <style>
        body {
            background-color: #030303;
            color: #00ff33;
            font-family: 'Courier New', Courier, monospace;
            margin: 0;
            padding: 10px;
            overflow: hidden;
        }
        h1 {
            text-align: center;
            text-shadow: 0 0 12px #00ff33;
            border-bottom: 1px dashed #00ff33;
            padding-bottom: 10px;
            font-size: clamp(1rem, 4vw, 1.4rem);
            letter-spacing: 1px;
            margin-top: 5px;
        }
        #painel-logs {
            height: 85vh;
            overflow-y: auto;
            background-color: #000000;
            border: 1px solid #00ff33;
            padding: 15px;
            box-shadow: inset 0 0 20px #002200, 0 0 15px #00ff33;
            font-size: clamp(0.85rem, 3vw, 1rem);
        }
        .linha {
            margin-bottom: 8px;
            line-height: 1.5;
            word-wrap: break-word;
        }
        .cursor {
            display: inline-block;
            width: 8px;
            height: 15px;
            background-color: #00ff33;
            animation: piscar 1s infinite;
            vertical-align: middle;
            margin-left: 2px;
        }
        @keyframes piscar {
            0%, 49% { opacity: 1; }
            50%, 100% { opacity: 0; }
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #000; border-left: 1px solid #00ff33; }
        ::-webkit-scrollbar-thumb { background: #00ff33; }
    </style>
</head>
<body>
    <h1>[ 👁️ VIGILANTE MASTER v14.0 ]</h1>
    <div id="painel-logs">
        <div class="linha">>> Inicializando handshake com a infraestrutura local... OK.</div>
        <div class="linha">>> Conectando canais de streaming SSE... OK.</div><br>
    </div>

    <script>
        const painel = document.getElementById('painel-logs');
        const evento = new EventSource('/stream');
        let filaDigitacao = Promise.resolve();

        function digitarTexto(elemento, htmlCompleto, velocidade = 10) {
            return new Promise(resolve => {
                let i = 0;
                let isTag = false;
                let textoExibido = "";

                elemento.innerHTML = '<span class="cursor"></span>';

                function proximoCaractere() {
                    if (i < htmlCompleto.length) {
                        let char = htmlCompleto.charAt(i);
                        textoExibido += char;
                        elemento.innerHTML = textoExibido + '<span class="cursor"></span>';
                        if (char === '<') isTag = true;
                        if (char === '>') isTag = false;
                        i++;
                        painel.scrollTop = painel.scrollHeight;
                        if (isTag) {
                            proximoCaractere();
                        } else {
                            setTimeout(proximoCaractere, velocidade);
                        }
                    } else {
                        elemento.innerHTML = textoExibido;
                        resolve();
                    }
                }
                proximoCaractere();
            });
        }

        evento.onmessage = function(event) {
            const novaLinha = document.createElement('div');
            novaLinha.className = 'linha';
            painel.appendChild(novaLinha);
            filaDigitacao = filaDigitacao.then(() => digitarTexto(novaLinha, ">> " + event.data));
        };

        evento.onerror = function() {
            console.log("Aguardando reconexão de pacotes do servidor...");
        };
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(_HTML_HACKER)


@app.route('/stream')
def stream():
    def gerar_eventos():
        while True:
            msg = fila_web.get()
            yield f"data: {msg}\n\n"
    return Response(gerar_eventos(), mimetype='text/event-stream')


def iniciar_servidor_web():
    port = int(os.getenv("FLASK_PORT", "8080"))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
