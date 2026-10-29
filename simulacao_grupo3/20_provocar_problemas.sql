SET ROLE grupo3_owner;

ALTER TABLE public.produto DROP CONSTRAINT IF EXISTS ck_preco;
ALTER TABLE public.produto DROP CONSTRAINT IF EXISTS fk_produto_categoria;
ALTER TABLE public.produto ALTER COLUMN preco DROP NOT NULL;

INSERT INTO public.produto (id_produto, nome, descricao, categoria_id, preco, unidade_medida, ativo) VALUES
 (201, 'Macarrão Espaguete 500g', NULL, 1,  -4.50, 'UN', TRUE),
 (202, '   ',                     NULL, 2,   3.00, 'UN', TRUE),
 (203, 'Azeite Extra Virgem',     NULL, 1,   NULL, 'UN', TRUE),
 (204, 'Desinfetante 2L',         NULL, 999, 9.90, 'UN', TRUE),
 (205, 'Esponja Multiuso',        NULL, 3,   1.99, '',   TRUE);

DROP VIEW public.vw_integracao_produtos;
CREATE VIEW public.vw_integracao_produtos AS
SELECT p.id_produto, p.nome, p.descricao, c.nome AS categoria, p.preco,
       p.unidade_medida, p.ativo, p.atualizado_em
  FROM public.produto p LEFT JOIN public.categoria c ON c.categoria_id = p.categoria_id
UNION ALL
SELECT 102, 'Feijão Carioca 1kg', 'Linha antiga', 'Alimentos', 7.99, 'UN', TRUE, now();
GRANT SELECT ON public.vw_integracao_produtos TO grupo3_app;

DELETE FROM public.produto WHERE id_produto = 114;

RESET ROLE;
