from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class AndamentoInicial:
    pid: str
    txt_novo: str
    fingerprint: Optional[str] = None


@dataclass
class Mudanca:
    pid: str
    txt_novo: str
    tribunal: str
    proc: dict
    img: Optional[str]
    fingerprint: Optional[str] = None


@dataclass
class FalhaCaptura:
    pid: str
    numero: str
    tribunal: str
    contagem: int


class Detector:
    def __init__(self, limite_alerta: int = 5):
        self._falhas: dict[str, int] = {}
        self.limite_alerta = limite_alerta

    def processar(
        self,
        proc: dict,
        tribunal: str,
        txt: Optional[str],
        img: Optional[str],
        fingerprint: Optional[str] = None,
    ) -> Union[AndamentoInicial, Mudanca, FalhaCaptura, None]:
        pid = proc['id']

        if not txt:
            contagem = self._falhas.get(pid, 0) + 1
            self._falhas[pid] = contagem
            return FalhaCaptura(
                pid=pid,
                numero=proc['numero'],
                tribunal=tribunal,
                contagem=contagem,
            )

        self._falhas[pid] = 0
        txt_novo = txt.strip()
        fp_antigo = proc.get('ultimo_fingerprint')

        # Se temos fingerprint novo E antigo, comparacao por hash (robusto contra
        # conteudo dinamico como timestamps ou IDs de sessao que variam entre
        # page-loads). Caso contrario, fallback para comparacao de texto.
        if fingerprint and fp_antigo:
            if fingerprint != fp_antigo:
                return Mudanca(
                    pid=pid, txt_novo=txt_novo, tribunal=tribunal, proc=proc, img=img,
                    fingerprint=fingerprint,
                )
            return None

        txt_antigo = proc.get('ultimo_andamento')
        if txt_antigo:
            txt_antigo = txt_antigo.strip()

        if not txt_antigo and not fp_antigo:
            return AndamentoInicial(pid=pid, txt_novo=txt_novo, fingerprint=fingerprint)

        if txt_novo != txt_antigo:
            return Mudanca(
                pid=pid, txt_novo=txt_novo, tribunal=tribunal, proc=proc, img=img,
                fingerprint=fingerprint,
            )

        return None
