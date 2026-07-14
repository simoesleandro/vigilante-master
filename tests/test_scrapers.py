"""Testes dos helpers do scraper TSE (scrapers.py).

Cobre dois fixes:
1. _esperar_card_estavel: aguarda N leituras consecutivas identicas do card
   (resolvia bug de loading parcial, mas so nao bastou — ver #2)
2. _fingerprint_itens: hash dos pares titulo+data, ignorando header/linhas
   dinamicas que poluem o card.text
"""
import time
from unittest.mock import MagicMock, PropertyMock

from scrapers import _esperar_card_estavel, _fingerprint_itens


def _card_mock_text(text_sequence):
    """Cria mock de card onde .text retorna cada item de text_sequence em chamadas sucessivas."""
    card = MagicMock()
    type(card).text = PropertyMock(side_effect=text_sequence)
    return card


def test_retorna_true_quando_card_ja_esta_estavel_na_primeira_leitura():
    texto = "Movimentos\nRecebidos os autos\n29/06/2026, 10:21:23" + "x" * 100
    card = _card_mock_text([texto, texto, texto])
    assert _esperar_card_estavel(card, timeout=10, poll=0.01) is True


def test_retorna_true_quando_estabiliza_apos_algumas_leituras():
    """Cenario real: card renderiza em 3 estagios (1, 3, 5 itens) antes de parar."""
    texto_parcial_1 = "Movimentos\nItem A\n01/01/2026"
    texto_parcial_2 = texto_parcial_1 + "\nItem B\n02/01/2026\nItem C\n03/01/2026"
    texto_final = texto_parcial_2 + "\nItem D\n04/01/2026\nItem E\n05/01/2026"
    sequencia = [texto_parcial_1, texto_parcial_2, texto_final, texto_final, texto_final, texto_final]
    card = _card_mock_text(sequencia)
    assert _esperar_card_estavel(card, timeout=10, poll=0.01) is True


def test_retorna_false_quando_texto_nunca_estabiliza_dentro_do_timeout():
    """Se a pagina ficar mudando para sempre (ex: spinner eterno), retorna False apos timeout."""
    contador = [0]

    def texto_sempre_diferente():
        contador[0] += 1
        return f"texto diferente {contador[0]} " + "x" * 100

    card = _card_mock_text(texto_sempre_diferente)
    inicio = time.time()
    resultado = _esperar_card_estavel(card, timeout=1, poll=0.1)
    duracao = time.time() - inicio
    assert resultado is False
    assert duracao < 2.0  # respeita o timeout (nao bloqueia infinitamente)


def test_retorna_false_se_card_levanta_excecao():
    card = MagicMock()
    type(card).text = PropertyMock(side_effect=Exception("stale element"))
    assert _esperar_card_estavel(card, timeout=5, poll=0.01) is False


def test_ignora_textos_muito_curtos_nao_conta_como_estavel():
    """Se o card.text vier com < 50 chars, NAO conta como estavel (heuristica de seguranca)."""
    card = _card_mock_text(["curto"] * 10)
    assert _esperar_card_estavel(card, timeout=1, poll=0.01) is False


def test_estabilizacao_com_3_leituras_consecutivas_e_mais_robusta():
    """A configuracao padrao agora exige 3 leituras identicas (era 2).

    Cenario: pagina ainda renderizando (1, 3, 5, 5, 5, 5 itens) — so na 3a
    leitura estavel e que confirmamos que parou de mudar.
    """
    texto_p1 = "Movimentos\nItem A\n01/01/2026"
    texto_p2 = texto_p1 + "\nItem B\n02/01/2026\nItem C\n03/01/2026"
    texto_final = texto_p2 + "\nItem D\n04/01/2026\nItem E\n05/01/2026"
    sequencia = [texto_p1, texto_p2, texto_final, texto_final, texto_final, texto_final]
    card = _card_mock_text(sequencia)
    assert _esperar_card_estavel(card, timeout=10, poll=0.01, leituras=3) is True


def test_fingerprint_estavel_para_mesmos_itens():
    """Mesmos andamentos = mesmo hash, mesmo que o texto bruto tenha variacoes."""
    linhas = [
        "Movimentos",
        "Recebidos os autos", "29/06/2026, 10:21:23",
        "Conclusos para decisão", "29/06/2026, 10:21:23",
        "Remetidos os Autos", "29/06/2026, 10:21:23",
    ]
    assert _fingerprint_itens(linhas) == _fingerprint_itens(list(linhas))


def test_fingerprint_muda_quando_item_e_adicionado_no_topo():
    """Novo movimento no topo deve gerar hash diferente (Mudanca real)."""
    fp_base = _fingerprint_itens([
        "Movimentos",
        "Recebidos os autos", "29/06/2026, 10:21:23",
        "Conclusos para decisão", "29/06/2026, 10:21:23",
    ])
    fp_com_novo = _fingerprint_itens([
        "Movimentos",
        "Nova movimentação no topo", "30/06/2026, 12:00:00",
        "Recebidos os autos", "29/06/2026, 10:21:23",
        "Conclusos para decisão", "29/06/2026, 10:21:23",
    ])
    assert fp_base != fp_com_novo


def test_fingerprint_ignora_linhas_extras_apos_os_itens():
    """Linhas alem dos pares titulo+data nao afetam o hash.

    Este e o cenario do bug: o card tem um rodape com timestamp ou
    'ultima consulta' que muda entre page-loads mas NAO e dado de movimento.
    Como nossa funcao so pega os pares ate o limite, esses elementos sao
    naturalmente ignorados.
    """
    fp_sem_rodape = _fingerprint_itens([
        "Movimentos",
        "Item A", "01/01/2026",
        "Item B", "02/01/2026",
    ])
    fp_com_rodape_diferente = _fingerprint_itens([
        "Movimentos",
        "Item A", "01/01/2026",
        "Item B", "02/01/2026",
        "Ultima consulta: 31/12/2026 23:59:59",  # dinamica
        "ID sessao: abc123xyz",                   # dinamica
    ])
    assert fp_sem_rodape == fp_com_rodape_diferente


def test_fingerprint_vazio_para_linhas_insuficientes():
    """Se o card nao tem nem header + 1 item, fingerprint fica vazio (string MD5 de '')."""
    fp_vazio = _fingerprint_itens(["Movimentos"])
    fp_header_only = _fingerprint_itens(["Movimentos", "Item solto"])
    # Sem pares completos, ambos devem cair no mesmo caso (sem itens)
    assert fp_vazio == fp_header_only
    assert len(fp_vazio) == 32  # MD5 hex tem 32 chars
