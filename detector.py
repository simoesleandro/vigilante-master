from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class AndamentoInicial:
    pid: str
    txt_novo: str


@dataclass
class Mudanca:
    pid: str
    txt_novo: str
    tribunal: str
    proc: dict
    img: Optional[str]


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
        txt_antigo = proc.get('ultimo_andamento')
        if txt_antigo:
            txt_antigo = txt_antigo.strip()

        if not txt_antigo:
            return AndamentoInicial(pid=pid, txt_novo=txt_novo)

        if txt_novo != txt_antigo:
            return Mudanca(pid=pid, txt_novo=txt_novo, tribunal=tribunal, proc=proc, img=img)

        return None
