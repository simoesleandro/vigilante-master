import queue
import sys
import os

sys.__stdout__.reconfigure(encoding='utf-8', write_through=True)
sys.__stderr__.reconfigure(encoding='utf-8', write_through=True)

fila_web: queue.Queue = queue.Queue()


class CloneTerminal:
    def __init__(self, terminal_original):
        self.terminal_original = terminal_original

    def write(self, mensagem):
        self.terminal_original.write(mensagem)
        self.terminal_original.flush()
        try:
            caminho_log = "Z:\\terminal.log" if os.path.exists("Z:\\") else "terminal.log"
            with open(caminho_log, "a", encoding="utf-8") as f:
                f.write(mensagem)
        except Exception:
            try:
                with open("terminal.log", "a", encoding="utf-8") as f:
                    f.write(mensagem)
            except Exception:
                pass
        if mensagem.strip():
            msg_segura = mensagem.replace('\n', '').replace('\r', '')
            fila_web.put(msg_segura)

    def flush(self):
        self.terminal_original.flush()


def ativar():
    sys.stdout = CloneTerminal(sys.__stdout__)
    sys.stderr = CloneTerminal(sys.__stderr__)
