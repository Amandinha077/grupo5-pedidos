# Contrato de Integração por Banco de Dados — Grupo 3 → Grupo 5

> Versão 1.1 — baseada no contrato enviado pelo Grupo 3 (v1.0) e complementada pelo Grupo 5 com os itens exigidos no enunciado do trabalho (seções 9.1 a 9.4 e 10). Os campos, tipos e regras definidos pelo Grupo 3 foram mantidos sem alteração.

## 1. Identificação

| Item | Definição |
|---|---|
| Sistema produtor | Grupo 3 — Sistema de Produtos |
| Sistema consumidor | Grupo 5 — Sistema de Pedidos |
| Banco produtor | `grupo3_db` (PostgreSQL), porta 5432 |
| Banco consumidor | `grupo5_db` (PostgreSQL) |
| Finalidade | Disponibilizar ao Sistema de Pedidos o catálogo de produtos (nome, categoria, preço, unidade e situação) para que os pedidos sejam montados apenas com produtos válidos e com preço atualizado. |
| Forma de acesso | Consulta direta à view `public.vw_integracao_produtos`, somente leitura |
| Frequência | Sob demanda (menu do Sistema de Pedidos) durante os testes e a apresentação; em produção, a cada 1 hora |
| Responsável pela estrutura | Grupo 3 (produtor). Qualquer alteração na view deve ser avisada ao Grupo 5 antes de ser aplicada e gerar nova versão deste contrato |
| Responsável pelo consumo | Grupo 5 |
| Credencial de acesso | Usuário `grupo3_app`, fornecido pelo Grupo 3. Para a integração ele deve ter somente leitura na view (seção 6) |

## 2. Estrutura disponibilizada

| Item | Definição |
|---|---|
| Nome | `public.vw_integracao_produtos` |
| Tipo | View (o Grupo 5 não acessa as tabelas internas do Grupo 3) |
| Chave primária | `id_produto` — não pode se repetir na view |
| Ordenação | Não garantida; o consumidor ordena por `id_produto` |

## 3. Campos

| Campo | Tipo | Obrig. | Nulo? | Regra | Exemplo |
|-----------------|-------------------|---------|-------|-------------------------|---------------|
| id_produto | INTEGER | Sim | Não | Identificador único e permanente (inteiro > 0) | 101 |
| nome | VARCHAR(120) | Sim | Não | Texto não vazio | Arroz Tipo 1 5kg |
| descricao | VARCHAR(500) | Não | Sim | Aceita NULL ou texto vazio | Arroz agulhinha tipo 1 |
| categoria | VARCHAR(100) | Sim | Não | Texto obrigatório e não vazio | Alimentos |
| preco | NUMERIC(12,2) | Sim | Não | Maior que zero, com duas casas decimais | 27.90 |
| unidade_medida | VARCHAR(20) | Sim | Não | Unidade de comercialização (ex.: UN, KG, L) | UN |
| ativo | BOOLEAN | Sim | Não | TRUE (ativo) ou FALSE (inativo) | TRUE |
| atualizado_em | TIMESTAMPTZ | Sim | Não | Data e hora da última alteração, com fuso horário | 2026-10-20 14:30:00-03 |

## 4. Regras dos dados (definidas pelo Grupo 3)

- `id_produto`: identificador único e permanente.
- `nome`: texto não vazio.
- `descricao`: aceita NULL ou texto vazio.
- `categoria`: texto obrigatório e não vazio.
- `preco`: valor maior que zero, com duas casas decimais.
- `unidade_medida`: unidade de comercialização (ex.: UN, KG, L).
- `ativo`: TRUE (ativo) ou FALSE (inativo).
- `atualizado_em`: data e hora da última alteração, com fuso horário.

## 5. Regras da integração

**Identificação dos registros.** O `id_produto` é usado para identificar produtos já importados e evitar duplicidade. No banco do Grupo 5 ele é gravado em `pedidos.produto.id_produto_origem`, com restrição `UNIQUE`. A chave primária local (`produto_id`) é gerada pelo banco do Grupo 5 e não depende do Grupo 3.

**Atualização.** Produtos alterados são atualizados no banco consumidor. O Grupo 5 compara campo a campo (nome, descrição, categoria, preço, unidade e situação) e registra o "antes → depois" no relatório. O `atualizado_em` é armazenado em `data_atualizacao_origem`.

**Produtos inativos.** São disponibilizados pelo Grupo 3 com `ativo = FALSE`. O Grupo 5 integra normalmente, marca o produto como indisponível e impede que ele entre em novos pedidos.

**Categoria.** A categoria é enviada como texto. No Grupo 5 ela vira um registro em `pedidos.categoria` (nome único, sem diferenciar maiúsculas e minúsculas) e o produto passa a apontar para ela por chave estrangeira. Se o Grupo 3 renomear uma categoria, o Grupo 5 passa a usar o novo nome a partir da próxima integração.

