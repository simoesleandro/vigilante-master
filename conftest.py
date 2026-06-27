import os
import sys

# Garante que os módulos da raiz (detector, repo, ...) sejam importáveis nos testes.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
