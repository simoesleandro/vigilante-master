import pytest

from repo import ProcessoRepo


@pytest.fixture
def repo():
    # :memory: mantém uma conexão viva isolada por instância (sem tocar disco).
    return ProcessoRepo(db_path=":memory:")


def test_seed_inicial_carregado(repo):
    todos = repo.list_todos()
    assert len(todos) == 9  # 4 TJRJ + 3 STF + 2 TSE


def test_get_processo_existente(repo):
    proc = repo.get_processo("TJRJ_1")
    assert proc is not None
    assert proc["tribunal"] == "TJRJ"
    assert proc["numero"] == "3004566-28.2026.8.19.0000"


def test_get_processo_inexistente_retorna_none(repo):
    assert repo.get_processo("NAO_EXISTE") is None


def test_list_processos_filtra_por_tribunal(repo):
    assert len(repo.list_processos("TJRJ")) == 4
    assert len(repo.list_processos("STF")) == 3
    assert len(repo.list_processos("TSE")) == 2


def test_add_e_pid_exists(repo):
    assert repo.pid_exists("STF_9") is False
    repo.add_processo(
        "STF_9", "ADI 1", "http://x", "STF",
        "Requerente", "Fulano", "Ação", "resumo",
    )
    assert repo.pid_exists("STF_9") is True
    novo = repo.get_processo("STF_9")
    assert novo["parte_nome"] == "Fulano"


def test_save_andamento_atualiza_campo(repo):
    repo.save_andamento("TJRJ_1", "Andamento atualizado")
    proc = repo.get_processo("TJRJ_1")
    assert proc["ultimo_andamento"] == "Andamento atualizado"


def test_delete_processo_remove_do_banco(repo):
    repo.delete_processo("TJRJ_1")
    assert repo.get_processo("TJRJ_1") is None
    assert len(repo.list_todos()) == 8


def test_contexto_persiste_e_recupera_em_ordem(repo):
    repo.add_contexto("TJRJ_1", "01/01/2026 10:00", "Primeira nota")
    repo.add_contexto("TJRJ_1", "02/01/2026 11:00", "Segunda nota")
    hist = repo.get_historico_contexto("TJRJ_1")
    assert len(hist) == 2
    assert hist[0][1] == "Primeira nota"
    assert hist[1][1] == "Segunda nota"


def test_delete_processo_remove_contexto_associado(repo):
    repo.add_contexto("TJRJ_1", "01/01/2026 10:00", "Nota")
    repo.delete_processo("TJRJ_1")
    assert repo.get_historico_contexto("TJRJ_1") == []


def test_save_resumo_round_trip_evolutivo(repo):
    repo.save_resumo("TJRJ_1", "Resumo evoluido pela IA")
    proc = repo.get_processo("TJRJ_1")
    assert proc["resumo"] == "Resumo evoluido pela IA"


def test_save_resumo_vazio_e_ignorado(repo):
    # Pega o resumo inicial do seed (TJRJ_1)
    antes = repo.get_processo("TJRJ_1")["resumo"]
    assert antes, "seed sem resumo_inicial?"
    # Tenta gravar vazio
    repo.save_resumo("TJRJ_1", "")
    repo.save_resumo("TJRJ_1", "   ")
    depois = repo.get_processo("TJRJ_1")["resumo"]
    assert depois == antes, f"guard falhou: resumo mudou para {depois!r}"


def test_update_processo_muda_numero(repo):
    novo = "9999999-99.2099.8.19.0000"
    ok = repo.update_processo("TJRJ_1", numero=novo)
    assert ok is True
    assert repo.get_processo("TJRJ_1")["numero"] == novo


def test_update_processo_rejeita_campo_nao_permitido(repo):
    # A whitelist filtra campos fora de {numero, url, tribunal, parte_label,
    # parte_nome, classe}. `pid` colide com o parâmetro posicional
    # (TypeError) e `resumo` é filtrado pela whitelist.
    # Aqui usamos um nome arbitrário (não-whitelist) para provar o filtro.
    antes_numero = repo.get_processo("TJRJ_1")["numero"]
    antes_resumo = repo.get_processo("TJRJ_1")["resumo"]
    # resumo não está na whitelist, então é filtrado → sets vazio → False
    ok = repo.update_processo("TJRJ_1", resumo="WRONG_RESUMO")
    assert ok is False
    # Nada mudou
    assert repo.get_processo("TJRJ_1")["numero"] == antes_numero
    assert repo.get_processo("TJRJ_1")["resumo"] == antes_resumo


def test_exportar_importar_roundtrip(repo):
    # Adiciona contexto no TJRJ_1 para garantir que o roundtrip inclui histórico
    repo.add_contexto("TJRJ_1", "01/01/2026 10:00", "Nota de teste")
    exportado = repo.exportar()
    assert len(exportado) == 9
    tjrj1 = next(p for p in exportado if p["id"] == "TJRJ_1")
    assert tjrj1["contexto"] and tjrj1["contexto"][0][1] == "Nota de teste"
    assert tjrj1["numero"] == "3004566-28.2026.8.19.0000"

    # importar é idempotente: pids existentes são pulados
    n = repo.importar(exportado)
    assert n == 0
    assert len(repo.list_todos()) == 9

    # importar com pids NOVOS adiciona e preserva o contexto
    novos = [
        {
            "id": "NOVO_1",
            "numero": "0001", "url": "u", "tribunal": "TJRJ",
            "parte_label": "Req", "parte_nome": "Fulano",
            "classe": "Classe X", "resumo": "Resumo novo",
            "contexto": [["02/02/2026 09:00", "Contexto novo"]],
        },
        {
            "id": "NOVO_2",
            "numero": "0002", "url": "u2", "tribunal": "STF",
            "parte_label": "Req", "parte_nome": "Ciclano",
            "classe": "Classe Y", "resumo": "Outro resumo",
            "contexto": [],
        },
    ]
    n2 = repo.importar(novos)
    assert n2 == 2
    assert repo.pid_exists("NOVO_1")
    assert repo.get_historico_contexto("NOVO_1")[0][1] == "Contexto novo"
    # Re-importar os mesmos novos é idempotente
    assert repo.importar(novos) == 0