**Exclusão.** O Grupo 3 deve inativar (`ativo = FALSE`) em vez de apagar. Se um produto já integrado deixar de aparecer na view, o Grupo 5 **não o exclui** (ele pode estar em pedidos): marca-o como indisponível e registra um aviso `REGISTRO_REMOVIDO_ORIGEM`.

**Registros duplicados.** A view não pode trazer o mesmo `id_produto` mais de uma vez. Se isso acontecer, o Grupo 5 rejeita todas as ocorrências daquele código (`REGISTRO_DUPLICADO`), porque não há como saber qual versão é a correta; o produto já gravado permanece como estava.

**Valores nulos e vazios.** Campos obrigatórios nulos ou vazios rejeitam o registro (`CAMPO_OBRIGATORIO`). `descricao` vazia é gravada como NULL.

**Registros inválidos.** São rejeitados e registrados em `controle.erro_integracao` para posterior correção, sem interromper os demais (processamento parcial). Depois que o Grupo 3 corrigir, o registro é integrado na próxima execução e o erro é marcado como resolvido (reprocessamento).

**Armazenamento.** Os dados importados são gravados no banco próprio do Grupo 5 (`grupo5_db`).

**Problemas estruturais.** Se a view não existir, alguma coluna do contrato faltar ou mudar de nome, o usuário perder a permissão ou o banco estiver indisponível, a integração é interrompida sem gravar nada e registrada com status `FALHA`. Colunas novas, que não estejam no contrato, são ignoradas e geram apenas aviso.

## 6. Acesso e permissões (responsabilidade do Grupo 3)

```sql
CREATE ROLE grupo3_app LOGIN PASSWORD '********';
GRANT CONNECT ON DATABASE grupo3_db TO grupo3_app;
GRANT USAGE  ON SCHEMA public TO grupo3_app;
GRANT SELECT ON public.vw_integracao_produtos TO grupo3_app;
```

O usuário do Grupo 5 não recebe INSERT, UPDATE, DELETE, ALTER ou DROP, nem acesso às tabelas internas do Grupo 3.

| Dado de conexão | Valor (preencher no dia) |
|---|---|
| Host / IP | Informado pelo Grupo 3 no dia da apresentação (o IP muda na rede do laboratório) |
| Porta | 5432 |
| Banco | grupo3_db |
| Schema | public (o Grupo 5 também localiza a view automaticamente se estiver em outro schema) |
| Usuário | grupo3_app |
| Senha | Fornecida pelo Grupo 3 |

## 7. Códigos de erro registrados pelo consumidor

| Código | Quando acontece |
|---|---|
| CAMPO_OBRIGATORIO | Campo obrigatório nulo ou vazio |
| TIPO_INVALIDO | Valor que não pode ser convertido para o tipo do contrato |
| TAMANHO_EXCEDIDO | Texto maior que o tamanho do contrato |
| VALOR_INVALIDO | Preço menor ou igual a zero |
| REGISTRO_DUPLICADO | Mesmo `id_produto` mais de uma vez na view |
| REGISTRO_REMOVIDO_ORIGEM | Produto já integrado que sumiu da view (aviso) |
| COLUNA_NAO_PREVISTA | Coluna que não está no contrato (aviso) |
| ESTRUTURA_ALTERADA / ESTRUTURA_INEXISTENTE | Quebra do contrato (fatal) |
| BANCO_INDISPONIVEL | Banco do Grupo 3 fora do ar depois de 3 tentativas (fatal) |
| AUTENTICACAO_FALHOU | Usuário ou senha recusados (fatal) |
| BANCO_INEXISTENTE / ACESSO_BLOQUEADO | Nome do banco errado ou IP não liberado no pg_hba.conf (fatal) |
| SEM_PERMISSAO | Usuário sem CONNECT, sem USAGE no schema ou sem SELECT na view (fatal, com o GRANT que falta) |
| SEM_PERMISSAO_CONSUMIDOR | Usuário do Grupo 5 sem permissão de gravar no próprio banco (fatal) |
| INTEGRIDADE_REFERENCIAL | Produto sem categoria válida (categoria inexistente no Grupo 3) |
| DADO_INCONSISTENTE | Dado válido isoladamente, mas que viola regra de negócio |
| REGISTRO_BLOQUEADO | Registro travado por outra transação por mais de 5 s (desfeito e reprocessado depois) |
| TRANSACAO_INTERROMPIDA | Processo caiu no meio da integração (fatal) |
| ERRO_BANCO_CONSUMIDOR | Outra falha ao gravar no banco do Grupo 5 (registro desfeito com ROLLBACK) |

