# Relatório Técnico — Grupo 5: Sistema de Pedidos

**Disciplina:** Integração de Aplicações — UNIFAN
**Trabalho:** Integração de Aplicações por Banco de Dados (PostgreSQL)
**Integrantes:** Amanda Carmo dos Santos, Ana Carolina Carmo dos Santos, Nathalia Marcelino Lima

## 1. Visão geral

O Grupo 5 desenvolve o Sistema de Pedidos e ocupa duas posições na cadeia de integração:

- **Consumidor** do Grupo 3 (Sistema de Produtos): lê o catálogo de produtos e grava no nosso banco.
- **Produtor** para o Grupo 7 (Sistema de Entregas): publica os pedidos confirmados/cancelados com endereço e itens.

| Etapa | Banco | Estrutura | Usuário que acessa |
|---|---|---|---|
| Origem | grupo3_db | public.vw_integracao_produtos | grupo3_app (só SELECT) |
| Nosso sistema | grupo5_db | pedidos.categoria, produto, cliente, endereco, pedido, item_pedido; controle.integracao, erro_integracao | grupo5_app |
| Publicação | grupo5_db | api_entregas.vw_integracao_pedidos e vw_integracao_itens_pedido | grupo7_integracao (só SELECT) |
| Destino | grupo7_db | tabelas do Sistema de Entregas | Grupo 7 |

## 2. Tecnologias

| Item | Escolha | Motivo |
|---|---|---|
| SGBD | PostgreSQL 16 | Exigido no trabalho |
| Linguagem | Python 3 | Código curto e fácil de explicar na apresentação |
| Driver | psycopg2 | Driver oficial mais usado do PostgreSQL em Python; dá controle total de COMMIT/ROLLBACK |
| Interface | Menu no terminal | O foco do trabalho é a integração, não a tela |

## 3. Banco de dados

Banco próprio `grupo5_db`, com três schemas (`pedidos`, `controle` e `api_entregas`), seis tabelas de negócio com CRUD, três tabelas de controle e duas views de integração. Detalhes em `03_modelo_banco.md`.

Regras de integridade ficam no próprio banco (CHECK, UNIQUE, FOREIGN KEY e triggers). Assim, mesmo que alguém grave direto pelo pgAdmin, os dados continuam consistentes — e o Grupo 7 recebe dados já validados.

## 4. Estratégia de integração (consumidor do Grupo 3)

O processo está em `app/integracao_produtos.py` e segue as etapas do trabalho:

**Etapa 1 — Conexão.** A aplicação abre duas conexões: uma no nosso banco (`grupo5_app`) e outra no banco do Grupo 3 com a credencial somente leitura `grupo3_app`. A autenticação é por usuário e senha, validada pelo PostgreSQL (`pg_hba.conf`). A conexão com o produtor é aberta em modo `readonly` e com isolamento `REPEATABLE READ`, para que toda a leitura enxergue uma "foto" consistente dos dados. Há timeout de 5 segundos e até 3 tentativas, com 2 segundos de intervalo, antes de considerar o banco indisponível. Se a conexão falhar, o sistema diz o motivo: servidor fora do ar, senha errada, banco inexistente, IP bloqueado ou falta de permissão.

**Etapa 2 — Consulta.** `SELECT * FROM public.vw_integracao_produtos`. Antes de processar, o sistema confere se todas as colunas do contrato vieram (`cursor.description`). Se faltar alguma, para tudo (falha estrutural). Colunas a mais só geram aviso.

**Etapa 3 — Validação** (`app/validacao.py`). Para cada registro: obrigatoriedade, tipo, tamanho, valores permitidos (preço > 0, booleano), integridade referencial (categoria existe na origem), duplicidade (código repetido na mesma consulta) e regras de negócio (data de atualização no futuro ou versão mais antiga que a já integrada).

