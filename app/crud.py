from decimal import Decimal, InvalidOperation

import psycopg2
from psycopg2 import sql

TABELAS = {
    "categoria": {
        "titulo": "Categorias",
        "pk": "categoria_id",
        "campos": {
            "nome": ("Nome", "texto", True),
        },
        "lista": ["categoria_id", "nome"],
    },
    "produto": {
        "titulo": "Produtos",
        "pk": "produto_id",
        "campos": {
            "nome": ("Nome", "texto", True),
            "descricao": ("Descrição", "texto", False),
            "categoria_id": ("ID da categoria", "inteiro", False),
            "preco": ("Preço", "decimal", True),
            "unidade": ("Unidade de medida (UN, KG, L...)", "texto", True),
            "disponivel": ("Disponível (s/n)", "booleano", True),
            "id_produto_origem": ("Código no Grupo 3 (vazio = produto local)", "inteiro", False),
        },
        "lista": ["produto_id", "id_produto_origem", "nome", "preco", "unidade", "disponivel"],
        "aviso": "Atenção: produtos vindos do Grupo 3 são sobrescritos na próxima integração.",
    },
    "cliente": {
        "titulo": "Clientes",
        "pk": "cliente_id",
        "campos": {
            "nome": ("Nome", "texto", True),
            "cpf": ("CPF (só números)", "texto", True),
            "email": ("E-mail", "texto", False),
            "telefone": ("Telefone", "texto", False),
        },
        "lista": ["cliente_id", "nome", "cpf", "email", "telefone"],
    },
    "endereco": {
        "titulo": "Endereços",
        "pk": "endereco_id",
        "campos": {
            "cliente_id": ("ID do cliente", "inteiro", True),
            "logradouro": ("Logradouro", "texto", True),
            "numero": ("Número", "texto", True),
            "complemento": ("Complemento", "texto", False),
            "bairro": ("Bairro", "texto", True),
            "cidade": ("Cidade", "texto", True),
            "uf": ("UF", "texto", True),
            "cep": ("CEP (só números)", "texto", True),
        },
        "lista": ["endereco_id", "cliente_id", "logradouro", "numero", "bairro", "cidade", "uf"],
    },
    "pedido": {
        "titulo": "Pedidos",
        "pk": "pedido_id",
        "campos": {
            "cliente_id": ("ID do cliente", "inteiro", True),
            "endereco_id": ("ID do endereço de entrega", "inteiro", True),
            "status": ("Status (ABERTO, CONFIRMADO, CANCELADO)", "texto", True),
            "observacao": ("Observação", "texto", False),
        },
        "lista": ["pedido_id", "cliente_id", "endereco_id", "data_pedido", "status", "valor_total"],
        "padroes": {"status": "ABERTO"},
    },
    "item_pedido": {
        "titulo": "Itens de pedido",
        "pk": "item_id",
        "campos": {
            "pedido_id": ("ID do pedido", "inteiro", True),
            "produto_id": ("ID do produto", "inteiro", True),
            "quantidade": ("Quantidade", "decimal", True),
        },
        "lista": ["item_id", "pedido_id", "produto_id", "quantidade", "preco_unitario", "subtotal"],
        "aviso": "O preço unitário é copiado do produto automaticamente.",
    },
}


def _converter(valor, tipo):
    if valor == "":
        return None
    if tipo == "inteiro":
        return int(valor)
    if tipo == "decimal":
        return Decimal(valor.replace(",", "."))
    if tipo == "booleano":
        v = valor.strip().lower()
        if v in ("s", "sim", "t", "true", "1"):
            return True
        if v in ("n", "nao", "não", "f", "false", "0"):
            return False
        raise ValueError("use s ou n")
    return valor.strip()


def _ler_campos(meta, atual=None):
    valores = {}
    padroes = meta.get("padroes", {})
    for campo, (rotulo, tipo, obrig) in meta["campos"].items():
        if atual is not None:
            sugestao = atual.get(campo)
        else:
            sugestao = padroes.get(campo)
        while True:
            dica = f" [{sugestao}]" if sugestao is not None else ""
            marca = "*" if obrig else ""
            entrada = input(f"  {rotulo}{marca}{dica}: ").strip()
            if entrada == "" and sugestao is not None:
                valores[campo] = sugestao
                break
            try:
                v = _converter(entrada, tipo)
            except (ValueError, InvalidOperation) as e:
                print(f"    Valor inválido ({e}). Tente de novo.")
                continue
            if v is None and obrig:
                print("    Campo obrigatório.")
                continue
            valores[campo] = v
            break
    return valores


def _imprimir(linhas, colunas):
    if not linhas:
        print("  (nenhum registro)")
        return
    larg = {c: max(len(c), *(len("" if r[i] is None else str(r[i])) for r in linhas)) for i, c in enumerate(colunas)}
    larg = {c: min(w, 35) for c, w in larg.items()}
    print("  " + " | ".join(c.ljust(larg[c]) for c in colunas))
    print("  " + "-+-".join("-" * larg[c] for c in colunas))
    for r in linhas:
        print("  " + " | ".join(("" if v is None else str(v))[:35].ljust(larg[c]) for c, v in zip(colunas, r)))


