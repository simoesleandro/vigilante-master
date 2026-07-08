import os
import tempfile

from carteiro import montar_mensagem


def _t(conteudo, **extra):
    return {"conteudo": conteudo, "tribunal": "STF", "img": extra.get("img"), **extra}


def _p(numero="001", classe="Classe", parte_nome="Parte", url="https://x.test", **kw):
    return {"numero": numero, "classe": classe, "parte_nome": parte_nome,
            "parte_label": "Impetrante", "url": url, **kw}


def test_texto_curto_nao_truncado():
    html_out, _ = montar_mensagem(_t("movimentação normal"), _p(), "01/01/2026")
    assert "[Texto cortado" not in html_out
    assert "movimentação normal" in html_out


def test_texto_longo_truncado():
    long = "x" * 300
    html_out, _ = montar_mensagem(_t(long), _p(), "01/01/2026")
    assert "[Texto cortado" in html_out
    assert "..." in html_out


def test_chars_especiais_sao_escapados():
    html_out, _ = montar_mensagem(_t("<b>bold</b> & <i>"), _p(), "01/01/2026")
    assert "<b>bold</b>" not in html_out
    assert "&lt;b&gt;bold&lt;/b&gt;" in html_out


def test_parte_nome_com_html_escapado():
    html_out, _ = montar_mensagem(_t("ok"), _p(parte_nome="<script>x</script>"), "01/01/2026")
    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out


def test_sem_foto_quando_arquivo_nao_existe():
    _, tem_foto = montar_mensagem(_t("ok", img="/nao/existe.png"), _p(), "01/01/2026")
    assert tem_foto is False


def test_com_foto_quando_arquivo_existe():
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        _, tem_foto = montar_mensagem(_t("ok", img=f.name), _p(), "01/01/2026")
        assert tem_foto is True