**Etapa 4 — Transformação.** Renomeia os campos para o nosso modelo (`id_produto → id_produto_origem`, `unidade_medida → unidade`, `ativo → disponivel`, `atualizado_em → data_atualizacao_origem`), limpa espaços, converte unidade para maiúsculas, arredonda preço para 2 casas e transforma texto vazio em NULL. A categoria vira uma linha em `pedidos.categoria` e o produto aponta para ela pela chave local.

**Etapa 5 — Processamento.** Se o código não existe localmente, faz INSERT. Se existe, compara campo a campo e faz UPDATE só quando algo mudou. Se nada mudou, conta como "sem alteração".

**Etapa 6 — Tratamento de erros.** Cada problema vira uma linha em `controle.erro_integracao` com registro, campo, tipo, descrição, valor recebido e gravidade (ERRO, AVISO ou FATAL).

**Etapa 7 — Finalização.** Atualiza `controle.integracao` com totais e status e imprime/salva o relatório em `relatorios/`.

## 5. Identificação dos registros

Usamos o código do produtor como **identificador externo**: `pedidos.produto.id_produto_origem`, com restrição UNIQUE. A chave primária local (`produto_id`) é independente, gerada pelo nosso banco. Escolhemos assim porque:

- as nossas chaves estrangeiras (item_pedido → produto) não dependem do código de outro sistema;
- o UNIQUE garante, no próprio banco, que um produto não seja integrado duas vezes;
- permite cadastrar produto local (com `id_produto_origem` nulo) se for necessário.

## 6. Transformações aplicadas

| Produtor (Grupo 3) | Consumidor (Grupo 5) | Transformação |
|---|---|---|
| id_produto | produto.id_produto_origem | inteiro (identificador externo) |
| nome | produto.nome | remove espaços extras |
| descricao | produto.descricao | vazio → NULL |
| categoria (texto) | categoria.nome e produto.categoria_id (chave local) | busca a categoria pelo nome ou cria; o produto passa a ter FK |
| preco | produto.preco | Decimal com 2 casas |
| unidade_medida | produto.unidade | maiúsculas |
| ativo | produto.disponivel | booleano (aceita t/f, s/n, 1/0) |
| atualizado_em | produto.data_atualizacao_origem | TIMESTAMPTZ (mantém o fuso) |

## 7. Transações e concorrência

- **Leitura no produtor:** uma transação `REPEATABLE READ` somente leitura, encerrada logo após o `fetchall()`.
- **Gravação no consumidor:** **uma transação por registro**. Categoria + produto + marcação de erro resolvido são gravados juntos; se der certo, `COMMIT`; se o banco recusar, `ROLLBACK` desfaz só aquele registro, que é registrado como rejeitado. Isso garante o processamento parcial: um registro ruim não derruba os outros e, se a integração cair na metade, o que foi gravado está correto e completo.
- **Registro da execução e dos erros:** em commits próprios, para que o log sobreviva mesmo se o processamento falhar.
- **Locks:** `pg_try_advisory_lock` impede duas integrações ao mesmo tempo (se alguém clicar duas vezes, a segunda é recusada). `SELECT ... FOR UPDATE` trava a linha do produto enquanto ela é comparada e atualizada, evitando que um usuário altere o mesmo produto no meio do processo.
- **lock_timeout de 5 s:** se outro processo segurar o mesmo produto, a integração espera no máximo 5 segundos. Se ele liberar antes, a integração grava normalmente (o relatório mostra quanto tempo esperou). Se não liberar, aquele registro é desfeito com ROLLBACK, registrado como `REGISTRO_BLOQUEADO` e reprocessado na próxima execução, sem travar o resto.
- **Por que não uma transação única para tudo?** Com uma transação só, um único registro ruim ou uma queda no fim desfaria todos os outros, e as linhas ficariam travadas durante a integração inteira. A transação por registro mantém o banco sempre consistente e permite processamento parcial e reprocessamento.

As opções 12 e 13 do menu demonstram, respectivamente, uma falha no meio da integração (COMMIT/ROLLBACK) e dois processos disputando o mesmo registro.

## 8. Tratamento de erros

