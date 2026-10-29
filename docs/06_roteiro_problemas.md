# Roteiro dos Problemas de Integração (15.11 a 15.20)

**Grupo 5 — Sistema de Pedidos (consumidor do Grupo 3)**

Como usar este roteiro: na apresentação, o professor provoca o problema no banco do Grupo 3 (ou pede para vocês provocarem), vocês rodam a **opção 7** do menu e explicam o relatório. Para ensaiar em casa, cada item mostra qual script do Grupo 3 simulado reproduz o problema.

Depois de cada problema, rode a opção 9 (erros pendentes) e a opção 8 (histórico) para mostrar que ficou tudo registrado.

---

## 15.11 Falha de conexão

**O que acontece:** o consumidor não consegue se conectar no banco do Grupo 3.

**O que o sistema faz:** tenta 3 vezes, com 2 segundos entre as tentativas. Se não conseguir, para, não mexe em nada do nosso banco e registra a execução com status FALHA. A mensagem diz exatamente a causa:

| Causa | Código no relatório |
|---|---|
| Servidor desligado ou IP errado | BANCO_INDISPONIVEL |
| Usuário ou senha errados | AUTENTICACAO_FALHOU |
| Nome do banco errado | BANCO_INEXISTENTE |
| IP da nossa máquina não liberado no pg_hba.conf | ACESSO_BLOQUEADO |

**Como mostrar:** opção 7 depois que o Grupo 3 desligar o PostgreSQL deles. No ensaio, troque `port = 5432` por `port = 5999` na seção `[produtor_grupo3]` do `config.ini`, ou coloque uma senha errada.

**O que falar:** "O sistema não trava nem quebra. Ele tenta de novo, explica o motivo e registra a ocorrência na tabela controle.erro_integracao. Como nada foi gravado pela metade, é só rodar de novo quando o banco voltar."

## 15.12 Usuário sem permissão

**O que acontece:** o usuário `grupo3_app` perde alguma permissão.

**O que o sistema faz:** identifica qual permissão está faltando e mostra o comando que resolve:

- sem CONNECT no banco: `GRANT CONNECT ON DATABASE grupo3_db TO grupo3_app;`
- sem USAGE no schema: `GRANT USAGE ON SCHEMA public TO grupo3_app;`
- sem SELECT na view: `GRANT SELECT ON public.vw_integracao_produtos TO grupo3_app;`

Se o problema for no **nosso** usuário (`grupo5_app` sem permissão de gravar no nosso banco), aparece `SEM_PERMISSAO_CONSUMIDOR` com o GRANT correspondente.

**Como mostrar:** o Grupo 3 executa `REVOKE SELECT ON public.vw_integracao_produtos FROM grupo3_app;` e vocês rodam a opção 7. No ensaio: script `27_remover_permissao.sql` e depois `28_devolver_permissao.sql`.

**O que falar:** "A autenticação deu certo, o PostgreSQL aceitou o usuário e a senha, mas a autorização falhou: o usuário não tem o GRANT necessário. Quem corrige é o Grupo 3, que é o dono do banco. A gente só lê a view e não tem permissão para alterar nada lá, e isso é proposital: é o princípio do menor privilégio."

## 15.13 Banco indisponível

**O que acontece:** o banco do Grupo 3 fica fora do ar por um tempo.

**O que o sistema faz:** o mesmo da 15.11 (3 tentativas, depois FALHA). Enquanto isso, o Sistema de Pedidos continua funcionando normalmente com os últimos produtos que foram integrados: dá para cadastrar cliente, fazer pedido etc.

**Como mostrar:** com o banco do Grupo 3 desligado, rode a opção 7 (vai dar FALHA). Depois mostre a opção 3 (Pedidos) funcionando. Quando o banco voltar, rode a opção 7 de novo: STATUS CONCLUÍDA.

**O que falar:** "A integração é desacoplada do uso do sistema. Se o produtor cai, a gente só fica com os produtos da última sincronização. Como cada execução lê a view inteira, a próxima recupera tudo o que mudou nesse meio-tempo."

## 15.14 Violação de chave primária (registro reenviado)

**O que acontece:** um produto que já foi integrado chega de novo.

**Decisão (está no contrato):** **atualiza ou ignora**, nunca insere de novo.

- Se algum campo mudou, atualiza.
- Se nada mudou, ignora e conta como "Sem alteração".
- Se o mesmo `id_produto` aparecer duas vezes **na mesma consulta**, rejeita as duas (`REGISTRO_DUPLICADO`), porque não dá para saber qual é a certa.

