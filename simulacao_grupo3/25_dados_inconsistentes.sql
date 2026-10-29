SET ROLE grupo3_owner;

ALTER TABLE public.produto DISABLE TRIGGER trg_produto_upd;

UPDATE public.produto
   SET preco = preco + 0.50, atualizado_em = now() + interval '30 days'
 WHERE id_produto = 104;

UPDATE public.produto
   SET preco = preco + 1.00, atualizado_em = timestamptz '2020-01-01 10:00:00-03'
 WHERE id_produto = 105;

ALTER TABLE public.produto ENABLE TRIGGER trg_produto_upd;

RESET ROLE;
