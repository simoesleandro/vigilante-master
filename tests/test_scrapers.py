"""Testes do helper _esperar_card_estavel (scrapers.py).

O bug original: a SPA do TSE renderiza andamentos de forma incremental
apos o captcha. O codigo antigo usava `time.sleep(2)` fixo, o que capturava
estados parciais (1, 3, 5, 7 itens) -> falsos positivos no Detector.

O fix: esperar ate que 2 leituras consecutivas de `card.text` sejam
identicas, com timeout de seguranca.
"""
import time
from unittest.mock import MagicMock, PropertyMock

from scrapers import _esperar_card_estavel


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
