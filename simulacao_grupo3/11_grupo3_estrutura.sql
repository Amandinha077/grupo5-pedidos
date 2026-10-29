SET ROLE grupo3_owner;

CREATE TABLE public.categoria (
    categoria_id  INTEGER PRIMARY KEY,
    nome          VARCHAR(100) NOT NULL
);

CREATE TABLE public.produto (
    id_produto      INTEGER PRIMARY KEY,
    nome            VARCHAR(120) NOT NULL,
    descricao       VARCHAR(500),
    categoria_id    INTEGER CONSTRAINT fk_produto_categoria REFERENCES public.categoria(categoria_id),
    preco           NUMERIC(12,2) NOT NULL CONSTRAINT ck_preco CHECK (preco > 0),
    unidade_medida  VARCHAR(20) NOT NULL DEFAULT 'UN',
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE FUNCTION public.fn_atualizado_em() RETURNS trigger AS $$
BEGIN NEW.atualizado_em := now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_produto_upd BEFORE UPDATE ON public.produto
    FOR EACH ROW EXECUTE FUNCTION public.fn_atualizado_em();

INSERT INTO public.categoria VALUES
 (1, 'Alimentos'), (2, 'Bebidas'), (3, 'Limpeza'), (4, 'Higiene'), (5, 'Hortifruti');

INSERT INTO public.produto (id_produto, nome, descricao, categoria_id, preco, unidade_medida, ativo) VALUES
 (101, 'Arroz Tipo 1 5kg',        'Arroz agulhinha tipo 1',      1,  27.90, 'UN', TRUE),
 (102, 'Feijão Carioca 1kg',      'Feijão carioca tipo 1',       1,   8.49, 'UN', TRUE),
 (103, 'Café Torrado 500g',       'Café torrado e moído',        1,  18.90, 'UN', TRUE),
 (104, 'Refrigerante Cola 2L',    NULL,                          2,   9.99, 'UN', TRUE),
 (105, 'Suco de Laranja 1L',      '',                            2,   7.50, 'UN', TRUE),
 (106, 'Água Mineral 500ml',      NULL,                          2,   2.50, 'UN', TRUE),
 (107, 'Detergente Neutro 500ml', 'Detergente líquido',          3,   2.99, 'UN', TRUE),
 (108, 'Sabão em Pó 1kg',         NULL,                          3,  14.90, 'CX', TRUE),
 (109, 'Sabonete 90g',            'Sabonete hidratante',         4,   2.29, 'UN', TRUE),
 (110, 'Creme Dental 90g',        NULL,                          4,   4.99, 'UN', TRUE),
 (111, 'Banana Prata',            'Vendida por quilo',           5,   6.99, 'KG', TRUE),
 (112, 'Tomate',                  'Vendido por quilo',           5,   8.90, 'KG', TRUE),
 (113, 'Batata Inglesa',          'Vendida por quilo',           5,   5.49, 'KG', TRUE),
 (114, 'Leite Integral 1L',       NULL,                          1,   5.79, 'L',  TRUE),
 (115, 'Biscoito Recheado 130g',  'Produto fora de linha',       1,   3.49, 'PCT', FALSE);

CREATE VIEW public.vw_integracao_produtos AS
SELECT p.id_produto,
       p.nome,
       p.descricao,
       c.nome            AS categoria,
       p.preco,
       p.unidade_medida,
       p.ativo,
       p.atualizado_em
  FROM public.produto p
  LEFT JOIN public.categoria c ON c.categoria_id = p.categoria_id;

GRANT USAGE ON SCHEMA public TO grupo3_app;
GRANT SELECT ON public.vw_integracao_produtos TO grupo3_app;

RESET ROLE;