def _erro_amigavel(e):
    msg = (e.diag.message_primary if getattr(e, "diag", None) and e.diag.message_primary else str(e)).strip()
    if isinstance(e, psycopg2.errors.ForeignKeyViolation):
        return f"Violação de chave estrangeira: {msg}"
    if isinstance(e, psycopg2.errors.UniqueViolation):
        return f"Registro duplicado: {msg}"
    if isinstance(e, psycopg2.errors.CheckViolation):
        return f"Valor fora da regra: {msg}"
    return msg


def listar(conn, tabela):
    meta = TABELAS[tabela]
    q = sql.SQL("SELECT {} FROM pedidos.{} ORDER BY {}").format(
        sql.SQL(", ").join(map(sql.Identifier, meta["lista"])), sql.Identifier(tabela), sql.Identifier(meta["pk"]))
    with conn.cursor() as cur:
        cur.execute(q)
        _imprimir(cur.fetchall(), meta["lista"])
    conn.commit()


def buscar(conn, tabela, pk):
    meta = TABELAS[tabela]
    q = sql.SQL("SELECT * FROM pedidos.{} WHERE {} = %s").format(sql.Identifier(tabela), sql.Identifier(meta["pk"]))
    with conn.cursor() as cur:
        cur.execute(q, (pk,))
        linha = cur.fetchone()
        cols = [d.name for d in cur.description]
    conn.commit()
    return dict(zip(cols, linha)) if linha else None


def inserir(conn, tabela):
    meta = TABELAS[tabela]
    if meta.get("aviso"):
        print("  " + meta["aviso"])
    valores = _ler_campos(meta)
    q = sql.SQL("INSERT INTO pedidos.{} ({}) VALUES ({}) RETURNING {}").format(
        sql.Identifier(tabela),
        sql.SQL(", ").join(map(sql.Identifier, valores)),
        sql.SQL(", ").join(sql.Placeholder() * len(valores)),
        sql.Identifier(meta["pk"]))
    try:
        with conn.cursor() as cur:
            cur.execute(q, list(valores.values()))
            novo = cur.fetchone()[0]
        conn.commit()
        print(f"  Registro {novo} incluído.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"  Não foi possível incluir: {_erro_amigavel(e)}")


def alterar(conn, tabela):
    meta = TABELAS[tabela]
    try:
        pk = int(input(f"  ID ({meta['pk']}): "))
    except ValueError:
        print("  ID inválido.")
        return
    atual = buscar(conn, tabela, pk)
    if not atual:
        print("  Registro não encontrado.")
        return
    if meta.get("aviso"):
        print("  " + meta["aviso"])
    print("  (ENTER mantém o valor atual)")
    valores = _ler_campos(meta, atual)
    q = sql.SQL("UPDATE pedidos.{} SET {} WHERE {} = %s").format(
        sql.Identifier(tabela),
        sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in valores),
        sql.Identifier(meta["pk"]))
    try:
        with conn.cursor() as cur:
            cur.execute(q, list(valores.values()) + [pk])
        conn.commit()
        print("  Registro alterado.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"  Não foi possível alterar: {_erro_amigavel(e)}")


def excluir(conn, tabela):
    meta = TABELAS[tabela]
    try:
        pk = int(input(f"  ID ({meta['pk']}) a excluir: "))
    except ValueError:
        print("  ID inválido.")
        return
    if input(f"  Confirma a exclusão do registro {pk}? (s/n): ").strip().lower() != "s":
        return
    q = sql.SQL("DELETE FROM pedidos.{} WHERE {} = %s").format(sql.Identifier(tabela), sql.Identifier(meta["pk"]))
    try:
        with conn.cursor() as cur:
            cur.execute(q, (pk,))
            n = cur.rowcount
        conn.commit()
        print("  Registro excluído." if n else "  Registro não encontrado.")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"  Não foi possível excluir: {_erro_amigavel(e)}")


def menu_crud(conn, tabela):
    meta = TABELAS[tabela]
    while True:
        print(f"\n--- {meta['titulo']} ---")
        print("1 Listar   2 Consultar por ID   3 Incluir   4 Alterar   5 Excluir   0 Voltar")
        op = input("Opção: ").strip()
        if op == "1":
            listar(conn, tabela)
        elif op == "2":
            try:
                reg = buscar(conn, tabela, int(input(f"  ID ({meta['pk']}): ")))
            except ValueError:
                print("  ID inválido.")
                continue
            if reg:
                for k, v in reg.items():
                    print(f"  {k}: {v}")
            else:
                print("  Registro não encontrado.")
        elif op == "3":
            inserir(conn, tabela)
        elif op == "4":
            alterar(conn, tabela)
        elif op == "5":
            excluir(conn, tabela)
        elif op == "0":
            return
