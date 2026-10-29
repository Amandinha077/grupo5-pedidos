SET ROLE grupo5_owner;

CREATE SCHEMA pedidos;
CREATE SCHEMA controle;

CREATE FUNCTION pedidos.fn_atualiza_data() RETURNS trigger AS $$
BEGIN
    NEW.data_atualizacao := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE pedidos.categoria (
    categoria_id          SERIAL PRIMARY KEY,
    nome                  VARCHAR(100) NOT NULL CHECK (btrim(nome) <> ''),
    data_inclusao         TIMESTAMP NOT NULL DEFAULT now(),
    data_atualizacao      TIMESTAMP NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_categoria_nome ON pedidos.categoria (lower(nome));

CREATE TABLE pedidos.produto (
    produto_id               SERIAL PRIMARY KEY,
    id_produto_origem        INTEGER UNIQUE,
    nome                     VARCHAR(120) NOT NULL,
    descricao                VARCHAR(500),
    categoria_id             INTEGER REFERENCES pedidos.categoria(categoria_id),
    preco                    NUMERIC(12,2) NOT NULL CHECK (preco > 0),
    unidade                  VARCHAR(20) NOT NULL DEFAULT 'UN',
    disponivel               BOOLEAN NOT NULL DEFAULT TRUE,
    data_atualizacao_origem  TIMESTAMPTZ,
    data_ultima_integracao   TIMESTAMP,
    data_inclusao            TIMESTAMP NOT NULL DEFAULT now(),
    data_atualizacao         TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE pedidos.cliente (
    cliente_id        SERIAL PRIMARY KEY,
    nome              VARCHAR(120) NOT NULL CHECK (btrim(nome) <> ''),
    cpf               VARCHAR(11)  NOT NULL UNIQUE CHECK (cpf ~ '^[0-9]{11}$'),
    email             VARCHAR(120) CHECK (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    telefone          VARCHAR(20),
    data_inclusao     TIMESTAMP NOT NULL DEFAULT now(),
    data_atualizacao  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE pedidos.endereco (
    endereco_id       SERIAL PRIMARY KEY,
    cliente_id        INTEGER NOT NULL REFERENCES pedidos.cliente(cliente_id) ON DELETE CASCADE,
    logradouro        VARCHAR(150) NOT NULL,
    numero            VARCHAR(10)  NOT NULL,
    complemento       VARCHAR(60),
    bairro            VARCHAR(80)  NOT NULL,
    cidade            VARCHAR(80)  NOT NULL,
    uf                CHAR(2)      NOT NULL CHECK (uf ~ '^[A-Z]{2}$'),
    cep               VARCHAR(8)   NOT NULL CHECK (cep ~ '^[0-9]{8}$'),
    data_inclusao     TIMESTAMP NOT NULL DEFAULT now(),
    data_atualizacao  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE pedidos.pedido (
    pedido_id         SERIAL PRIMARY KEY,
    cliente_id        INTEGER NOT NULL REFERENCES pedidos.cliente(cliente_id),
    endereco_id       INTEGER NOT NULL REFERENCES pedidos.endereco(endereco_id),
    data_pedido       TIMESTAMP NOT NULL DEFAULT now(),
    status            VARCHAR(15) NOT NULL DEFAULT 'ABERTO'
                      CHECK (status IN ('ABERTO','CONFIRMADO','CANCELADO')),
    valor_total       NUMERIC(12,2) NOT NULL DEFAULT 0,
    observacao        VARCHAR(255),
    data_inclusao     TIMESTAMP NOT NULL DEFAULT now(),
    data_atualizacao  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE pedidos.item_pedido (
    item_id           SERIAL PRIMARY KEY,
    pedido_id         INTEGER NOT NULL REFERENCES pedidos.pedido(pedido_id) ON DELETE CASCADE,
    produto_id        INTEGER NOT NULL REFERENCES pedidos.produto(produto_id),
    quantidade        NUMERIC(10,3) NOT NULL CHECK (quantidade > 0),
    preco_unitario    NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (preco_unitario >= 0),
    subtotal          NUMERIC(12,2) GENERATED ALWAYS AS (round(quantidade * preco_unitario, 2)) STORED,
    data_inclusao     TIMESTAMP NOT NULL DEFAULT now(),
    data_atualizacao  TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (pedido_id, produto_id)
);

CREATE INDEX ix_endereco_cliente ON pedidos.endereco(cliente_id);
CREATE INDEX ix_pedido_cliente   ON pedidos.pedido(cliente_id);
CREATE INDEX ix_item_pedido      ON pedidos.item_pedido(pedido_id);

CREATE TRIGGER trg_categoria_upd BEFORE UPDATE ON pedidos.categoria   FOR EACH ROW EXECUTE FUNCTION pedidos.fn_atualiza_data();
CREATE TRIGGER trg_produto_upd   BEFORE UPDATE ON pedidos.produto     FOR EACH ROW EXECUTE FUNCTION pedidos.fn_atualiza_data();
CREATE TRIGGER trg_cliente_upd   BEFORE UPDATE ON pedidos.cliente     FOR EACH ROW EXECUTE FUNCTION pedidos.fn_atualiza_data();
CREATE TRIGGER trg_endereco_upd  BEFORE UPDATE ON pedidos.endereco    FOR EACH ROW EXECUTE FUNCTION pedidos.fn_atualiza_data();
CREATE TRIGGER trg_pedido_upd    BEFORE UPDATE ON pedidos.pedido      FOR EACH ROW EXECUTE FUNCTION pedidos.fn_atualiza_data();
CREATE TRIGGER trg_item_upd      BEFORE UPDATE ON pedidos.item_pedido FOR EACH ROW EXECUTE FUNCTION pedidos.fn_atualiza_data();

CREATE FUNCTION pedidos.fn_valida_item() RETURNS trigger AS $$
DECLARE
    v_disp  BOOLEAN;
    v_preco NUMERIC(12,2);
    v_status VARCHAR(15);
BEGIN
    SELECT disponivel, preco INTO v_disp, v_preco
      FROM pedidos.produto WHERE produto_id = NEW.produto_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Produto % não existe', NEW.produto_id;
    END IF;

    SELECT status INTO v_status FROM pedidos.pedido WHERE pedido_id = NEW.pedido_id;
    IF v_status <> 'ABERTO' THEN
        RAISE EXCEPTION 'Pedido % está %, itens não podem ser alterados', NEW.pedido_id, v_status;
    END IF;

    IF TG_OP = 'INSERT' OR NEW.produto_id <> OLD.produto_id THEN
        IF NOT v_disp THEN
            RAISE EXCEPTION 'Produto % está indisponível (inativo no Sistema de Produtos)', NEW.produto_id;
        END IF;
        NEW.preco_unitario := v_preco;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_item_valida BEFORE INSERT OR UPDATE ON pedidos.item_pedido
    FOR EACH ROW EXECUTE FUNCTION pedidos.fn_valida_item();

CREATE FUNCTION pedidos.fn_recalcula_total() RETURNS trigger AS $$
DECLARE
    v_pedido INTEGER := COALESCE(NEW.pedido_id, OLD.pedido_id);
BEGIN
    UPDATE pedidos.pedido
       SET valor_total = COALESCE((SELECT sum(subtotal) FROM pedidos.item_pedido
                                    WHERE pedido_id = v_pedido), 0)
     WHERE pedido_id = v_pedido;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_item_total AFTER INSERT OR UPDATE OR DELETE ON pedidos.item_pedido
    FOR EACH ROW EXECUTE FUNCTION pedidos.fn_recalcula_total();

CREATE FUNCTION pedidos.fn_valida_pedido() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pedidos.endereco
                    WHERE endereco_id = NEW.endereco_id AND cliente_id = NEW.cliente_id) THEN
        RAISE EXCEPTION 'Endereço % não pertence ao cliente %', NEW.endereco_id, NEW.cliente_id;
    END IF;
    IF NEW.status = 'CONFIRMADO' AND NEW.valor_total <= 0 THEN
        RAISE EXCEPTION 'Pedido sem itens não pode ser confirmado';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_pedido_valida BEFORE INSERT OR UPDATE ON pedidos.pedido
    FOR EACH ROW EXECUTE FUNCTION pedidos.fn_valida_pedido();

CREATE TABLE controle.integracao (
    integracao_id     SERIAL PRIMARY KEY,
    data_inicio       TIMESTAMP NOT NULL DEFAULT now(),
    data_fim          TIMESTAMP,
    sistema_origem    VARCHAR(60) NOT NULL,
    sistema_destino   VARCHAR(60) NOT NULL,
    estrutura_origem  VARCHAR(100) NOT NULL,
    total_registros   INTEGER NOT NULL DEFAULT 0,
    processados       INTEGER NOT NULL DEFAULT 0,
    inseridos         INTEGER NOT NULL DEFAULT 0,
    atualizados       INTEGER NOT NULL DEFAULT 0,
    sem_alteracao     INTEGER NOT NULL DEFAULT 0,
    rejeitados        INTEGER NOT NULL DEFAULT 0,
    inativados        INTEGER NOT NULL DEFAULT 0,
    status            VARCHAR(25) NOT NULL DEFAULT 'EM_ANDAMENTO'
                      CHECK (status IN ('EM_ANDAMENTO','CONCLUIDA','CONCLUIDA_COM_ERROS','FALHA')),
    mensagem          TEXT
);

CREATE TABLE controle.erro_integracao (
    erro_id           SERIAL PRIMARY KEY,
    integracao_id     INTEGER NOT NULL REFERENCES controle.integracao(integracao_id),
    registro_origem   VARCHAR(50),
    campo             VARCHAR(60),
    tipo_erro         VARCHAR(40) NOT NULL,
    descricao         TEXT NOT NULL,
    valor_recebido    TEXT,
    gravidade         VARCHAR(10) NOT NULL DEFAULT 'ERRO' CHECK (gravidade IN ('ERRO','AVISO','FATAL')),
    data_ocorrencia   TIMESTAMP NOT NULL DEFAULT now(),
    resolvido         BOOLEAN NOT NULL DEFAULT FALSE,
    data_resolucao    TIMESTAMP,
    resolvido_na_integracao INTEGER REFERENCES controle.integracao(integracao_id)
);

CREATE INDEX ix_erro_integracao ON controle.erro_integracao(integracao_id);
CREATE INDEX ix_erro_registro   ON controle.erro_integracao(registro_origem) WHERE NOT resolvido;

CREATE TABLE controle.historico_contrato (
    historico_id   SERIAL PRIMARY KEY,
    versao         VARCHAR(10) NOT NULL,
    estrutura      VARCHAR(100) NOT NULL,
    descricao      TEXT NOT NULL,
    data_alteracao TIMESTAMP NOT NULL DEFAULT now()
);

GRANT USAGE ON SCHEMA pedidos, controle TO grupo5_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pedidos  TO grupo5_app;
GRANT SELECT, INSERT, UPDATE         ON ALL TABLES IN SCHEMA controle TO grupo5_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA pedidos, controle TO grupo5_app;

RESET ROLE;
