SET ROLE grupo3_owner;

UPDATE public.produto SET atualizado_em = now() WHERE id_produto IN (104, 105);

RESET ROLE;
