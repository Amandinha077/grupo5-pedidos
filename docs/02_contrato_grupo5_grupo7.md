# Contrato de Integração por Banco de Dados — Grupo 5 → Grupo 7

> Versão 1.0 — elaborado em conjunto pelo Grupo 5 (Sistema de Pedidos) e pelo Grupo 7 (Sistema de Entregas).

## 1. Identificação

| Item | Definição |
|---|---|
| Sistema produtor | Grupo 5 — Sistema de Pedidos |
| Sistema consumidor | Grupo 7 — Sistema de Entregas |
| Banco produtor | `grupo5_db` (PostgreSQL) |
| Banco consumidor | `grupo7_db` (PostgreSQL) |
| Finalidade | Informar ao Sistema de Entregas quais pedidos estão prontos para entrega (confirmados) ou foram cancelados, com cliente, endereço, valor e itens. |
| Frequência | Sob demanda pelo Grupo 7; sugestão em produção: a cada 30 minutos. |
| Mecanismo | Duas views no schema exclusivo `api_entregas` |
| Responsável pela estrutura | Grupo 5. Alterações são avisadas ao Grupo 7 e registradas em `controle.historico_contrato`. |
| Credencial de acesso | Usuário `grupo7_integracao` (somente leitura). A senha é entregue ao Grupo 7 em particular. |

## 2. Estruturas disponibilizadas

| Estrutura | Finalidade | Chave |
|---|---|---|
| `api_entregas.vw_integracao_pedidos` | Um registro por pedido confirmado ou cancelado | `codigo_pedido` |
| `api_entregas.vw_integracao_itens_pedido` | Itens dos pedidos publicados na view acima | `codigo_item` |

Pedidos com status `ABERTO` **não** aparecem, porque ainda podem mudar.

## 3. Campos — `vw_integracao_pedidos`

| Campo | Tipo | Tamanho | Obrigatório | Nulo? | Regra | Exemplo |
|----------------|-----------|-------|------|------|-------------------------|----------------|
| codigo_pedido | INTEGER | — | Sim | Não | Identificador único do pedido no Grupo 5 | 1 |
| data_pedido | TIMESTAMP | — | Sim | Não | Data/hora em que o pedido foi criado | 2026-10-20 14:00:00 |
| status_pedido | VARCHAR | 15 | Sim | Não | `CONFIRMADO` ou `CANCELADO` | CONFIRMADO |
| codigo_cliente | INTEGER | — | Sim | Não | Identificador do cliente no Grupo 5 | 1 |
| nome_cliente | VARCHAR | 120 | Sim | Não | Não vazio | João Silva |
| telefone_cliente | VARCHAR | 20 | Não | Sim | Somente números | 62991110001 |
| logradouro | VARCHAR | 150 | Sim | Não | — | Rua 10 |
| numero | VARCHAR | 10 | Sim | Não | — | 120 |
| complemento | VARCHAR | 60 | Não | Sim | — | Apto 302 |
| bairro | VARCHAR | 80 | Sim | Não | — | Setor Oeste |
| cidade | VARCHAR | 80 | Sim | Não | — | Goiânia |
| uf | CHAR | 2 | Sim | Não | Duas letras maiúsculas | GO |
| cep | VARCHAR | 8 | Sim | Não | 8 dígitos, sem traço | 74120020 |
| quantidade_itens | INTEGER | — | Sim | Não | ≥ 1 | 2 |
| valor_total | NUMERIC | 12,2 | Sim | Não | > 0 | 64.29 |
| data_atualizacao | TIMESTAMP | — | Sim | Não | Maior data entre pedido, cliente e endereço | 2026-10-20 14:05:00 |

## 4. Campos — `vw_integracao_itens_pedido`

