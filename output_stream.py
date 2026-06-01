import queue
import sys

fila_web: queue.Queue = queue.Queue()


class CloneTerminal:
    def __init__(self):
        self.terminal_original = sys.__stdout__

    def write(self, mensagem):
        self.terminal_original.write(mensagem)
        self.terminal_original.flush()
        if mensagem.strip():
            msg_segura = mensagem.replace('\n', '').replace('\r', '')
            fila_web.put(msg_segura)

    def flush(self):
        self.terminal_original.flush()


def ativar():
    sys.stdout = CloneTerminal()
