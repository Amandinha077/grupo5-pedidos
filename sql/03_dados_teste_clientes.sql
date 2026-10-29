SET ROLE grupo5_app;

INSERT INTO pedidos.cliente (nome, cpf, email, telefone) VALUES
 ('João Silva',        '12345678901', 'joao.silva@email.com',   '62991110001'),
 ('Maria Souza',       '23456789012', 'maria.souza@email.com',  '62991110002'),
 ('Pedro Henrique',    '34567890123', 'pedro.h@email.com',      '62991110003'),
 ('Ana Paula Ribeiro', '45678901234', 'ana.ribeiro@email.com',  '62991110004'),
 ('Carlos Eduardo',    '56789012345', 'carlos.edu@email.com',   '62991110005'),
 ('Fernanda Lima',     '67890123456', 'fernanda.lima@email.com','62991110006');

INSERT INTO pedidos.endereco (cliente_id, logradouro, numero, complemento, bairro, cidade, uf, cep) VALUES
 (1, 'Rua 10',               '120', 'Apto 302', 'Setor Oeste',        'Goiânia',           'GO', '74120020'),
 (2, 'Avenida T-63',         '1500', NULL,      'Setor Bueno',        'Goiânia',           'GO', '74230100'),
 (3, 'Rua Engenheiro Portela','45', 'Casa',     'Centro',             'Anápolis',          'GO', '75023085'),
 (4, 'Avenida Rio Verde',    '800', 'Qd 5 Lt 3','Vila Rosa',          'Goiânia',           'GO', '74345010'),
 (5, 'Rua 7',                '33',  NULL,       'Centro',             'Aparecida de Goiânia','GO','74905070'),
 (6, 'Avenida Goiás',        '2001', 'Sala 4',  'Setor Central',      'Goiânia',           'GO', '74063010'),
 (1, 'Rua 85',               '510', NULL,       'Setor Sul',          'Goiânia',           'GO', '74080010');

RESET ROLE;
