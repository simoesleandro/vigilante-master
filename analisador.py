from google import genai

_MODELOS = ['models/gemini-3.1-flash-lite', 'models/gemini-flash-latest']


class AnalisadorJuridico:
    def __init__(self, client: genai.Client):
        self._client = client

    def analisar(self, processo: dict, andamentos: str, historico: list) -> str:
        historico_txt = ""
        if historico:
            historico_txt = "\n\n--- 🧠 MEMÓRIA DO ADVOGADO (Interações Anteriores):\n"
            for data_hora, texto in historico:
                historico_txt += f"[{data_hora}] Nota: {texto}\n"

        instrucao_extra = ""
        if historico_txt:
            instrucao_extra = (
                "O advogado responsável adicionou NOTAS e ATUALIZAÇÕES na seção 'MEMÓRIA DO ADVOGADO'. "
                "Considere essa linha do tempo para guiar seu raciocínio estratégico."
            )

        resumo_base = processo.get("resumo", "Contexto base não fornecido.")

        prompt = (
            f"Você é um consultor jurídico sênior auxiliando um advogado experiente. "
            f"Analise o processo {processo['numero']}.\n"
            "Sua tarefa é cruzar o CONTEXTO BASE da ação com os ANDAMENTOS RECENTES do tribunal, "
            "explicando como as novidades impactam a tese fundamental do caso.\n"
            f"{instrucao_extra}\n\n"
            "⚠️ REGRAS ESTRITAS DE FORMATAÇÃO:\n"
            "1. NUNCA use os símbolos '#' ou '*' ou '**' na sua resposta.\n"
            "2. Seja direto, técnico e focado na estratégia processual.\n"
            "3. Estruture a resposta EXATAMENTE com estes 3 tópicos, usando os emojis:\n\n"
            "📌 STATUS ATUAL: (Sintetize a evolução do caso cruzando a base com a novidade)\n\n"
            "⚖️ PONTOS DE ATENÇÃO:\n"
            "- (Item 1 crítico dos andamentos)\n"
            "- (Item 2 crítico dos andamentos)\n\n"
            "💡 RECOMENDAÇÃO: (Qual a próxima peça ou atitude estratégica a tomar)\n\n"
            f"--- CONTEXTO BASE DO PROCESSO:\n{resumo_base}\n\n"
            f"--- ANDAMENTOS RECENTES CAPTURADOS:\n{andamentos}"
            f"{historico_txt}"
        )

        return self._chamar_gemini(prompt)

    def resumo_evolutivo(self, processo: dict, andamento_novo: str) -> str:
        resumo_atual = processo.get("resumo", "")
        numero = processo.get("numero", "")

        prompt = (
            f"Você é um assistente jurídico encarregado de manter o resumo do processo {numero} atualizado.\n"
            f"Abaixo está o RESUMO ATUAL do caso e uma NOVA MOVIMENTAÇÃO que acabou de acontecer.\n"
            f"Sua tarefa é reescrever o resumo, incorporando a nova movimentação de forma concisa, "
            f"mantendo o histórico importante e atualizando o status do processo.\n\n"
            f"⚠️ REGRAS:\n"
            f"1. Use formatação HTML básica (<b>, <i>, <u>).\n"
            f"2. NUNCA use os símbolos '#', '*' ou '**'.\n"
            f"3. Seja muito conciso (máximo de 3 parágrafos).\n\n"
            f"--- RESUMO ATUAL:\n{resumo_atual}\n\n"
            f"--- NOVA MOVIMENTAÇÃO:\n{andamento_novo}"
        )

        return self._chamar_gemini(prompt)

    def _chamar_gemini(self, prompt: str) -> str:
        for modelo in _MODELOS:
            try:
                resposta = self._client.models.generate_content(model=modelo, contents=prompt)
                if resposta:
                    return (
                        resposta.text
                        .replace("###", "")
                        .replace("##", "")
                        .replace("**", "")
                    )
            except Exception:
                continue
        return ""
