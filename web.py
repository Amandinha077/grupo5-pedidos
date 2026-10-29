
from decimal import Decimal, InvalidOperation

from flask import Flask, render_template_string, request, redirect, url_for, flash
from app.conexao import conectar_consumidor

app = Flask(__name__)
app.secret_key = "grupo5-local-session"

ESTILO = """
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f1f5f9;color:#172033}
header{background:#14213d;color:white;padding:24px 5%}
header h1{margin:0 0 8px}
header p{margin:0;color:#cbd5e1}
main{max-width:1450px;margin:auto;padding:28px 5%}
a{color:#2456a6}
.menu{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}
.menu a,.btn{display:inline-block;padding:11px 15px;border-radius:8px;
text-decoration:none;border:0;cursor:pointer;font-size:14px}
.menu a{background:white;border:1px solid #dbe3ee;color:#14213d}
.btn{background:#14213d;color:white}
.btn-sec{background:#e2e8f0;color:#172033}
.btn-danger{background:#fee2e2;color:#991b1b}
.card{background:white;padding:22px;border-radius:13px;
box-shadow:0 4px 15px #0000000b;margin-bottom:20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}
.label{color:#64748b;font-size:14px}
.value{font-size:30px;font-weight:bold;margin-top:10px}
.status{padding:14px;border-radius:9px;margin:18px 0}
.ok{background:#dcfce7;color:#166534}
.err{background:#fee2e2;color:#991b1b}
form.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px}
label{display:block;font-weight:bold;font-size:14px;margin-bottom:6px}
input,select,textarea{width:100%;padding:11px;border:1px solid #cbd5e1;
border-radius:7px;font:inherit;background:white}
.actions{display:flex;gap:8px;flex-wrap:wrap}
.table-wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;background:white}
th,td{text-align:left;padding:12px;border-bottom:1px solid #e2e8f0}
th{background:#f8fafc;font-size:13px;color:#475569}
td{font-size:14px}
.badge{padding:5px 9px;border-radius:20px;font-size:12px;background:#dcfce7;color:#166534}
.badge.off{background:#e2e8f0;color:#475569}
.flash{padding:12px;border-radius:8px;background:#dbeafe;color:#1e40af;margin-bottom:12px}
.inline{display:inline}
@media(max-width:600px){main{padding:20px 4%}header{padding:22px 4%}.card{padding:16px}}
"""

BASE = """
<!DOCTYPE html><html lang="pt-BR"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ titulo }} | Grupo 5</title><style>""" + ESTILO + """</style></head>
<body><header><h1>Grupo 5 — Sistema de Pedidos</h1>
<p>Gerenciamento e integração de pedidos</p></header>
<main>
<nav class="menu">
<a href="/">📊 Dashboard</a><a href="/produtos">📦 Produtos</a>
<a href="/clientes">👥 Clientes</a><a href="/pedidos">🛒 Pedidos</a>
<a href="/categorias">🏷️ Categorias</a><a href="/integracao">🔄 Integração</a>
</nav>
{% for mensagem in get_flashed_messages() %}<div class="flash">{{ mensagem }}</div>{% endfor %}
""" + "{{ conteudo|safe }}" + """
</main></body></html>
"""

DASHBOARD = """
<h2>Visão geral</h2>
<div class="cards">
{% for rotulo, valor in indicadores %}
<div class="card"><div class="label">{{ rotulo }}</div><div class="value">{{ valor }}</div></div>
{% endfor %}
</div>
<div class="status {{ 'ok' if conectado else 'err' }}">
<strong>Banco de dados:</strong>
{{ 'Conexão estabelecida.' if conectado else 'Não foi possível consultar o banco.' }}
{% if erro %}<br>{{ erro }}{% endif %}
</div>
"""

