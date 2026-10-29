from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

COLUNAS_CONTRATO = [
    "id_produto", "nome", "descricao", "categoria",
    "preco", "unidade_medida", "ativo", "atualizado_em",
]

TAM_NOME = 120
TAM_DESCRICAO = 500
TAM_CATEGORIA = 100
TAM_UNIDADE = 20
TOLERANCIA_RELOGIO = timedelta(minutes=5)
PRECO_MAXIMO = Decimal("9999999999.99")


class ErroValidacao:
    def __init__(self, campo, tipo, descricao, valor=None):
        self.campo = campo
        self.tipo = tipo
        self.descricao = descricao
        self.valor = None if valor is None else str(valor)

    def __repr__(self):
        return f"{self.tipo}({self.campo}): {self.descricao}"


def _texto(v):
    if v is None:
        return None
    t = " ".join(str(v).split())
    return t or None


def _inteiro(v):
    if v is None or isinstance(v, bool):
        raise ValueError
    if isinstance(v, int):
        return v
    if isinstance(v, Decimal) and v == v.to_integral_value():
        return int(v)
    texto = str(v).strip()
    if not texto.lstrip("-").isdigit():
        raise ValueError
    return int(texto)


def _booleano(v):
    if isinstance(v, bool):
        return v
    mapa = {"t": True, "true": True, "1": True, "s": True, "sim": True,
            "f": False, "false": False, "0": False, "n": False, "nao": False, "não": False}
    chave = str(v).strip().lower()
    if chave in mapa:
        return mapa[chave]
    raise ValueError


def _data_hora(v):
    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, date):
        dt = datetime(v.year, v.month, v.day)
    else:
        dt = datetime.fromisoformat(str(v).strip())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=-3)))
    return dt


def validar_e_transformar(reg):
    erros = []
    dados = {}

    v = reg.get("id_produto")
    if v is None:
        erros.append(ErroValidacao("id_produto", "CAMPO_OBRIGATORIO", "Identificador do produto não informado"))
    else:
        try:
            cod = _inteiro(v)
            if cod <= 0:
                raise ValueError
            dados["id_produto_origem"] = cod
        except ValueError:
            erros.append(ErroValidacao("id_produto", "TIPO_INVALIDO", "id_produto deve ser inteiro positivo", v))

    nome = _texto(reg.get("nome"))
    if nome is None:
        erros.append(ErroValidacao("nome", "CAMPO_OBRIGATORIO", "Nome do produto vazio ou nulo", reg.get("nome")))
    elif len(nome) > TAM_NOME:
        erros.append(ErroValidacao("nome", "TAMANHO_EXCEDIDO", f"Nome com {len(nome)} caracteres (máx. {TAM_NOME})", nome[:40] + "..."))
    else:
        dados["nome"] = nome

    desc = _texto(reg.get("descricao"))
    if desc is not None and len(desc) > TAM_DESCRICAO:
        erros.append(ErroValidacao("descricao", "TAMANHO_EXCEDIDO", f"Descrição com {len(desc)} caracteres (máx. {TAM_DESCRICAO})", desc[:40] + "..."))
    else:
        dados["descricao"] = desc

    cat = _texto(reg.get("categoria"))
    if cat is None:
        erros.append(ErroValidacao("categoria", "INTEGRIDADE_REFERENCIAL", "Produto sem categoria válida: a categoria veio nula ou vazia (o produto aponta para uma categoria que não existe no Grupo 3). Rejeitado até o Grupo 3 corrigir; será reprocessado depois", reg.get("categoria")))
    elif len(cat) > TAM_CATEGORIA:
        erros.append(ErroValidacao("categoria", "TAMANHO_EXCEDIDO", f"Categoria excede {TAM_CATEGORIA} caracteres", cat[:40]))
    else:
        dados["nome_categoria"] = cat

    v = reg.get("preco")
    if v is None:
        erros.append(ErroValidacao("preco", "CAMPO_OBRIGATORIO", "Preço nulo"))
    else:
        try:
            preco = Decimal(str(v).replace(",", "."))
            if not preco.is_finite():
                raise InvalidOperation
            preco = preco.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if preco <= 0:
                erros.append(ErroValidacao("preco", "VALOR_INVALIDO", "Preço deve ser maior que zero", v))
            elif preco > PRECO_MAXIMO:
                erros.append(ErroValidacao("preco", "VALOR_INVALIDO", "Preço acima do limite NUMERIC(12,2)", v))
            else:
                dados["preco"] = preco
        except (InvalidOperation, ValueError):
            erros.append(ErroValidacao("preco", "TIPO_INVALIDO", "Preço não é um número válido", v))

    un = _texto(reg.get("unidade_medida"))
    if un is None:
        erros.append(ErroValidacao("unidade_medida", "CAMPO_OBRIGATORIO", "Unidade de medida não informada", reg.get("unidade_medida")))
    elif len(un) > TAM_UNIDADE:
        erros.append(ErroValidacao("unidade_medida", "TAMANHO_EXCEDIDO", f"Unidade excede {TAM_UNIDADE} caracteres", un))
    else:
        dados["unidade"] = un.upper()

    v = reg.get("ativo")
    if v is None:
        erros.append(ErroValidacao("ativo", "CAMPO_OBRIGATORIO", "Situação (ativo) não informada"))
    else:
        try:
            dados["disponivel"] = _booleano(v)
        except ValueError:
            erros.append(ErroValidacao("ativo", "TIPO_INVALIDO", "Valor de 'ativo' não é booleano", v))

    v = reg.get("atualizado_em")
    if v is None:
        erros.append(ErroValidacao("atualizado_em", "CAMPO_OBRIGATORIO", "Data da última alteração não informada"))
    else:
        try:
            dt = _data_hora(v)
            if dt > datetime.now(timezone.utc) + TOLERANCIA_RELOGIO:
                erros.append(ErroValidacao("atualizado_em", "DADO_INCONSISTENTE",
                                           "Data da última alteração está no futuro: o produto não pode ter sido "
                                           "alterado depois de agora", v))
            else:
                dados["data_atualizacao_origem"] = dt
        except ValueError:
            erros.append(ErroValidacao("atualizado_em", "TIPO_INVALIDO", "Data/hora de atualização inválida", v))

    return erros, dados