**Como mostrar:** rode a opção 7 duas vezes seguidas. Na segunda, aparece "Inseridos: 0" e "Sem alteração: 15". Para o duplicado, no ensaio: script `20_provocar_problemas.sql` (o produto 102 vem duas vezes).

**O que falar:** "A gente guarda o id_produto do Grupo 3 na coluna id_produto_origem, que tem restrição UNIQUE. Antes de gravar, procura por ele: se existe, compara; se não existe, insere. Mesmo que o código tentasse inserir duas vezes, o próprio banco barraria."

## 15.15 Violação de integridade referencial

**O que acontece:** um produto depende de uma categoria que não existe.

**Decisão:**

- Se a categoria vem preenchida, ela é **criada automaticamente** no nosso banco antes do produto, na mesma transação.
- Se a categoria vem nula (o produto aponta para uma categoria que não existe no Grupo 3), o produto é **rejeitado** (`INTEGRIDADE_REFERENCIAL`), fica registrado e entra sozinho quando o Grupo 3 corrigir.

**Como mostrar:** no ensaio, script `30_categoria_inexistente.sql` (o produto 301 aponta para a categoria 6, que não existe) e opção 7: produto rejeitado. Depois, `31_corrigir_categoria.sql` e opção 7: o produto 301 aparece em "REPROCESSADOS".

**O que falar:** "No nosso banco, produto tem chave estrangeira para categoria, então o pai tem que existir antes do filho. Quando o dado do pai vem junto, a gente cria; quando não vem, a gente não inventa: rejeita, registra e reprocessa depois. Do nosso lado, como produtor para o Grupo 7, a view só publica pedidos com cliente e endereço que existem, porque as chaves estrangeiras garantem isso."

## 15.16 Dados inconsistentes

**O que acontece:** o dado é válido sozinho, mas não faz sentido para o negócio.

**Regras que o sistema verifica:**

1. `atualizado_em` no futuro: o produto não pode ter sido alterado depois de agora.
2. Produto já integrado que chega com dados diferentes, mas com `atualizado_em` **mais antigo** que a versão que já temos: seria uma versão velha sobrescrevendo uma nova.

Os dois casos são rejeitados como `DADO_INCONSISTENTE` e reprocessados quando o Grupo 3 corrigir. As demais regras (preço maior que zero, campos obrigatórios) já barram o resto.

**Como mostrar:** no ensaio, script `25_dados_inconsistentes.sql` (o 104 fica com data daqui a 30 dias e o 105 com data de 2020) e opção 7. Depois, `26_corrigir_inconsistentes.sql` e opção 7: os dois aparecem em "REPROCESSADOS".

**O que falar:** "Cada campo está no formato certo, mas a combinação não faz sentido. É o mesmo caso do exemplo data_inicio maior que data_fim. Por isso a validação não é só de tipo: tem regra de negócio também."

## 15.17 Atualização de registro já integrado

**O que acontece:** o Grupo 3 altera um produto que já foi integrado.

**O que o sistema faz:** identifica o produto pelo `id_produto`, compara campo a campo (nome, descrição, categoria, preço, unidade e ativo) e só faz UPDATE se algo mudou. O relatório mostra "antes → depois".

**Como mostrar:** o Grupo 3 muda o preço ou o nome de um produto e vocês rodam a opção 7. No ensaio: `22_alterar_produtos.sql`.

**O que falar:** "Não dependemos só do atualizado_em, porque nem toda mudança altera essa data. Por exemplo, se a categoria for renomeada, a data do produto continua a mesma. A comparação campo a campo pega todos os casos e mostra exatamente o que mudou."

## 15.18 Exclusão de registro

**O que acontece:** o Grupo 3 apaga um produto que já tinha sido integrado.

**Decisão:** **registrada, não replicada**. O produto não é apagado do nosso banco, porque pode estar em pedidos antigos. Ele fica indisponível (não entra em pedido novo) e gera um aviso `REGISTRO_REMOVIDO_ORIGEM`. Se voltar a aparecer na view, é reativado.

**Como mostrar:** o Grupo 3 apaga um produto e vocês rodam a opção 7: "Inativados: 1". Depois, opção 5 (Produtos): o produto continua lá com disponível = False. No ensaio: `29_excluir_produto.sql`.