PRODUTOS = """
<h2>Produtos</h2>
<p>Cadastre e gerencie os produtos do Grupo 5.</p>
<div class="card">
<h3>{{ 'Editar produto' if produto else 'Cadastrar produto' }}</h3>
<form class="grid" method="post" action="{{ url_for('salvar_produto', produto_id=produto.produto_id if produto else 0) }}">
<div><label>Nome *</label><input name="nome" maxlength="120" required value="{{ produto.nome if produto else '' }}"></div>
<div><label>Descrição</label><input name="descricao" maxlength="500" value="{{ produto.descricao if produto else '' }}"></div>
<div><label>Categoria</label><select name="categoria_id"><option value="">Sem categoria</option>
{% for c in categorias %}<option value="{{ c[0] }}" {% if produto and produto.categoria_id == c[0] %}selected{% endif %}>{{ c[1] }}</option>{% endfor %}
</select></div>
<div><label>Preço (R$) *</label><input name="preco" type="number" min="0.01" step="0.01" required value="{{ produto.preco if produto else '' }}"></div>
<div><label>Unidade *</label><input name="unidade" maxlength="20" required value="{{ produto.unidade if produto else 'UN' }}"></div>
<div><label>Disponível?</label><select name="disponivel">
<option value="true" {% if not produto or produto.disponivel %}selected{% endif %}>Sim</option>
<option value="false" {% if produto and not produto.disponivel %}selected{% endif %}>Não</option>
</select></div>
<div><label>Código de origem (Grupo 3)</label><input value="{{ produto.id_produto_origem if produto and produto.id_produto_origem else 'Gerenciado pela integração' }}" disabled></div>
<div class="actions" style="align-self:end">
<button class="btn" type="submit">Salvar produto</button>
{% if produto %}<a class="btn btn-sec" href="/produtos">Cancelar</a>{% endif %}
</div>
</form>
</div>
<div class="card">
<form method="get" class="grid">
<div><label>Pesquisar produto</label><input name="q" placeholder="Digite o nome..." value="{{ busca }}"></div>
<div class="actions" style="align-self:end"><button class="btn" type="submit">Pesquisar</button><a class="btn btn-sec" href="/produtos">Limpar</a></div>
</form>
</div>
<div class="card">
<h3>Produtos cadastrados ({{ produtos|length }})</h3>
<div class="table-wrap"><table>
<thead><tr><th>ID</th><th>Produto</th><th>Categoria</th><th>Preço</th><th>Unidade</th><th>Status</th><th>Origem</th><th>Ações</th></tr></thead>
<tbody>
{% for p in produtos %}
<tr>
<td>{{ p.produto_id }}</td><td><strong>{{ p.nome }}</strong><br><small>{{ p.descricao or '' }}</small></td>
<td>{{ p.categoria or '—' }}</td><td>R$ {{ '%.2f'|format(p.preco) }}</td><td>{{ p.unidade }}</td>
<td><span class="badge {{ '' if p.disponivel else 'off' }}">{{ 'Disponível' if p.disponivel else 'Indisponível' }}</span></td>
<td>{{ 'Grupo 3' if p.id_produto_origem else 'Local' }}</td>
<td><div class="actions">
{% if not p.id_produto_origem %}
<a class="btn btn-sec" href="/produtos/editar/{{ p.produto_id }}">Editar</a>
<form class="inline" method="post" action="/produtos/excluir/{{ p.produto_id }}" onsubmit="return confirm('Confirma a exclusão deste produto?')">
<button class="btn btn-danger" type="submit">Excluir</button></form>
{% else %}<small>Gerenciado pela integração</small>{% endif %}
</div></td>
</tr>
{% else %}<tr><td colspan="8">Nenhum produto encontrado.</td></tr>{% endfor %}
</tbody></table></div>
</div>
"""

@app.route("/")
def inicio():
    consultas = [
        ("Clientes cadastrados", "SELECT COUNT(*) FROM pedidos.cliente"),
        ("Produtos cadastrados", "SELECT COUNT(*) FROM pedidos.produto"),
        ("Categorias", "SELECT COUNT(*) FROM pedidos.categoria"),
        ("Pedidos", "SELECT COUNT(*) FROM pedidos.pedido"),
        ("Integrações realizadas", "SELECT COUNT(*) FROM controle.integracao"),
        ("Erros pendentes", "SELECT COUNT(*) FROM controle.erro_integracao WHERE NOT resolvido AND gravidade <> 'AVISO'"),
    ]
    indicadores = []
    conectado = False
    erro = ""
    conn = None
    try:
        conn = conectar_consumidor()
        with conn.cursor() as cur:
            for rotulo, consulta in consultas:
                cur.execute(consulta)
                indicadores.append((rotulo, cur.fetchone()[0]))
        conectado = True
    except Exception:
        erro = "Confira a conexão e a estrutura das tabelas."
    finally:
        if conn:
            conn.close()
    return render_template_string(BASE, titulo="Dashboard",
        conteudo=render_template_string(DASHBOARD, indicadores=indicadores,
        conectado=conectado, erro=erro))

