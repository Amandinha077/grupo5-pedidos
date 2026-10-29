import threading
import time

import psycopg2

from app.conexao import conectar_consumidor
from app.integracao_produtos import LOCK_TIMEOUT, executar_integracao


def _ler_inteiro(pergunta, padrao):
    texto = input(f"{pergunta} [{padrao}]: ").strip()
    try:
        return int(texto) if texto else padrao
    except ValueError:
        return padrao


def demo_falha_transacao():
    print("\n--- 15.19 PROBLEMA DE TRANSAÇÃO ---")
    print("Cada registro é gravado na sua própria transação. A integração vai confirmar (COMMIT)")
    print("algumas alterações e, no meio da gravação da seguinte, o processo 'cai'.")
    print("O registro que estava no meio é desfeito (ROLLBACK) e os demais ficam para a próxima execução.\n")
    n = _ler_inteiro("Quantas alterações confirmar antes da falha", 2)
    executar_integracao(falhar_apos=n)
    print("\nExecute a opção 7 para concluir: os registros pendentes serão integrados sem duplicar nada.")


def _primeiro_produto():
    conn = conectar_consumidor()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT produto_id, id_produto_origem, nome FROM pedidos.produto
                            WHERE id_produto_origem IS NOT NULL ORDER BY id_produto_origem LIMIT 1""")
            return cur.fetchone()
    finally:
        conn.close()


def demo_concorrencia():
    print("\n--- 15.20 CONCORRÊNCIA ---")
    produto = _primeiro_produto()
    if not produto:
        print("Nenhum produto integrado ainda. Execute a opção 7 primeiro.")
        return
    produto_id, codigo, nome = produto
    segundos = _ler_inteiro(f"Por quantos segundos o processo A segura o produto {codigo} "
                            f"(maior que {LOCK_TIMEOUT} = integração desiste; menor = integração espera e grava)", 8)

    bloqueado = threading.Event()

    def processo_a():
        conn = conectar_consumidor()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE pedidos.produto SET nome = nome WHERE produto_id = %s", (produto_id,))
            print(f"[A] Processo A abriu uma transação e bloqueou o produto {codigo} ({nome}) "
                  f"por {segundos}s (lock de linha, como um usuário editando o cadastro).")
            bloqueado.set()
            time.sleep(segundos)
            conn.rollback()
            print(f"[A] Processo A terminou a transação (ROLLBACK) e liberou o produto {codigo}.")
        finally:
            conn.close()

    def processo_b():
        print("[B] Integração B iniciada. Ao chegar no produto bloqueado ela precisa esperar o lock.")
        executar_integracao(saida=lambda m: print("[B] " + m.replace("\n", "\n[B] ")))

    def processo_c():
        print("[C] Integração C tentou iniciar ao mesmo tempo que a B.")
        executar_integracao(saida=lambda m: print("[C] " + m))

    a = threading.Thread(target=processo_a)
    a.start()
    bloqueado.wait(10)
    b = threading.Thread(target=processo_b)
    b.start()
    time.sleep(1)
    c = threading.Thread(target=processo_c)
    c.start()
    for t in (a, b, c):
        t.join()

    print("\nResumo:")
    print(f" - O lock de linha (SELECT ... FOR UPDATE) fez a integração B esperar o processo A. Ela espera no máximo "
          f"{LOCK_TIMEOUT} (lock_timeout); se passar disso, desfaz só aquele registro (ROLLBACK) e reprocessa depois.")
    print(" - O advisory lock da integração recusou a integração C: duas integrações não rodam ao mesmo tempo.")
    print(" - A leitura no Grupo 3 usa REPEATABLE READ: a integração enxerga uma foto consistente da view.")


def executar_demo(opcao):
    try:
        {"falha": demo_falha_transacao, "concorrencia": demo_concorrencia}[opcao]()
    except psycopg2.Error as e:
        print(f"Erro no banco durante a demonstração: {e}")
