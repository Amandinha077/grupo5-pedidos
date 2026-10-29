SET ROLE grupo3_owner;

UPDATE public.produto SET preco = 29.90                           WHERE id_produto = 101;
UPDATE public.produto SET nome  = 'Café Torrado Extra Forte 500g' WHERE id_produto = 103;
UPDATE public.produto SET ativo = FALSE                           WHERE id_produto = 106;
UPDATE public.produto SET categoria_id = 4                        WHERE id_produto = 107;

RESET ROLE;
