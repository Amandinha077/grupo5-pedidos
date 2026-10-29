import os
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2 import sql

from app.conexao import config_produtor, conectar_consumidor, conectar_produtor, ler_config, RAIZ
from app.validacao import COLUNAS_CONTRATO, ErroValidacao, validar_e_transformar

SISTEMA_ORIGEM = "Grupo 3 - Sistema de Produtos"
SISTEMA_DESTINO = "Grupo 5 - Sistema de Pedidos"
CHAVE_LOCK = 5003
TENTATIVAS_CONEXAO = 3
ESPERA_ENTRE_TENTATIVAS = 2
LOCK_TIMEOUT = "5s"
FUSO_BRASILIA = timezone(timedelta(hours=-3))

CAMPOS_COMPARADOS = ["nome", "descricao", "categoria_id", "preco", "unidade", "disponivel"]


class FalhaEstrutural(Exception):

    def __init__(self, tipo, descricao):
        super().__init__(descricao)
        self.tipo = tipo
        self.descricao = descricao


class RegraNegocio(Exception):

    def __init__(self, campo, descricao, valor=None):
        super().__init__(descricao)
        self.campo = campo
        self.descricao = descricao
        self.valor = valor


class FalhaSimulada(Exception):
    pass


def _mensagem(e):
    if getattr(e, "diag", None) and e.diag.message_primary:
        return e.diag.message_primary.strip()
    return " ".join(str(e).split())


def _hora(dt):
    if dt.tzinfo is not None:
        dt = dt.astimezone(FUSO_BRASILIA)
    return f"{dt:%d/%m/%Y %H:%M}"


def classificar_falha_conexao(e, cfg):
    msg = str(e).lower()
    usuario, banco, host = cfg.get("user"), cfg.get("database"), cfg.get("host")
    if "password authentication failed" in msg or "no password supplied" in msg or \
            ("role" in msg and "does not exist" in msg):
        return False, FalhaEstrutural(
            "AUTENTICACAO_FALHOU",
            f"O banco do Grupo 3 recusou o usuário '{usuario}' ou a senha informada. "
            f"Confira user e password na seção [produtor_grupo3] do config.ini.")
    if "permission denied for database" in msg:
        return False, FalhaEstrutural(
            "SEM_PERMISSAO",
            f"O usuário '{usuario}' existe, mas não tem permissão de CONNECT no banco '{banco}'. "
            f"O Grupo 3 precisa executar: GRANT CONNECT ON DATABASE {banco} TO {usuario};")
    if "database" in msg and "does not exist" in msg:
        return False, FalhaEstrutural(
            "BANCO_INEXISTENTE",
            f"O banco '{banco}' não existe no servidor {host}. Confira o nome com o Grupo 3.")
    if "no pg_hba.conf entry" in msg:
        return False, FalhaEstrutural(
            "ACESSO_BLOQUEADO",
            f"O servidor do Grupo 3 ({host}) não aceita conexões vindas desta máquina. "
            f"O Grupo 3 precisa liberar o IP no pg_hba.conf.")
    return True, FalhaEstrutural(
        "BANCO_INDISPONIVEL",
        f"O banco do Grupo 3 ({host}) está fora do ar ou inacessível pela rede "
        f"({TENTATIVAS_CONEXAO} tentativas sem resposta). Nenhum dado foi alterado no banco do Grupo 5; "
        f"o Sistema de Pedidos continua funcionando com os últimos produtos integrados.")


def explicar_falta_permissao(msg, schema, view, usuario):
    texto = msg.lower()
    if "schema" in texto:
        return (f"O usuário '{usuario}' não tem acesso ao schema '{schema}' (falta USAGE). "
                f"O Grupo 3 precisa executar: GRANT USAGE ON SCHEMA {schema} TO {usuario};")
    return (f"O usuário '{usuario}' não tem permissão de leitura na view {schema}.{view} (falta SELECT). "
            f"O Grupo 3 precisa executar: GRANT SELECT ON {schema}.{view} TO {usuario};")


