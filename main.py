import sys

import psycopg2

from app import consultas, crud, demonstracoes
from app.conexao import conectar_consumidor
from app.integracao_produtos import executar_integracao

MENU = """
==============================================
  GRUPO 5 - SISTEMA DE PEDIDOS
==============================================
  CADASTROS (CRUD)
   1 Clientes
   2 Endereços
   3 Pedidos
   4 Itens de pedido
   5 Produtos
   6 Categorias
  INTEGRAÇÃO
   7 Executar integração com o Grupo 3 (Produtos)
   8 Histórico de integrações
   9 Erros pendentes
  10 Todos os erros/ocorrências
  11 Ver o que publicamos para o Grupo 7 (Entregas)
  DEMONSTRAÇÕES
  12 Falha no meio da transação (COMMIT/ROLLBACK)
  13 Concorrência (dois processos no mesmo registro)
   0 Sair
=============================================="""

TABELA_POR_OPCAO = {"1": "cliente", "2": "endereco", "3": "pedido",
                    "4": "item_pedido", "5": "produto", "6": "categoria"}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "integrar":
        falhar_apos = None
        if "--falhar-apos" in sys.argv:
            falhar_apos = int(sys.argv[sys.argv.index("--falhar-apos") + 1])
        executar_integracao(falhar_apos=falhar_apos)
        return

    try:
        conn = conectar_consumidor()
    except psycopg2.OperationalError as e:
        print(f"Não foi possível conectar ao banco do Grupo 5: {e}")
        print("Confira o config.ini e se o setup_ambiente.py já foi executado.")
        return

    try:
        while True:
            print(MENU)
            op = input("Opção: ").strip()
            try:
                if op in TABELA_POR_OPCAO:
                    crud.menu_crud(conn, TABELA_POR_OPCAO[op])
                elif op == "7":
                    executar_integracao()
                elif op == "8":
                    consultas.historico_integracoes(conn)
                elif op == "9":
                    consultas.erros_integracao(conn, somente_pendentes=True)
                elif op == "10":
                    consultas.erros_integracao(conn, somente_pendentes=False)
                elif op == "11":
                    consultas.visao_grupo7(conn)
                elif op == "12":
                    demonstracoes.executar_demo("falha")
                elif op == "13":
                    demonstracoes.executar_demo("concorrencia")
                elif op == "0":
                    break
            except psycopg2.Error as e:
                conn.rollback()
                print(f"Erro no banco: {e}")
            if op not in TABELA_POR_OPCAO and op != "0":
                input("\nENTER para continuar...")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
