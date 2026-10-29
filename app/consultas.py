from app.crud import _imprimir


def _mostrar(conn, consulta, params=None):
    with conn.cursor() as cur:
        cur.execute(consulta, params)
        linhas = cur.fetchall()
        colunas = [d.name for d in cur.description]
    conn.commit()
    _imprimir(linhas, colunas)


def historico_integracoes(conn):
    print("\n--- Histórico de integrações (Grupo 3 -> Grupo 5) ---")
    _mostrar(conn, """
        SELECT integracao_id AS id, to_char(data_inicio, 'DD/MM/YYYY HH24:MI:SS') AS inicio,
               to_char(data_fim, 'HH24:MI:SS') AS fim, total_registros AS consultados,
               processados, inseridos, atualizados, rejeitados, inativados, status
          FROM controle.integracao ORDER BY integracao_id DESC LIMIT 20""")


def erros_integracao(conn, somente_pendentes=True):
    titulo = "pendentes" if somente_pendentes else "(últimos 50)"
    print(f"\n--- Erros de integração {titulo} ---")
    filtro = "WHERE NOT resolvido AND gravidade <> 'AVISO'" if somente_pendentes else ""
    _mostrar(conn, f"""
        SELECT erro_id, integracao_id AS exec, registro_origem AS registro, campo, tipo_erro,
               gravidade, descricao, CASE WHEN resolvido THEN 'sim' ELSE 'não' END AS resolvido
          FROM controle.erro_integracao {filtro}
         ORDER BY erro_id DESC LIMIT 50""")


def visao_grupo7(conn):
    print("\n--- O que o Grupo 7 (Entregas) enxerga: api_entregas.vw_integracao_pedidos ---")
    _mostrar(conn, """
        SELECT codigo_pedido, to_char(data_pedido, 'DD/MM/YYYY') AS data, status_pedido,
               nome_cliente, cidade, uf, quantidade_itens AS itens, valor_total
          FROM api_entregas.vw_integracao_pedidos ORDER BY codigo_pedido""")
    print("\n--- api_entregas.vw_integracao_itens_pedido ---")
    _mostrar(conn, """
        SELECT codigo_item, codigo_pedido, codigo_produto, nome_produto, quantidade, unidade, subtotal
          FROM api_entregas.vw_integracao_itens_pedido ORDER BY codigo_pedido, codigo_item""")
