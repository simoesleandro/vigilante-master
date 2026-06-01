import sqlite3
from typing import Optional

_SEED_PROCESSOS = [
    {
        "id": "TJRJ_1", "tribunal": "TJRJ",
        "numero": "3004566-28.2026.8.19.0000",
        "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_nome_parte_publica&acao_retorno=processo_consulta_nome_parte_publica&num_processo=30045662820268190000&num_chave=&hash=b33f48b0cc0ad69e5cd182e3751fd64e&num_chave_documento=",
        "parte_label": "Impetrante", "parte_nome": "PDT - PARTIDO DEMOCRÁTICO TRABALHISTA DIRETÓRIO RJ",
        "classe": "Mandado de Segurança Cível (Órgão Especial)",
        "resumo": "🏛️ <b>RESUMO TJRJ_1:</b>\n\n<b>Cerne:</b> MS contra as regras da eleição da Mesa Diretora da ALERJ (pede voto secreto).\n<b>Última Decisão:</b> Liminar <b>INDEFERIDA</b> sob o argumento de que é assunto interno da casa (<i>interna corporis</i> - Tema 1.120 STF).\n<b>Status:</b> Prazos abertos para manifestação do Estado e MP. Aguardando julgamento de mérito.",
    },
    {
        "id": "TJRJ_2", "tribunal": "TJRJ",
        "numero": "3004326-39.2026.8.19.0000",
        "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30043263920268190000&num_chave=&num_chave_documento=&hash=2ad7164906ea016a598e771470c6a7fb",
        "parte_label": "Impetrante", "parte_nome": "LUIZ PAULO CORRÊA DA ROCHA",
        "classe": "Mandado de Segurança Cível (Órgão Especial)",
        "resumo": "🏛️ <b>RESUMO TJRJ_2:</b>\n\n<b>Cerne:</b> MS individual impetrado por Luiz Paulo contra ato da ALERJ.\n<b>Última Decisão:</b> Despacho de mero expediente em 13/04/2026. Prazo de manifestação do impetrante já encerrou.\n<b>Status:</b> Autos no Órgão Especial aguardando manifestação do MP ou julgamento.",
    },
    {
        "id": "TJRJ_3", "tribunal": "TJRJ",
        "numero": "3004629-53.2026.8.19.0000",
        "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30046295320268190000&num_chave=&num_chave_documento=&hash=85afa7fb1115618798dc54ecb979febd",
        "parte_label": "Impetrante", "parte_nome": "LUIZ PAULO CORRÊA DA ROCHA",
        "classe": "Mandado de Segurança Cível (Órgão Especial)",
        "resumo": "🏛️ <b>RESUMO TJRJ_3:</b>\n\n<b>Cerne:</b> Novo MS de Luiz Paulo visando suspender/invalidar a eleição da Mesa da ALERJ.\n<b>Última Decisão:</b> Liminar <b>INDEFERIDA</b> em 15/04/2026 (mesmo motivo do TJRJ_1: <i>interna corporis</i>).\n<b>Status:</b> Prazos correndo até maio/2026 para o Estado e Impetrante se manifestarem.",
    },
    {
        "id": "TJRJ_4", "tribunal": "TJRJ",
        "numero": "3006257-77.2026.8.19.0000",
        "url": "https://eproc2g-cp.tjrj.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&acao_origem=processo_consulta_publica&acao_retorno=processo_consulta_publica&num_processo=30062577720268190000&num_chave=&num_chave_documento=&hash=da8242e844340fbe2106c1a341df9b82",
        "parte_label": "Requerente", "parte_nome": "PARTIDO DEMOCRÁTICO TRABALHISTA",
        "classe": "Tutela Cautelar Antecedente (Órgão Especial)",
        "resumo": "🏛️ <b>RESUMO TJRJ_4:</b>\n\n<b>Cerne:</b> Ação Cautelar do PDT para tentar forçar uma liminar em apoio ao processo TJRJ_1.\n<b>Última Decisão:</b> Redistribuído por prevenção ao Relator Ricardo Couto.\n<b>Status:</b> Os autos estão conclusos para decisão sobre o pedido de urgência desde 27/04.",
    },
    {
        "id": "STF_1", "tribunal": "STF",
        "numero": "ADI 7942",
        "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7531465",
        "parte_label": "Impetrante", "parte_nome": "PARTIDO SOCIAL DEMOCRÁTICO - PSD DIRETÓRIO NACIONAL",
        "classe": "Ação Direta de Inconstitucionalidade",
        "resumo": "🏛️ <b>RESUMO STF_1:</b>\n\n<b>Cerne:</b> ADI contra as regras da eleição indireta para Governador-Tampão do RJ.\n<b>Última Decisão:</b> Min. Luiz Fux deferiu liminar parcial suspendendo o voto aberto, mas manteve a eleição indireta.\n<b>Status:</b> Em julgamento no Plenário Virtual, aguardando conclusão após pedidos de destaque.",
    },
    {
        "id": "STF_2", "tribunal": "STF",
        "numero": "RLC 92644",
        "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7547470",
        "parte_label": "Reclamante", "parte_nome": "DIRETÓRIO ESTADUAL DO PARTIDO SOCIAL DEMOCRÁTICO DO RIO DE JANEIRO - PSD/RJ",
        "classe": "Reclamação",
        "resumo": "🏛️ <b>RESUMO STF_2:</b>\n\n<b>Cerne:</b> Reclamação para forçar a ALERJ a cumprir a decisão da ADI 7942 (STF_1).\n<b>Última Decisão:</b> Min. Cristiano Zanin deferiu liminar <b>SUSPENDENDO</b> a eleição indireta até decisão final do Plenário.\n<b>Status:</b> Vinculado à ADI 7942. O Presidente do TJRJ segue no comando do Executivo estadual.",
    },
    {
        "id": "STF_3", "tribunal": "STF",
        "numero": "ADPF 1319",
        "url": "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7569263",
        "parte_label": "Requerente", "parte_nome": "PARTIDO DEMOCRÁTICO TRABALHISTA – PDT",
        "classe": "Arguição de Descumprimento de Preceito Fundamental",
        "resumo": "🏛️ <b>RESUMO STF_3:</b>\n\n<b>Cerne:</b> ADPF do PDT também questionando atos da ALERJ sobre a eleição indireta para Governador.\n<b>Última Decisão:</b> Autos conclusos em 05/05/2026 para o Min. Luiz Fux.\n<b>Status:</b> Aguardando decisão liminar urgente do relator.",
    },
    {
        "id": "TSE_1", "tribunal": "TSE",
        "numero": "0603507-14.2022.6.19.0000",
        "url": "https://consultaunificadapje.tse.jus.br/#/public/resultado/0603507-14.2022.6.19.0000",
        "parte_label": "Recorrente", "parte_nome": "COLIGAÇÃO A VIDA VAI MELHORAR / MARCELO RIBEIRO FREIXO",
        "classe": "Recurso Ordinário Eleitoral",
        "resumo": "🗳️ <b>RESUMO TSE_1:</b>\n\n<b>Cerne:</b> Recurso sobre as eleições de 2022 acusando a chapa de Cláudio Castro de conduta vedada a agente público.\n<b>Última Decisão:</b> Acórdão proferido em 23/04/2026. A defense opôs Embargos de Declaração.\n<b>Status:</b> Publicação de intimações em andamento. Aguarda julgamento dos Embargos pela Min. Isabel Gallotti.",
    },
    {
        "id": "TSE_2", "tribunal": "TSE",
        "numero": "0606570-47.2022.6.19.0000",
        "url": "https://consultaunificadapje.tse.jus.br/#/public/resultado/0606570-47.2022.6.19.0000",
        "parte_label": "Recorrente", "parte_nome": "MINISTÉRIO PÚBLICO ELEITORAL",
        "classe": "Recurso Ordinário Eleitoral",
        "resumo": "🗳️ <b>RESUMO TSE_2:</b>\n\n<b>Cerne:</b> Processo-irmão do TSE_1, focado em abuso de poder econômico nas eleições de 2022.\n<b>Última Decisão:</b> Acórdão proferido em 23/04/2026. Defesa opôs Embargos de Declaração.\n<b>Status:</b> Intimações publicadas no DJE. Autos conclusos para análise dos Embargos pela relatora.",
    },
]