class Integrador:
    def __init__(self, saida=print, falhar_apos=None):
        self.saida = saida
        self.falhar_apos = falhar_apos
        self.schema, self.view = config_produtor()
        self.cons = None
        self.integracao_id = None
        self.stats = Counter()
        self.erros = []
        self.atualizacoes = []
        self.reprocessados = []
        self.alteracoes_confirmadas = 0
        self.transacao = []
        self.esperas = []

    def _estrutura(self):
        return f"{self.schema}.{self.view}" if self.schema else f"(schema automático).{self.view}"

    def _iniciar_execucao(self):
        with self.cons.cursor() as cur:
            cur.execute(
                """INSERT INTO controle.integracao (sistema_origem, sistema_destino, estrutura_origem)
                   VALUES (%s, %s, %s) RETURNING integracao_id""",
                (SISTEMA_ORIGEM, SISTEMA_DESTINO, self._estrutura()),
            )
            self.integracao_id = cur.fetchone()[0]
        self.cons.commit()

    def _registrar_erro(self, registro, campo, tipo, descricao, valor=None, gravidade="ERRO"):
        self.erros.append((registro, campo, tipo, descricao, gravidade))
        with self.cons.cursor() as cur:
            cur.execute(
                """INSERT INTO controle.erro_integracao
                       (integracao_id, registro_origem, campo, tipo_erro, descricao, valor_recebido, gravidade)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (self.integracao_id, None if registro is None else str(registro),
                 campo, tipo, descricao, valor, gravidade),
            )
        self.cons.commit()

    def _finalizar_execucao(self, status, mensagem=None):
        s = self.stats
        with self.cons.cursor() as cur:
            cur.execute(
                """UPDATE controle.integracao
                      SET data_fim = now(), total_registros = %s, processados = %s, inseridos = %s,
                          atualizados = %s, sem_alteracao = %s, rejeitados = %s, inativados = %s,
                          status = %s, mensagem = %s, estrutura_origem = %s
                    WHERE integracao_id = %s""",
                (s["consultados"], s["inseridos"] + s["atualizados"] + s["sem_alteracao"],
                 s["inseridos"], s["atualizados"], s["sem_alteracao"], s["rejeitados"],
                 s["inativados"], status, mensagem, self._estrutura(), self.integracao_id),
            )
        self.cons.commit()

    def _conectar_produtor(self):
        cfg = ler_config()["produtor_grupo3"]
        for tentativa in range(1, TENTATIVAS_CONEXAO + 1):
            try:
                return conectar_produtor()
            except psycopg2.OperationalError as e:
                temporaria, falha = classificar_falha_conexao(e, cfg)
                if not temporaria:
                    raise falha
                if tentativa < TENTATIVAS_CONEXAO:
                    self.saida(f"[AVISO] Tentativa {tentativa}/{TENTATIVAS_CONEXAO}: banco do Grupo 3 indisponível. "
                               f"Nova tentativa em {ESPERA_ENTRE_TENTATIVAS}s...")
                    time.sleep(ESPERA_ENTRE_TENTATIVAS)
                else:
                    raise falha

    def _consultar_produtor(self):
        prod = self._conectar_produtor()
        usuario = ler_config()["produtor_grupo3"].get("user")
        try:
            with prod.cursor() as cur:
                if not self.schema:
                    cur.execute(
                        """SELECT n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE c.relname = %s AND c.relkind IN ('v', 'm', 'r')
                              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                            ORDER BY (n.nspname = 'public') DESC, n.nspname""",
                        (self.view,))
                    achados = [r[0] for r in cur.fetchall()]
                    if not achados:
                        raise FalhaEstrutural("ESTRUTURA_INEXISTENTE",
                                              f"A view {self.view} não existe em nenhum schema do banco do Grupo 3")
                    self.schema = achados[0]
                    self.saida(f"Estrutura encontrada: {self.schema}.{self.view}")

                consulta = sql.SQL("SELECT * FROM {}.{} ORDER BY 1").format(
                    sql.Identifier(self.schema), sql.Identifier(self.view))
                cur.execute(consulta)
                colunas = [d.name for d in cur.description]

                faltando = [c for c in COLUNAS_CONTRATO if c not in colunas]
                if faltando:
                    raise FalhaEstrutural(
                        "ESTRUTURA_ALTERADA",
                        f"A estrutura {self.schema}.{self.view} não possui as colunas do contrato: "
                        f"{', '.join(faltando)}. Colunas recebidas: {', '.join(colunas)}")
                extras = [c for c in colunas if c not in COLUNAS_CONTRATO]

                registros = [dict(zip(colunas, linha)) for linha in cur.fetchall()]
            prod.commit()
            return registros, extras
        except psycopg2.errors.UndefinedTable:
            raise FalhaEstrutural("ESTRUTURA_INEXISTENTE", f"A view {self._estrutura()} não existe no banco do Grupo 3")
        except psycopg2.errors.InsufficientPrivilege as e:
            raise FalhaEstrutural("SEM_PERMISSAO",
                                  explicar_falta_permissao(_mensagem(e), self.schema, self.view, usuario))
        except psycopg2.OperationalError as e:
            raise FalhaEstrutural("BANCO_INDISPONIVEL",
                                  f"A conexão com o banco do Grupo 3 caiu durante a consulta ({_mensagem(e)}). "
                                  f"Nada foi gravado; a integração deve ser executada novamente.")
        finally:
            prod.close()

    def _gravar_registro(self, d):
        with self.cons.cursor() as cur:
            cur.execute("SELECT categoria_id FROM pedidos.categoria WHERE lower(nome) = lower(%s)",
                        (d["nome_categoria"],))
            linha = cur.fetchone()
            if linha is None:
                cur.execute("INSERT INTO pedidos.categoria (nome) VALUES (%s) RETURNING categoria_id",
                            (d["nome_categoria"],))
                linha = cur.fetchone()
            d["categoria_id"] = linha[0]

            cur.execute(
                """SELECT p.produto_id, p.nome, p.descricao, p.categoria_id, p.preco, p.unidade, p.disponivel,
                          c.nome, p.data_atualizacao_origem
                     FROM pedidos.produto p LEFT JOIN pedidos.categoria c ON c.categoria_id = p.categoria_id
                    WHERE p.id_produto_origem = %s FOR UPDATE OF p""",
                (d["id_produto_origem"],),
            )
            atual = cur.fetchone()
            mudancas = []

            if atual is None:
                cur.execute(
                    """INSERT INTO pedidos.produto
                           (id_produto_origem, nome, descricao, categoria_id, preco, unidade,
                            disponivel, data_atualizacao_origem, data_ultima_integracao)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())""",
                    (d["id_produto_origem"], d["nome"], d["descricao"], d["categoria_id"], d["preco"],
                     d["unidade"], d["disponivel"], d["data_atualizacao_origem"]),
                )
                resultado = "inseridos"
            else:
                antes = dict(zip(CAMPOS_COMPARADOS, atual[1:7]))
                mudancas = [(c, antes[c], d[c]) for c in CAMPOS_COMPARADOS if antes[c] != d[c]]
                mudancas = [("categoria", atual[7], d["nome_categoria"]) if c == "categoria_id" else (c, a, b)
                            for c, a, b in mudancas]
                data_gravada = atual[8]
                if mudancas and data_gravada and d["data_atualizacao_origem"] < data_gravada:
                    raise RegraNegocio(
                        "atualizado_em",
                        f"O produto chegou com dados diferentes, mas com atualizado_em "
                        f"({_hora(d['data_atualizacao_origem'])}) ANTERIOR à versão já integrada "
                        f"({_hora(data_gravada)}). Uma versão antiga não pode sobrescrever uma mais nova.",
                        d["data_atualizacao_origem"])
                if mudancas:
                    cur.execute(
                        """UPDATE pedidos.produto
                              SET nome = %s, descricao = %s, categoria_id = %s, preco = %s, unidade = %s,
                                  disponivel = %s, data_atualizacao_origem = %s, data_ultima_integracao = now()
                            WHERE produto_id = %s""",
                        (d["nome"], d["descricao"], d["categoria_id"], d["preco"], d["unidade"],
                         d["disponivel"], d["data_atualizacao_origem"], atual[0]),
                    )
                    resultado = "atualizados"
                else:
                    cur.execute("UPDATE pedidos.produto SET data_ultima_integracao = now() WHERE produto_id = %s",
                                (atual[0],))
                    resultado = "sem_alteracao"

            cur.execute(
                """UPDATE controle.erro_integracao
                      SET resolvido = TRUE, data_resolucao = now(), resolvido_na_integracao = %s
                    WHERE registro_origem = %s AND NOT resolvido AND gravidade = 'ERRO'
                      AND integracao_id <> %s""",
                (self.integracao_id, str(d["id_produto_origem"]), self.integracao_id),
            )
            reprocessado = cur.rowcount > 0
        return resultado, mudancas, reprocessado

    def _tratar_inexistentes(self, codigos_origem):
        with self.cons.cursor() as cur:
            cur.execute(
                """UPDATE pedidos.produto SET disponivel = FALSE, data_ultima_integracao = now()
                    WHERE id_produto_origem IS NOT NULL AND disponivel
                      AND NOT (id_produto_origem = ANY(%s))
                RETURNING id_produto_origem""",
                (list(codigos_origem),),
            )
            removidos = [r[0] for r in cur.fetchall()]
        self.cons.commit()
        for cod in removidos:
            self.stats["inativados"] += 1
            self._registrar_erro(cod, "id_produto", "REGISTRO_REMOVIDO_ORIGEM",
                                 f"Produto {cod} não existe mais no banco de origem; marcado como indisponível "
                                 f"(não foi excluído porque pode estar em pedidos)", gravidade="AVISO")

    def _processar_registro(self, reg, ocorrencias):
        codigo = reg.get("id_produto")
        erros, dados = validar_e_transformar(reg)

        if codigo is not None and ocorrencias[codigo] > 1:
            erros.insert(0, ErroValidacao("id_produto", "REGISTRO_DUPLICADO",
                                          f"Código {codigo} aparece {ocorrencias[codigo]} vezes na origem; "
                                          f"todas as ocorrências foram rejeitadas", codigo))
        if erros:
            self.stats["rejeitados"] += 1
            for e in erros:
                self._registrar_erro(codigo, e.campo, e.tipo, e.descricao, e.valor)
            return

        inicio = time.monotonic()
        try:
            resultado, mudancas, reprocessado = self._gravar_registro(dados)
            espera = time.monotonic() - inicio
            if espera >= 1:
                self.esperas.append(f"Produto {codigo}: esperou {espera:.1f}s outra transação liberar o registro "
                                    f"(lock) e depois gravou normalmente")
            if self.falhar_apos is not None and resultado != "sem_alteracao" \
                    and self.alteracoes_confirmadas >= self.falhar_apos:
                raise FalhaSimulada(codigo)
            self.cons.commit()
        except FalhaSimulada:
            self.cons.rollback()
            raise
        except RegraNegocio as r:
            self.cons.rollback()
            self.stats["rejeitados"] += 1
            self._registrar_erro(codigo, r.campo, "DADO_INCONSISTENTE", r.descricao, r.valor)
            return
        except (psycopg2.errors.LockNotAvailable, psycopg2.errors.DeadlockDetected):
            self.cons.rollback()
            self.stats["rejeitados"] += 1
            self._registrar_erro(codigo, None, "REGISTRO_BLOQUEADO",
                                 f"O produto {codigo} estava bloqueado por outra transação (outro processo "
                                 f"alterando o mesmo registro). A integração esperou {LOCK_TIMEOUT}, desfez a "
                                 f"gravação deste registro (ROLLBACK) e ele será reprocessado na próxima execução.")
            return
        except psycopg2.errors.InsufficientPrivilege as e:
            self.cons.rollback()
            usuario = ler_config()["consumidor_grupo5"].get("user")
            raise FalhaEstrutural(
                "SEM_PERMISSAO_CONSUMIDOR",
                f"O usuário '{usuario}' não tem permissão para gravar no banco do Grupo 5 ({_mensagem(e)}). "
                f"Correção: GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pedidos TO {usuario};")
        except psycopg2.Error as e:
            self.cons.rollback()
            self.stats["rejeitados"] += 1
            self._registrar_erro(codigo, None, "ERRO_BANCO_CONSUMIDOR", _mensagem(e))
            return

        self.stats[resultado] += 1
        if resultado != "sem_alteracao":
            self.alteracoes_confirmadas += 1
            self.transacao.append(f"COMMIT   produto {codigo} ({resultado[:-1]})")
        if mudancas:
            self.atualizacoes.append((f"Produto {codigo}", mudancas))
        if reprocessado:
            self.reprocessados.append(codigo)

    def executar(self):
        try:
            self.cons = conectar_consumidor()
        except psycopg2.OperationalError as e:
            self.saida(f"[FALHA] Não foi possível conectar no banco do Grupo 5: {_mensagem(e)}")
            return None

        try:
            with self.cons.cursor() as cur:
                cur.execute("SELECT pg_try_advisory_lock(%s)", (CHAVE_LOCK,))
                if not cur.fetchone()[0]:
                    self.saida("[AVISO] Já existe uma integração em andamento (lock da integração ocupado). "
                               "Esta execução foi recusada para não processar os mesmos registros duas vezes.")
                    self.cons.commit()
                    return None
                cur.execute(f"SET lock_timeout = '{LOCK_TIMEOUT}'")
            self.cons.commit()

            self._iniciar_execucao()
            self.saida(f"Integração #{self.integracao_id} iniciada: {SISTEMA_ORIGEM} -> {SISTEMA_DESTINO}")

            try:
                registros, extras = self._consultar_produtor()
            except FalhaEstrutural as f:
                self._registrar_erro(None, None, f.tipo, f.descricao, gravidade="FATAL")
                self._finalizar_execucao("FALHA", f.descricao)
                return self._gerar_relatorio("FALHA")

            for col in extras:
                self._registrar_erro(None, col, "COLUNA_NAO_PREVISTA",
                                     f"Coluna '{col}' não está no contrato e foi ignorada", gravidade="AVISO")

            self.stats["consultados"] = len(registros)
            ocorrencias = Counter(r.get("id_produto") for r in registros)
            codigos_origem = {c for c in ocorrencias if isinstance(c, int)}

            for posicao, reg in enumerate(registros):
                try:
                    self._processar_registro(reg, ocorrencias)
                except FalhaSimulada as f:
                    codigo = f.args[0]
                    restantes = [str(r.get("id_produto")) for r in registros[posicao + 1:]]
                    self.transacao.append(f"ROLLBACK produto {codigo} (falha no meio da transação)")
                    if restantes:
                        self.transacao.append(f"NÃO PROCESSADOS: {', '.join(restantes)}")
                    descricao = (f"Falha simulada durante a gravação do produto {codigo}. "
                                 f"{self.alteracoes_confirmadas} alteração(ões) já confirmada(s) com COMMIT "
                                 f"continuam gravadas; o produto {codigo} foi desfeito com ROLLBACK; "
                                 f"{len(restantes)} registro(s) não foram processados. "
                                 f"Basta executar a integração de novo para concluir.")
                    self._registrar_erro(codigo, None, "TRANSACAO_INTERROMPIDA", descricao, gravidade="FATAL")
                    self._finalizar_execucao("FALHA", descricao)
                    return self._gerar_relatorio("FALHA")
                except FalhaEstrutural as f:
                    self._registrar_erro(None, None, f.tipo, f.descricao, gravidade="FATAL")
                    self._finalizar_execucao("FALHA", f.descricao)
                    return self._gerar_relatorio("FALHA")

            self._tratar_inexistentes(codigos_origem)

            with self.cons.cursor() as cur:
                cur.execute(
                    """UPDATE controle.erro_integracao
                          SET resolvido = TRUE, data_resolucao = now(), resolvido_na_integracao = %s
                        WHERE gravidade = 'FATAL' AND NOT resolvido""", (self.integracao_id,))
            self.cons.commit()

            status = "CONCLUIDA_COM_ERROS" if self.stats["rejeitados"] else "CONCLUIDA"
            self._finalizar_execucao(status)
            return self._gerar_relatorio(status)

        except psycopg2.errors.InsufficientPrivilege as e:
            self.cons.rollback()
            usuario = ler_config()["consumidor_grupo5"].get("user")
            self.saida(f"[FALHA] O usuário '{usuario}' não tem permissão no banco do Grupo 5 para registrar a "
                       f"integração ({_mensagem(e)}). Correção: GRANT SELECT, INSERT, UPDATE ON ALL TABLES "
                       f"IN SCHEMA controle TO {usuario};")
            return None
        except psycopg2.Error as e:
            try:
                self.cons.rollback()
                if self.integracao_id:
                    self._finalizar_execucao("FALHA", f"Erro inesperado: {_mensagem(e)}")
            except psycopg2.Error:
                pass
            self.saida(f"[FALHA] Erro inesperado durante a integração: {_mensagem(e)}")
            return None
        finally:
            try:
                with self.cons.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (CHAVE_LOCK,))
                self.cons.commit()
            except psycopg2.Error:
                pass
            self.cons.close()

    def _gerar_relatorio(self, status):
        s = self.stats
        linha = "=" * 52
        sep = "-" * 52
        txt = [
            linha,
            "PROCESSAMENTO DA INTEGRAÇÃO",
            linha,
            f"Integração nº:     {self.integracao_id}",
            f"Data/hora:         {datetime.now():%d/%m/%Y %H:%M:%S}",
            f"Origem:            {SISTEMA_ORIGEM}",
            f"Estrutura:         {self._estrutura()}",
            f"Destino:           {SISTEMA_DESTINO}",
            sep,
            f"Total consultado:  {s['consultados']}",
            f"Processados:       {s['inseridos'] + s['atualizados'] + s['sem_alteracao']}",
            f"   Inseridos:      {s['inseridos']}",
            f"   Atualizados:    {s['atualizados']}",
            f"   Sem alteração:  {s['sem_alteracao']}",
            f"Rejeitados:        {s['rejeitados']}",
            f"Inativados:        {s['inativados']}  (removidos da origem)",
        ]

        if self.atualizacoes:
            txt += [sep, "REGISTROS ATUALIZADOS (antes -> depois)", sep]
            for rotulo, mud in self.atualizacoes:
                txt.append(f"{rotulo}:")
                for campo, antes, depois in mud:
                    txt.append(f"   {campo}: {antes} -> {depois}")

        if self.reprocessados:
            txt += [sep, "REPROCESSADOS (tinham erro e agora foram integrados)", sep,
                    "Produtos: " + ", ".join(str(c) for c in self.reprocessados)]

        if self.esperas:
            txt += [sep, "ESPERAS POR LOCK (concorrência)", sep] + self.esperas

        if self.falhar_apos is not None and self.transacao:
            txt += [sep, "TRANSAÇÕES (uma por registro)", sep] + self.transacao

        txt += [sep, "ERROS E OCORRÊNCIAS", sep]
        if not self.erros:
            txt.append("Nenhum erro encontrado.")
        for reg, campo, tipo, desc, grav in self.erros:
            alvo = f"Registro {reg}" if reg is not None else "Integração"
            campo_txt = f" [{campo}]" if campo else ""
            txt.append(f"{alvo}{campo_txt} - {grav} {tipo}:")
            txt.append(f"   {desc}")

        status_txt = {"CONCLUIDA": "CONCLUÍDA", "CONCLUIDA_COM_ERROS": "CONCLUÍDA COM ERROS",
                      "FALHA": "FALHA - INTEGRAÇÃO INTERROMPIDA"}[status]
        txt += [sep, f"STATUS: {status_txt}", linha]
        relatorio = "\n".join(txt)

        pasta = ler_config().get("integracao", "pasta_relatorios", fallback="relatorios")
        pasta = pasta if os.path.isabs(pasta) else os.path.join(RAIZ, pasta)
        os.makedirs(pasta, exist_ok=True)
        arquivo = os.path.join(pasta, f"integracao_{self.integracao_id:04d}_{datetime.now():%Y%m%d_%H%M%S}.txt")
        with open(arquivo, "w", encoding="utf-8") as f:
            f.write(relatorio + "\n")

        self.saida(relatorio)
        self.saida(f"Relatório salvo em: {arquivo}")
        return relatorio


def executar_integracao(saida=print, falhar_apos=None):
    return Integrador(saida, falhar_apos).executar()


if __name__ == "__main__":
    executar_integracao()
