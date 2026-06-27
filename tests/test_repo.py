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