class ProcessoRepo:
    def __init__(self, db_path: str = "memoria_vigilante.db"):
        self._db_path = db_path
        self._inicializar_banco()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _inicializar_banco(self) -> None:
        try:
            conn = self._conn()
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processos (
                    pid TEXT PRIMARY KEY,
                    numero TEXT,
                    url TEXT,
                    tribunal TEXT,
                    parte_label TEXT,
                    parte_nome TEXT,
                    classe TEXT,
                    resumo_inicial TEXT,
                    ultimo_andamento TEXT
                )
            ''')

            try:
                cursor.execute("ALTER TABLE processos ADD COLUMN ultimo_andamento TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historico_contexto (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pid TEXT,
                    data_hora TEXT,
                    texto TEXT,
                    FOREIGN KEY (pid) REFERENCES processos(pid)
                )
            ''')
            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM processos")
            if cursor.fetchone()[0] == 0:
                print("📦 Migrando processos do script para o SQLite...")
                for p in _SEED_PROCESSOS:
                    cursor.execute(
                        '''INSERT INTO processos
                           (pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo_inicial)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (p['id'], p['numero'], p['url'], p['tribunal'],
                         p['parte_label'], p['parte_nome'], p['classe'], p['resumo']),
                    )
                conn.commit()
                print("✅ Todos os processos migrados com sucesso!")

            conn.close()
        except Exception as e:
            print(f"❌ Erro crítico ao inicializar o banco: {e}")

    def get_processo(self, pid: str) -> Optional[dict]:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo_inicial, ultimo_andamento "
                "FROM processos WHERE pid = ?",
                (pid,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "id": row[0], "numero": row[1], "url": row[2], "tribunal": row[3],
                    "parte_label": row[4], "parte_nome": row[5], "classe": row[6],
                    "resumo": row[7], "ultimo_andamento": row[8],
                }
        except Exception as e:
            print(f"❌ Erro ao buscar o processo {pid}: {e}")
        return None

    def list_processos(self, tribunal: str) -> list:
        lista = []
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pid, numero, url, parte_label, parte_nome, classe, resumo_inicial, ultimo_andamento "
                "FROM processos WHERE tribunal = ?",
                (tribunal,),
            )
            for row in cursor.fetchall():
                lista.append({
                    "id": row[0], "numero": row[1], "url": row[2],
                    "parte_label": row[3], "parte_nome": row[4], "classe": row[5],
                    "resumo": row[6], "ultimo_andamento": row[7],
                })
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao buscar do {tribunal}: {e}")
        return lista

    def list_todos(self) -> list:
        lista = []
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pid, tribunal, numero, classe FROM processos ORDER BY tribunal, pid"
            )
            lista = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao listar processos: {e}")
        return lista

    def save_andamento(self, pid: str, txt: str) -> None:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE processos SET ultimo_andamento = ? WHERE pid = ?", (txt, pid)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao salvar andamento de {pid}: {e}")

    def save_resumo(self, pid: str, resumo: str) -> None:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE processos SET resumo_inicial = ? WHERE pid = ?", (resumo, pid)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao salvar resumo de {pid}: {e}")

    def pid_exists(self, pid: str) -> bool:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute("SELECT pid FROM processos WHERE pid = ?", (pid,))
            existe = cursor.fetchone() is not None
            conn.close()
            return existe
        except Exception as e:
            print(f"❌ Erro ao verificar ID {pid}: {e}")
        return False

    def add_processo(
        self,
        pid: str,
        numero: str,
        url: str,
        tribunal: str,
        parte_label: str,
        parte_nome: str,
        classe: str,
        resumo: str,
    ) -> None:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO processos
                   (pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo_inicial)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (pid, numero, url, tribunal, parte_label, parte_nome, classe, resumo),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao inserir processo {pid}: {e}")

    def delete_processo(self, pid: str) -> None:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM processos WHERE pid = ?", (pid,))
            cursor.execute("DELETE FROM historico_contexto WHERE pid = ?", (pid,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao remover processo {pid}: {e}")

    def add_contexto(self, pid: str, data_hora: str, texto: str) -> None:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO historico_contexto (pid, data_hora, texto) VALUES (?, ?, ?)",
                (pid, data_hora, texto),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ Erro ao salvar contexto de {pid}: {e}")

    def get_historico_contexto(self, pid: str) -> list:
        try:
            conn = self._conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_hora, texto FROM historico_contexto WHERE pid = ? ORDER BY id ASC",
                (pid,),
            )
            registros = cursor.fetchall()
            conn.close()
            return registros
        except Exception as e:
            print(f"❌ Erro ao ler histórico de {pid}: {e}")
        return []
