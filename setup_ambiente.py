import os
import re
import sys

import psycopg2

from app.conexao import RAIZ, conectar_admin
from app.integracao_produtos import executar_integracao


def ler_sql(caminho):
    with open(os.path.join(RAIZ, caminho), encoding="utf-8") as f:
        return f.read()


def executar_por_comando(conn, caminho):
    texto = re.sub(r"--[^\n]*", "", ler_sql(caminho))
    with conn.cursor() as cur:
        for comando in (c.strip() for c in texto.split(";")):
            if comando:
                cur.execute(comando)
    print(f"  ok  {caminho}")


def executar_arquivo(database, caminho):
    conn = conectar_admin(database)
    try:
        with conn.cursor() as cur:
            cur.execute(ler_sql(caminho))
        print(f"  ok  {caminho}")
    finally:
        conn.close()


def main():
    simulacao = "--sem-simulacao" not in sys.argv

    try:
        admin = conectar_admin("postgres")
    except psycopg2.OperationalError as e:
        print(f"Não foi possível conectar como administrador. Confira a seção [admin] do config.ini.\n{e}")
        sys.exit(1)

    try:
        if "--resetar" in sys.argv:
            print("Removendo banco e usuários do Grupo 5...")
            executar_por_comando(admin, "sql/99_remover_tudo.sql")
            if simulacao:
                print("Removendo o Grupo 3 SIMULADO...")
                executar_por_comando(admin, "simulacao_grupo3/99_remover_grupo3_simulado.sql")

        print("\n[1/5] Banco e usuários do Grupo 5")
        executar_por_comando(admin, "sql/00_criar_bancos_usuarios.sql")
        print("[2/5] Estrutura do Grupo 5 e views para o Grupo 7")
        executar_arquivo("grupo5_db", "sql/01_schema_grupo5.sql")
        executar_arquivo("grupo5_db", "sql/02_estrutura_integracao_grupo7.sql")
        executar_arquivo("grupo5_db", "sql/03_dados_teste_clientes.sql")

        if simulacao:
            print("[3/5] Grupo 3 simulado (para teste local)")
            executar_por_comando(admin, "simulacao_grupo3/10_grupo3_banco_usuarios.sql")
            executar_arquivo("grupo3_db", "simulacao_grupo3/11_grupo3_estrutura.sql")
        else:
            print("[3/5] Simulação do Grupo 3 ignorada (--sem-simulacao)")
    except psycopg2.errors.DuplicateObject as e:
        print(f"\nJá existe: {e}".strip())
        print("Rode com --resetar para recriar o Grupo 5.")
        print("Se o banco REAL do Grupo 3 está neste mesmo PostgreSQL, use também --sem-simulacao.")
        sys.exit(1)
    except psycopg2.errors.DuplicateDatabase as e:
        print(f"\nJá existe: {e}".strip())
        print("Rode com --resetar para recriar o Grupo 5.")
        print("Se o banco REAL do Grupo 3 está neste mesmo PostgreSQL, use também --sem-simulacao.")
        sys.exit(1)
    finally:
        admin.close()

    print("\n[4/5] Primeira integração com o Grupo 3")
    executar_integracao()

    print("\n[5/5] Pedidos de teste")
    try:
        executar_arquivo("grupo5_db", "sql/04_dados_teste_pedidos.sql")
    except psycopg2.Error as e:
        print(f"  Pedidos de teste não criados: {e}")

    print("\nAmbiente pronto. Rode: python main.py")


if __name__ == "__main__":
    main()
