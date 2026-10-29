SET ROLE grupo5_owner;

CREATE SCHEMA api_entregas;

CREATE VIEW api_entregas.vw_integracao_pedidos AS
SELECT
    p.pedido_id                         AS codigo_pedido,
    p.data_pedido                       AS data_pedido,
    p.status                            AS status_pedido,
    c.cliente_id                        AS codigo_cliente,
    c.nome::VARCHAR(120)                AS nome_cliente,
    c.telefone::VARCHAR(20)             AS telefone_cliente,
    e.logradouro::VARCHAR(150)          AS logradouro,
    e.numero::VARCHAR(10)               AS numero,
    e.complemento::VARCHAR(60)          AS complemento,
    e.bairro::VARCHAR(80)               AS bairro,
    e.cidade::VARCHAR(80)               AS cidade,
    e.uf::CHAR(2)                       AS uf,
    e.cep::VARCHAR(8)                   AS cep,
    (SELECT count(*) FROM pedidos.item_pedido i WHERE i.pedido_id = p.pedido_id)::INTEGER
                                        AS quantidade_itens,
    p.valor_total::NUMERIC(12,2)        AS valor_total,
    GREATEST(p.data_atualizacao, c.data_atualizacao, e.data_atualizacao)
                                        AS data_atualizacao
FROM pedidos.pedido   p
JOIN pedidos.cliente  c ON c.cliente_id  = p.cliente_id
JOIN pedidos.endereco e ON e.endereco_id = p.endereco_id
WHERE p.status IN ('CONFIRMADO', 'CANCELADO');

COMMENT ON VIEW api_entregas.vw_integracao_pedidos IS
 'Contrato Grupo 5 -> Grupo 7 v1.0: pedidos confirmados/cancelados para o Sistema de Entregas';

CREATE VIEW api_entregas.vw_integracao_itens_pedido AS
SELECT
    i.item_id                       AS codigo_item,
    i.pedido_id                     AS codigo_pedido,
    pr.id_produto_origem            AS codigo_produto,
    pr.nome::VARCHAR(120)           AS nome_produto,
    i.quantidade::NUMERIC(10,3)     AS quantidade,
    pr.unidade::VARCHAR(20)         AS unidade,
    i.preco_unitario::NUMERIC(12,2) AS preco_unitario,
    i.subtotal::NUMERIC(12,2)       AS subtotal,
    i.data_atualizacao              AS data_atualizacao
FROM pedidos.item_pedido i
JOIN pedidos.pedido  p  ON p.pedido_id   = i.pedido_id
JOIN pedidos.produto pr ON pr.produto_id = i.produto_id
WHERE p.status IN ('CONFIRMADO', 'CANCELADO');

COMMENT ON VIEW api_entregas.vw_integracao_itens_pedido IS
 'Contrato Grupo 5 -> Grupo 7 v1.0: itens dos pedidos publicados';

REVOKE ALL ON SCHEMA pedidos, controle FROM PUBLIC;
GRANT USAGE ON SCHEMA api_entregas TO grupo7_integracao;
GRANT SELECT ON api_entregas.vw_integracao_pedidos      TO grupo7_integracao;
GRANT SELECT ON api_entregas.vw_integracao_itens_pedido TO grupo7_integracao;

GRANT USAGE ON SCHEMA api_entregas TO grupo5_app;
GRANT SELECT ON ALL TABLES IN SCHEMA api_entregas TO grupo5_app;

INSERT INTO controle.historico_contrato (versao, estrutura, descricao) VALUES
 ('1.0', 'api_entregas.vw_integracao_pedidos',      'Criação da view de pedidos para o Sistema de Entregas (Grupo 7)'),
 ('1.0', 'api_entregas.vw_integracao_itens_pedido', 'Criação da view de itens de pedido para o Sistema de Entregas (Grupo 7)');

RESET ROLE;
