SET ROLE grupo5_app;

DO $$
DECLARE
    prod INTEGER[];
    n    INTEGER;
BEGIN
    SELECT array_agg(produto_id ORDER BY produto_id) INTO prod
      FROM pedidos.produto WHERE disponivel;
    n := COALESCE(array_length(prod, 1), 0);

    IF n < 3 THEN
        RAISE EXCEPTION 'É preciso ter pelo menos 3 produtos disponíveis. Rode a integração com o Grupo 3 primeiro (encontrados: %).', n;
    END IF;

    INSERT INTO pedidos.pedido (cliente_id, endereco_id, observacao) VALUES (1, 1, 'Entregar no período da manhã');
    INSERT INTO pedidos.item_pedido (pedido_id, produto_id, quantidade) VALUES
        (currval('pedidos.pedido_pedido_id_seq'), prod[1], 2),
        (currval('pedidos.pedido_pedido_id_seq'), prod[2], 1);
    UPDATE pedidos.pedido SET status = 'CONFIRMADO' WHERE pedido_id = currval('pedidos.pedido_pedido_id_seq');

    INSERT INTO pedidos.pedido (cliente_id, endereco_id) VALUES (2, 2);
    INSERT INTO pedidos.item_pedido (pedido_id, produto_id, quantidade) VALUES
        (currval('pedidos.pedido_pedido_id_seq'), prod[3], 3);
    UPDATE pedidos.pedido SET status = 'CONFIRMADO' WHERE pedido_id = currval('pedidos.pedido_pedido_id_seq');

    INSERT INTO pedidos.pedido (cliente_id, endereco_id, observacao) VALUES (3, 3, 'Portão azul');
    INSERT INTO pedidos.item_pedido (pedido_id, produto_id, quantidade) VALUES
        (currval('pedidos.pedido_pedido_id_seq'), prod[1], 1),
        (currval('pedidos.pedido_pedido_id_seq'), prod[3], 2);
    UPDATE pedidos.pedido SET status = 'CONFIRMADO' WHERE pedido_id = currval('pedidos.pedido_pedido_id_seq');

    INSERT INTO pedidos.pedido (cliente_id, endereco_id) VALUES (4, 4);
    INSERT INTO pedidos.item_pedido (pedido_id, produto_id, quantidade) VALUES
        (currval('pedidos.pedido_pedido_id_seq'), prod[2], 5);

    INSERT INTO pedidos.pedido (cliente_id, endereco_id, observacao) VALUES (5, 5, 'Cliente desistiu');
    INSERT INTO pedidos.item_pedido (pedido_id, produto_id, quantidade) VALUES
        (currval('pedidos.pedido_pedido_id_seq'), prod[1], 1);
    UPDATE pedidos.pedido SET status = 'CONFIRMADO' WHERE pedido_id = currval('pedidos.pedido_pedido_id_seq');
    UPDATE pedidos.pedido SET status = 'CANCELADO'  WHERE pedido_id = currval('pedidos.pedido_pedido_id_seq');

    INSERT INTO pedidos.pedido (cliente_id, endereco_id) VALUES (6, 6);
    INSERT INTO pedidos.item_pedido (pedido_id, produto_id, quantidade) VALUES
        (currval('pedidos.pedido_pedido_id_seq'), prod[LEAST(n, 4)], 2),
        (currval('pedidos.pedido_pedido_id_seq'), prod[2], 1);
    UPDATE pedidos.pedido SET status = 'CONFIRMADO' WHERE pedido_id = currval('pedidos.pedido_pedido_id_seq');

    RAISE NOTICE 'Pedidos de teste criados com sucesso.';
END $$;

RESET ROLE;
