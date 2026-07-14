from detector import AndamentoInicial, Detector, FalhaCaptura, Mudanca


def _proc(pid="TJRJ_1", numero="123", ultimo=None):
    return {"id": pid, "numero": numero, "ultimo_andamento": ultimo}


def test_andamento_inicial_quando_nao_ha_historico():
    det = Detector()
    res = det.processar(_proc(ultimo=None), "TJRJ", "Movimento A", "img.png")
    assert isinstance(res, AndamentoInicial)
    assert res.pid == "TJRJ_1"
    assert res.txt_novo == "Movimento A"


def test_mudanca_detectada_quando_texto_difere():
    det = Detector()
    res = det.processar(_proc(ultimo="Movimento A"), "STF", "Movimento B", "img.png")
    assert isinstance(res, Mudanca)
    assert res.txt_novo == "Movimento B"
    assert res.tribunal == "STF"
    assert res.img == "img.png"


def test_sem_novidades_retorna_none():
    det = Detector()
    res = det.processar(_proc(ultimo="Movimento A"), "TJRJ", "Movimento A", None)
    assert res is None


def test_sem_novidades_ignora_espacos_em_branco():
    det = Detector()
    res = det.processar(_proc(ultimo="  Movimento A  "), "TJRJ", "Movimento A\n", None)
    assert res is None


def test_falha_captura_incrementa_contagem():
    det = Detector()
    r1 = det.processar(_proc(), "TSE", None, None)
    r2 = det.processar(_proc(), "TSE", None, None)
    assert isinstance(r1, FalhaCaptura) and r1.contagem == 1
    assert isinstance(r2, FalhaCaptura) and r2.contagem == 2
    assert r2.tribunal == "TSE"


def test_sucesso_reseta_contador_de_falhas():
    det = Detector()
    det.processar(_proc(), "TSE", None, None)
    det.processar(_proc(), "TSE", None, None)
    # Captura volta a funcionar -> contador zera
    det.processar(_proc(ultimo="X"), "TSE", "Y", None)
    # Nova falha deve recomeçar do 1
    nova = det.processar(_proc(), "TSE", None, None)
    assert isinstance(nova, FalhaCaptura)
    assert nova.contagem == 1


def test_limite_alerta_configuravel():
    det = Detector(limite_alerta=2)
    assert det.limite_alerta == 2


def test_fingerprint_igual_nao_dispara_mudanca_mesmo_com_texto_diferente():
    """Cenario-chave do bug: textos brutos diferentes (conteudo dinamico) mas
    fingerprint igual (mesmos itens) -> NAO dispara Mudanca."""
    det = Detector()
    proc = {"id": "TSE_1", "numero": "0603507-14.2022.6.19.0000", "ultimo_fingerprint": "abc123"}
    # Texto bruto diferente (simula timestamp de "ultima consulta" variando)
    # mas fingerprint igual -> sem Mudanca
    res = det.processar(
        proc, "TSE",
        "Movimentos\nRecebidos os autos\n29/06/2026\n[ultima consulta: HH:MM:SS]",
        "img.png", fingerprint="abc123",
    )
    assert res is None


def test_fingerprint_diferente_dispara_mudanca():
    """Itens realmente diferentes -> Mudanca mesmo com fingerprint novo."""
    det = Detector()
    proc = {"id": "TSE_1", "numero": "0603507-14.2022.6.19.0000", "ultimo_fingerprint": "abc123"}
    res = det.processar(
        proc, "TSE", "texto qualquer", "img.png", fingerprint="xyz999",
    )
    assert isinstance(res, Mudanca)
    assert res.fingerprint == "xyz999"


def test_fingerprint_vazio_fallback_para_comparacao_de_texto():
    """Se nem fingerprint novo nem antigo existem, usa texto (backward compat)."""
    det = Detector()
    proc = {"id": "TSE_1", "numero": "0603507-14.2022.6.19.0000"}  # sem fingerprint
    res = det.processar(proc, "TSE", "novo texto", None, fingerprint=None)
    assert isinstance(res, AndamentoInicial)
    assert res.fingerprint is None


def test_andamento_inicial_quando_nao_ha_fingerprint_nem_texto():
    """Primeira extracao: sem fingerprint nem ultimo_andamento -> AndamentoInicial."""
    det = Detector()
    proc = {"id": "TSE_1", "numero": "0603507-14.2022.6.19.0000"}
    res = det.processar(proc, "TSE", "primeiro texto", None, fingerprint="fp1")
    assert isinstance(res, AndamentoInicial)
    assert res.fingerprint == "fp1"