| Situação | Comportamento |
|---|---|
| Campo obrigatório nulo, tipo errado, valor fora da regra | Registro rejeitado, erro gravado, integração continua |
| Categoria nula/vazia (produto sem categoria ou com categoria inexistente na origem) | Registro rejeitado (`INTEGRIDADE_REFERENCIAL`) |
| atualizado_em no futuro, ou versão mais antiga que a já integrada | Registro rejeitado (`DADO_INCONSISTENTE`) |
| Registro travado por outro processo por mais de 5 s | ROLLBACK do registro (`REGISTRO_BLOQUEADO`), reprocessado depois |
| Código duplicado na view | Todas as ocorrências rejeitadas (`REGISTRO_DUPLICADO`); o produto já gravado fica como estava |
| Produto sumiu da origem | Não é apagado (pode estar em pedidos); vira `disponivel = FALSE` com AVISO |
| Banco do Grupo 3 fora do ar | 3 tentativas; depois status `FALHA` (`BANCO_INDISPONIVEL`), nada é gravado |
| Senha errada, banco inexistente, IP bloqueado | Status `FALHA` com a causa (`AUTENTICACAO_FALHOU`, `BANCO_INEXISTENTE`, `ACESSO_BLOQUEADO`) |
| Usuário sem permissão | Status `FALHA` (`SEM_PERMISSAO`) com o GRANT que está faltando |
| View inexistente, coluna renomeada, sem permissão | Status `FALHA`, nada é gravado, erro FATAL explicando o motivo |
| Erro ao gravar no nosso banco | ROLLBACK do registro, erro `ERRO_BANCO_CONSUMIDOR` |

## 9. Problemas da demonstração (itens 15.11 a 15.20)

As decisões para cada problema estão na seção 8 do contrato Grupo 3 → Grupo 5. O roteiro de demonstração, com o que mostrar e o que explicar em cada caso, está no documento *Roteiro dos Problemas de Integração*.

## 10. Reprocessamento e atualização

Cada execução lê a view inteira. Quando o Grupo 3 corrige um registro que antes foi rejeitado, ele passa na validação, é gravado, e os erros antigos daquele código são marcados `resolvido = TRUE`, com a execução que resolveu. O relatório lista esses códigos em "REPROCESSADOS".

Para atualização, o sistema compara os campos atuais com os recebidos e mostra no relatório o "antes → depois" (ex.: `preco: 27.90 → 29.90`). Não dependemos só do `atualizado_em` do produtor porque uma mudança no nome da categoria não muda a data do produto — a comparação campo a campo pega os dois casos.

## 11. Papel de produtor (Grupo 7)

Publicamos duas views no schema `api_entregas`. O Grupo 7 recebe um usuário próprio com permissão mínima (CONNECT, USAGE no schema e SELECT nas views) e não tem acesso às nossas tabelas. A view funciona como uma camada de proteção: se mudarmos o modelo interno, ajustamos a view e o contrato continua o mesmo. Só publicamos pedidos CONFIRMADOS e CANCELADOS; os ABERTOS ainda podem mudar. Alterações na estrutura são registradas em `controle.historico_contrato`.

## 12. Decisões técnicas resumidas

1. View em vez de tabela para integração (desacopla do modelo interno e permite permissão só de leitura).
2. Identificador externo com UNIQUE separado da chave primária local.
3. Commit por registro (processamento parcial) e falha total para problemas estruturais.
4. Duplicados: rejeitar todas as ocorrências em vez de escolher uma.
5. Nunca apagar produto vindo da origem; apenas inativar.
6. Preço congelado no item do pedido.
7. Regras de integridade no banco, não só na aplicação.

## 13. Conclusão

A integração por banco de dados é simples de montar e rápida, mas deixa o consumidor dependente de detalhes do produtor (nomes de colunas, tipos, permissões, disponibilidade). O contrato, a view, a verificação de estrutura e o registro de erros reduzem esse risco, mas não eliminam o acoplamento — em cenários com muitos sistemas ou mudanças frequentes, uma API ou mensageria seria mais adequada.