def consultar_categorias(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT categoria_id, nome FROM pedidos.categoria ORDER BY nome")
        return cur.fetchall()

@app.route("/produtos")
def produtos():
    conn = conectar_consumidor()
    try:
        busca = request.args.get("q", "").strip()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.produto_id, p.nome, p.descricao, p.categoria_id,
                       c.nome AS categoria, p.preco, p.unidade, p.disponivel,
                       p.id_produto_origem
                FROM pedidos.produto p
                LEFT JOIN pedidos.categoria c ON c.categoria_id = p.categoria_id
                WHERE p.nome ILIKE %s
                ORDER BY p.produto_id DESC
            """, (f"%{busca}%",))
            produtos_lista = [dict(zip([d.name for d in cur.description], row))
                              for row in cur.fetchall()]
        categorias = consultar_categorias(conn)
    finally:
        conn.close()
    return render_template_string(BASE, titulo="Produtos",
        conteudo=render_template_string(PRODUTOS, produtos=produtos_lista,
        categorias=categorias, produto=None, busca=busca))

@app.route("/produtos/salvar/<int:produto_id>", methods=["POST"])
def salvar_produto(produto_id):
    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip() or None
    categoria_texto = request.form.get("categoria_id", "").strip()
    preco_texto = request.form.get("preco", "").strip().replace(",", ".")
    unidade = request.form.get("unidade", "").strip()
    disponivel = request.form.get("disponivel") == "true"

    if not nome or not unidade or len(nome) > 120 or len(unidade) > 20:
        flash("Informe nome e unidade válidos.")
        return redirect(url_for("produtos"))

    try:
        preco = Decimal(preco_texto)
        if not preco.is_finite() or preco <= 0:
            raise InvalidOperation
        categoria_id = int(categoria_texto) if categoria_texto else None
    except (InvalidOperation, ValueError):
        flash("Preço ou categoria inválidos.")
        return redirect(url_for("produtos"))

    conn = conectar_consumidor()
    try:
        with conn.cursor() as cur:
            if produto_id:
                cur.execute("SELECT id_produto_origem FROM pedidos.produto WHERE produto_id=%s FOR UPDATE", (produto_id,))
                existente = cur.fetchone()
                if not existente:
                    flash("Produto não encontrado.")
                    return redirect(url_for("produtos"))
                if existente[0] is not None:
                    flash("Produtos do Grupo 3 são gerenciados pela integração.")
                    return redirect(url_for("produtos"))
                cur.execute("""
                    UPDATE pedidos.produto
                    SET nome=%s, descricao=%s, categoria_id=%s, preco=%s,
                        unidade=%s, disponivel=%s, data_atualizacao=now()
                    WHERE produto_id=%s
                """, (nome, descricao, categoria_id, preco, unidade, disponivel, produto_id))
                flash("Produto atualizado com sucesso.")
            else:
                cur.execute("""
                    INSERT INTO pedidos.produto
                        (nome, descricao, categoria_id, preco, unidade, disponivel)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (nome, descricao, categoria_id, preco, unidade, disponivel))
                flash("Produto cadastrado com sucesso.")
        conn.commit()
    except Exception:
        conn.rollback()
        flash("Não foi possível salvar. Confira os dados e as regras do banco.")
    finally:
        conn.close()
    return redirect(url_for("produtos"))

@app.route("/produtos/editar/<int:produto_id>")
def editar_produto(produto_id):
    conn = conectar_consumidor()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT produto_id, nome, descricao, categoria_id, preco, unidade,
                       disponivel, id_produto_origem
                FROM pedidos.produto WHERE produto_id=%s
            """, (produto_id,))
            row = cur.fetchone()
            if not row:
                flash("Produto não encontrado.")
                return redirect(url_for("produtos"))
            produto = dict(zip([d.name for d in cur.description], row))
            if produto["id_produto_origem"] is not None:
                flash("Este produto é gerenciado pela integração do Grupo 3.")
                return redirect(url_for("produtos"))
        categorias = consultar_categorias(conn)
    finally:
        conn.close()
    with open(__file__, encoding="utf-8") as arquivo:
        codigo = arquivo.read()
    # Reutiliza o mesmo formulário da tela de produtos.
    return render_template_string(BASE, titulo="Editar produto",
        conteudo=render_template_string(PRODUTOS, produtos=[], categorias=categorias,
        produto=produto, busca=""))

@app.route("/produtos/excluir/<int:produto_id>", methods=["POST"])
def excluir_produto(produto_id):
    conn = conectar_consumidor()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id_produto_origem FROM pedidos.produto WHERE produto_id=%s", (produto_id,))
            row = cur.fetchone()
            if not row:
                flash("Produto não encontrado.")
            elif row[0] is not None:
                flash("Produtos do Grupo 3 não podem ser excluídos por esta tela.")
            else:
                cur.execute("DELETE FROM pedidos.produto WHERE produto_id=%s", (produto_id,))
                conn.commit()
                flash("Produto excluído com sucesso.")
    except Exception:
        conn.rollback()
        flash("Não foi possível excluir. O produto pode estar associado a um pedido.")
    finally:
        conn.close()
    return redirect(url_for("produtos"))

@app.route("/<modulo>")
def modulo(modulo):
    nomes = {"clientes": "Clientes", "pedidos": "Pedidos",
             "categorias": "Categorias", "integracao": "Integração"}
    if modulo not in nomes:
        return "Página não encontrada", 404
    return render_template_string(BASE, titulo=nomes[modulo],
        conteudo="<div class='card'><h2>" + nomes[modulo] +
        "</h2><p>Esta tela será implementada na próxima etapa.</p>"
        "<a href='/'>Voltar ao dashboard</a></div>")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