**O que falar:** "Se a gente apagasse, os pedidos antigos que têm esse produto ficariam quebrados, e o próprio banco nem deixaria, por causa da chave estrangeira. Então fazemos exclusão lógica e registramos."

## 15.19 Problema de transação

**O que acontece:** a integração cai depois de já ter gravado alguns registros.

**Estratégia:** **uma transação por registro**. Cada produto é gravado e confirmado com COMMIT. Se cair no meio:

- o que já teve COMMIT continua gravado e correto;
- o registro que estava no meio da transação é desfeito com ROLLBACK;
- os que faltaram são processados na próxima execução, sem duplicar nada.

**Como mostrar:** **opção 12** do menu. Ela pergunta quantas alterações confirmar antes da falha (padrão 2). O relatório mostra a seção "TRANSAÇÕES" com COMMIT, COMMIT, ROLLBACK e a lista dos não processados. Depois rode a opção 7 para concluir. Para ter alterações para processar, peça ao Grupo 3 para mudar alguns preços (no ensaio, `22_alterar_produtos.sql`).

**O que falar:** "COMMIT confirma de forma definitiva; ROLLBACK desfaz tudo o que a transação fez. A gente escolheu uma transação por registro, e não uma única para tudo, porque com uma só um erro no último registro desfaria os outros e as linhas ficariam travadas a integração inteira. Assim, o banco nunca fica com dado pela metade, e rodar de novo é seguro."

## 15.20 Concorrência

**O que acontece:** dois processos tentam alterar o mesmo registro ao mesmo tempo.

**Mecanismos usados:**

- **Transação + lock de linha (SELECT ... FOR UPDATE):** quando a integração vai atualizar um produto, ela trava aquela linha. Se outro processo já estiver com ela, a integração espera.
- **lock_timeout de 5 s:** a espera tem limite. Se o outro processo liberar antes, a integração grava normalmente. Se não liberar, ela desfaz só aquele registro (ROLLBACK), registra `REGISTRO_BLOQUEADO` e reprocessa na próxima.
- **Advisory lock:** impede duas integrações rodando ao mesmo tempo; a segunda é recusada.
- **Isolamento REPEATABLE READ** na leitura do Grupo 3: a integração enxerga uma "foto" consistente da view, mesmo que o Grupo 3 altere algo durante a leitura.

**Como mostrar:** **opção 13** do menu. Ela simula três processos:

- **A:** um "usuário" segura o produto 101.
- **B:** a integração, que precisa esperar.
- **C:** uma segunda integração, que é recusada.

Ela pergunta por quantos segundos o processo A segura o produto:

- **8 s** (mais que o limite): a integração B desiste daquele produto e registra REGISTRO_BLOQUEADO. Rodando a opção 7 depois, ele aparece em "REPROCESSADOS".
- **3 s** (menos que o limite): a integração B espera e grava. O relatório mostra "ESPERAS POR LOCK".

**O que falar:** "O banco controla a concorrência com locks. Quem chega primeiro trava a linha, e o segundo espera ou desiste depois do tempo limite. Assim, nenhuma alteração sobrescreve a outra sem querer (lost update), e a integração nunca fica travada para sempre."

---

## Resumo rápido

| Item | Onde aparece | Decisão |
|---|---|---|
| 15.11 / 15.13 | FATAL BANCO_INDISPONIVEL (e variantes) | 3 tentativas, FALHA registrada, nada gravado |
| 15.12 | FATAL SEM_PERMISSAO | Explica o GRANT que falta; quem corrige é o Grupo 3 |
| 15.14 | "Sem alteração" / REGISTRO_DUPLICADO | Atualiza ou ignora; duplicado na mesma consulta é rejeitado |
| 15.15 | INTEGRIDADE_REFERENCIAL | Cria a categoria se ela vier preenchida; senão rejeita e reprocessa |
| 15.16 | DADO_INCONSISTENTE | Rejeita e reprocessa |
| 15.17 | "REGISTROS ATUALIZADOS (antes -> depois)" | Comparação campo a campo |
| 15.18 | AVISO REGISTRO_REMOVIDO_ORIGEM | Exclusão lógica, não apaga |
| 15.19 | Opção 12 / TRANSACAO_INTERROMPIDA | COMMIT por registro, ROLLBACK do registro em andamento |
| 15.20 | Opção 13 / REGISTRO_BLOQUEADO / ESPERAS POR LOCK | FOR UPDATE, lock_timeout, advisory lock, REPEATABLE READ |
