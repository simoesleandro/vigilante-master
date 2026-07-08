import queue
import sys

sys.__stdout__.reconfigure(encoding='utf-8', write_through=True)
sys.__stderr__.reconfigure(encoding='utf-8', write_through=True)

fila_web: queue.Queue = queue.Queue(maxsize=2000)


class CloneTerminal:
    def __init__(self):
        self.terminal_original = sys.__stdout__

    def write(self, mensagem):
        self.terminal_original.write(mensagem)
        self.terminal_original.flush()
        if mensagem.strip():
            msg_segura = mensagem.replace('\n', '').replace('\r', '')
            try:
                fila_web.put_nowait(msg_segura)
            except queue.Full:
                pass  # painel de log é lossy; descarta linha antiga virtual

    def flush(self):
        self.terminal_original.flush()


def ativar():
    sys.stdout = CloneTerminal()