| Campo | Tipo | Tamanho | Obrigatório | Nulo? | Regra | Exemplo |
|----------------|-----------|-------|------|------|-------------------------|----------------|
| codigo_item | INTEGER | — | Sim | Não | Identificador único do item | 1 |
| codigo_pedido | INTEGER | — | Sim | Não | Deve existir em `vw_integracao_pedidos` | 1 |
| codigo_produto | INTEGER | — | Não | Sim | `id_produto` do Sistema de Produtos (Grupo 3); nulo só para produto cadastrado localmente | 101 |
| nome_produto | VARCHAR | 120 | Sim | Não | — | Arroz Tipo 1 5kg |
| quantidade | NUMERIC | 10,3 | Sim | Não | > 0 | 2.000 |
| unidade | VARCHAR | 20 | Sim | Não | Unidade de comercialização (ex.: UN, KG, L) | UN |
| preco_unitario | NUMERIC | 12,2 | Sim | Não | ≥ 0 | 27.90 |
| subtotal | NUMERIC | 12,2 | Sim | Não | quantidade × preço | 55.80 |
| data_atualizacao | TIMESTAMP | — | Sim | Não | Última alteração do item | 2026-10-20 14:05:00 |

## 5. Regras de negócio

**Identificação.** O Grupo 7 deve guardar `codigo_pedido` como identificador externo (ex.: `id_pedido_origem` com `UNIQUE`) para saber se o pedido já foi integrado.

**Atualização.** Sempre que o pedido, o cliente ou o endereço mudar, `data_atualizacao` muda (triggers no banco do Grupo 5). O Grupo 7 pode comparar essa data com a que guardou para saber o que precisa atualizar.

**Cancelamento.** Um pedido cancelado continua na view com `status_pedido = 'CANCELADO'`. O Grupo 7 deve cancelar a entrega correspondente. Pedidos não são apagados.

**Relacionamento.** Todo item pertence a um pedido presente em `vw_integracao_pedidos`. Item cujo pedido não está na view de pedidos deve ser rejeitado pelo Grupo 7.

**Duplicidade.** As duas views não repetem chaves (`codigo_pedido` e `codigo_item` vêm de chaves primárias).

**Valores nulos.** Apenas `telefone_cliente`, `complemento` e `codigo_produto` podem vir nulos.

**Garantias do produtor.** As regras de valores (CPF, CEP, UF, preço, quantidade) são garantidas por `CHECK` e triggers no banco do Grupo 5, então os dados já saem validados.

## 6. Acesso e permissões (responsabilidade do Grupo 5)

```sql
CREATE ROLE grupo7_integracao LOGIN PASSWORD '********';
GRANT CONNECT ON DATABASE grupo5_db TO grupo7_integracao;
GRANT USAGE  ON SCHEMA api_entregas TO grupo7_integracao;
GRANT SELECT ON api_entregas.vw_integracao_pedidos      TO grupo7_integracao;
GRANT SELECT ON api_entregas.vw_integracao_itens_pedido TO grupo7_integracao;
```

O usuário do Grupo 7 não tem acesso às tabelas reais (`schema pedidos`) nem pode alterar nada. Testado:

```
SELECT * FROM pedidos.pedido;                      -> ERROR: permission denied for schema pedidos
DELETE FROM api_entregas.vw_integracao_pedidos;    -> ERROR: cannot delete from view
```

## 7. Dados de conexão (preencher no dia)

| Item | Valor |
|---|---|
| Host | IP da máquina do Grupo 5: ____________ |
| Porta | 5432 |
| Banco | grupo5_db |
| Usuário | grupo7_integracao |
| Senha | (entregue em particular) |

## 8. Alterações no contrato

| Versão | Data | Alteração |
|---|---|---|
| 1.0 | 10/2026 | Versão inicial (registrada em `controle.historico_contrato`) |

**Grupo 5 (produtor):** Amanda Carmo dos Santos, Ana Carolina Carmo dos Santos, Nathalia Marcelino Lima

**Grupo 7 (consumidor):** ______________________________
