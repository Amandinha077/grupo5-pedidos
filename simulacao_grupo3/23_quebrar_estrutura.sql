SET ROLE grupo3_owner;

DROP VIEW public.vw_integracao_produtos;
CREATE VIEW public.vw_integracao_produtos AS
SELECT p.id_produto, p.nome, p.descricao, c.nome AS categoria,
       p.preco AS valor_unitario,
       p.unidade_medida, p.ativo, p.atualizado_em
  FROM public.produto p LEFT JOIN public.categoria c ON c.categoria_id = p.categoria_id;
GRANT SELECT ON public.vw_integracao_produtos TO grupo3_app;

RESET ROLE;