## 8. Decisões para os problemas de integração (itens 15.11 a 15.20)

| Item | Problema | Decisão adotada |
|---|---|---|
| 15.11 | Falha de conexão | O consumidor tenta conectar 3 vezes, com 2 s de intervalo e timeout de 5 s. Se não conseguir, a execução é registrada com status `FALHA` e a mensagem diz qual é a causa (servidor fora do ar, senha errada, banco inexistente ou IP bloqueado). Nada é alterado no banco do Grupo 5. |
| 15.12 | Usuário sem permissão | O consumidor identifica qual permissão está faltando (CONNECT no banco, USAGE no schema ou SELECT na view) e registra um erro `SEM_PERMISSAO` com o comando GRANT que o Grupo 3 precisa executar. A correção é sempre do produtor; o consumidor não tem e não deve ter permissão para alterar o banco do Grupo 3. |
| 15.13 | Banco indisponível | O Sistema de Pedidos continua funcionando com os últimos produtos integrados. Quando o banco voltar, a próxima execução sincroniza tudo, porque a integração lê a view inteira a cada execução. |
| 15.14 | Violação de chave primária (registro reenviado) | **Atualiza ou ignora.** Se o `id_produto` já existe no Grupo 5 e algum campo mudou, o registro é atualizado; se nada mudou, é ignorado e contado como "sem alteração". Nunca é inserido de novo, o que é garantido pela restrição `UNIQUE` em `id_produto_origem`. Se o mesmo `id_produto` vier repetido na **mesma** consulta, todas as ocorrências são **rejeitadas** (`REGISTRO_DUPLICADO`). |
| 15.15 | Violação de integridade referencial | O produto depende da categoria. Se a categoria vem preenchida, ela é criada automaticamente no Grupo 5 antes do produto, na mesma transação. Se vem nula (produto apontando para uma categoria que não existe no Grupo 3), o produto é **rejeitado** (`INTEGRIDADE_REFERENCIAL`), fica registrado e é reprocessado automaticamente quando o Grupo 3 corrigir. |
| 15.16 | Dados inconsistentes | Regras de negócio verificadas: (1) `atualizado_em` não pode estar no futuro; (2) um produto já integrado não pode chegar com dados diferentes e `atualizado_em` **anterior** ao da versão gravada (uma versão antiga não sobrescreve uma mais nova). Esses registros são rejeitados como `DADO_INCONSISTENTE` e reprocessados quando o Grupo 3 corrigir. |
| 15.17 | Atualização de registro já integrado | Identificada pelo `id_produto` e por comparação campo a campo (nome, descrição, categoria, preço, unidade e situação). Só faz UPDATE se algo mudou, e o relatório mostra "antes → depois". |
| 15.18 | Exclusão de registro | **Registrada, não replicada.** O produto não é apagado no Grupo 5, porque pode estar em pedidos. Ele é marcado como indisponível (não entra em novos pedidos) e é registrado um aviso `REGISTRO_REMOVIDO_ORIGEM`. Se voltar à view, é reativado. |
| 15.19 | Problema de transação | **Uma transação por registro.** Cada produto é gravado e confirmado com `COMMIT`. Se ocorrer uma falha no meio, o registro em andamento é desfeito com `ROLLBACK`, o que já foi confirmado permanece correto e o restante é processado na próxima execução, sem duplicar nada. |
| 15.20 | Concorrência | O registro é travado com `SELECT ... FOR UPDATE` enquanto é comparado e gravado. Se outro processo estiver com o mesmo registro, a integração espera até 5 s (`lock_timeout`); passando disso, desfaz só aquele registro e o reprocessa depois (`REGISTRO_BLOQUEADO`). Um advisory lock impede duas integrações ao mesmo tempo, e a leitura no Grupo 3 usa isolamento `REPEATABLE READ`. |

## 9. Situação das pendências

- Campo `atualizado_em`: confirmado pelo Grupo 3 (já existe na tabela de produtos).
- Banco, porta, usuário e senha: informados pelo Grupo 3.
- Host/IP: será informado no dia da apresentação.

## 10. Histórico de versões

| Versão | Data | Alteração |
|---|---|---|
| 1.0 | 10/2026 | Contrato inicial enviado pelo Grupo 3 |
| 1.1 | 22/10/2026 | Dados de acesso do Grupo 3 e confirmação do `atualizado_em`. Complementos do Grupo 5: identificação, frequência, responsáveis, chave, exemplos, regras de exclusão, duplicidade, nulos, estrutura, permissões, códigos de erro e decisões para os problemas 15.11 a 15.20 |

**Grupo 3 (produtor):** ______________________________

**Grupo 5 (consumidor):** Amanda Carmo dos Santos, Ana Carolina Carmo dos Santos, Nathalia Marcelino Lima
