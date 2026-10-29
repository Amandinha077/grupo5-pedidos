SET ROLE grupo3_owner;

INSERT INTO public.categoria (categoria_id, nome) VALUES (6, 'Pet Shop');

ALTER TABLE public.produto ADD CONSTRAINT fk_produto_categoria
      FOREIGN KEY (categoria_id) REFERENCES public.categoria(categoria_id);

RESET ROLE;
