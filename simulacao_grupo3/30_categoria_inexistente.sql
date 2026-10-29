SET ROLE grupo3_owner;

ALTER TABLE public.produto DROP CONSTRAINT IF EXISTS fk_produto_categoria;

INSERT INTO public.produto (id_produto, nome, descricao, categoria_id, preco, unidade_medida, ativo)
VALUES (301, 'Ração para Cães 1kg', NULL, 6, 19.90, 'UN', TRUE);

RESET ROLE;
