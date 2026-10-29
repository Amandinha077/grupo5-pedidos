SET ROLE grupo3_owner;

UPDATE public.produto SET preco = 4.50                  WHERE id_produto = 201;
UPDATE public.produto SET nome  = 'Água com Gás 500ml'  WHERE id_produto = 202;
UPDATE public.produto SET preco = 32.90                 WHERE id_produto = 203;
UPDATE public.produto SET categoria_id = 3              WHERE id_produto = 204;
UPDATE public.produto SET unidade_medida = 'UN'         WHERE id_produto = 205;

DROP VIEW public.vw_integracao_produtos;
CREATE VIEW public.vw_integracao_produtos AS
SELECT p.id_produto, p.nome, p.descricao, c.nome AS categoria, p.preco,
       p.unidade_medida, p.ativo, p.atualizado_em
  FROM public.produto p LEFT JOIN public.categoria c ON c.categoria_id = p.categoria_id;
GRANT SELECT ON public.vw_integracao_produtos TO grupo3_app;

ALTER TABLE public.produto ALTER COLUMN preco SET NOT NULL;
ALTER TABLE public.produto ADD CONSTRAINT ck_preco CHECK (preco > 0);
ALTER TABLE public.produto ADD CONSTRAINT fk_produto_categoria
      FOREIGN KEY (categoria_id) REFERENCES public.categoria(categoria_id);

RESET ROLE;
