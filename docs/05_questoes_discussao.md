# Respostas às Questões para Discussão — Grupo 5

**1. Quais foram os principais problemas encontrados durante a integração?**
Nos testes apareceram: preço negativo e nulo, nome vazio, produto apontando para categoria que não existe, unidade fora da lista combinada, o mesmo produto vindo duas vezes na view, produto apagado na origem, coluna renomeada pelo produtor, perda de permissão e banco fora do ar. Todos ficaram registrados em `controle.erro_integracao`.

**2. Quais problemas poderiam ter sido evitados por um contrato mais detalhado?**
A lista de unidades permitidas, a regra de "não apagar produto, só inativar", a garantia de que o código não se repete na view e o aviso prévio antes de mudar nome de coluna. Quando isso está escrito no contrato, o produtor sabe o que não pode fazer e o consumidor sabe o que esperar.

**3. Quais são os riscos de uma aplicação acessar diretamente o banco de outra?**
Ela fica dependente da estrutura interna do outro sistema; qualquer mudança de tabela pode quebrar a integração. Também há risco de segurança (credencial com permissão demais), de desempenho (consultas pesadas no banco de produção do outro) e de pular regras de negócio que só existem na aplicação do produtor.

**4. O que acontece se o produtor alterar uma tabela usada pelo consumidor?**
Se a alteração afetar a view, a consulta quebra ou volta com colunas diferentes. No nosso sistema isso é detectado antes de processar: a integração para, nada é gravado e fica um erro FATAL `ESTRUTURA_ALTERADA` dizendo qual coluna faltou. Se a alteração for só na tabela interna e o produtor ajustar a view, o consumidor nem percebe — essa é a vantagem de usar view.

**5. Como o consumidor identifica se um registro já foi integrado?**
Pelo identificador externo: o código do produto no Grupo 3 é gravado em `id_produto_origem`, com UNIQUE. Se já existe uma linha com aquele código, o produto já foi integrado e passa para a etapa de comparação/atualização.

**6. Qual estratégia foi usada para registros duplicados?**
Dois níveis. Duplicado dentro da mesma consulta (mesmo código duas vezes na view): rejeitamos todas as ocorrências, porque não dá para saber qual está certa, e o produto que já estava gravado continua igual. Duplicado entre execuções (produto que já existe aqui): não é erro, vira atualização ou "sem alteração", e o UNIQUE no banco impede inserir duas vezes.

**7. Como foram tratados os problemas de chave estrangeira?**
O produto depende da categoria. O Grupo 3 manda a categoria como texto; se ela vier nula ou vazia (produto sem categoria ou apontando para uma categoria que não existe lá), o produto é rejeitado. Quando é válida, a categoria é gravada (ou encontrada pelo nome) antes do produto, na mesma transação, e o produto passa a apontar para a chave local dela. No nosso lado, produto que sumiu da origem não é apagado, porque itens de pedido apontam para ele.

**8. Quando deve ser utilizado COMMIT?**
Quando um conjunto de operações que precisa ficar junto terminou com sucesso. No nosso caso, depois de gravar categoria + produto de um registro, e depois de gravar o log de cada erro e o resumo da execução.

**9. Em quais situações um ROLLBACK é necessário?**
Quando alguma operação da transação falha e o que foi feito até ali não pode ficar pela metade. Exemplo: a categoria foi gravada, mas o produto foi recusado pelo banco; o ROLLBACK desfaz a categoria também, e o registro vai para a lista de rejeitados.

**10. O que pode acontecer se a integração falhar depois de metade dos registros?**
Sem cuidado, poderiam sobrar dados incompletos ou inconsistentes. Como fazemos commit por registro, o que já foi gravado está completo e correto, e o que faltou é simplesmente lido de novo na próxima execução (a integração é idempotente: rodar de novo não duplica nada). A execução fica com status FALHA no histórico para análise.

**11. Qual a importância das permissões de acesso ao banco produtor?**
Garantem que o consumidor só veja o que foi combinado e não consiga estragar nada. Se a credencial vazar ou a aplicação tiver um bug, o estrago fica limitado a uma leitura. É o princípio do menor privilégio.

**12. O consumidor deveria poder alterar os dados do produtor? Justifique.**
Não. O produtor é o dono do dado e responsável pelas regras dele. Se o consumidor encontra algo errado, ele registra o erro e avisa; quem corrige é o produtor. Se o consumidor pudesse alterar, ninguém saberia mais qual é a versão correta, e um erro do consumidor afetaria todos os outros sistemas que usam aquele banco.

**13. Diferença entre usar a tabela diretamente e usar uma view?**
A view expõe só as colunas e linhas combinadas, com nomes próprios para a integração, e esconde o modelo interno. O produtor pode reorganizar as tabelas e manter a view igual. Também permite dar permissão só na view, sem acesso às tabelas. Usando a tabela direto, qualquer mudança interna quebra o consumidor e o consumidor enxerga mais do que precisa.

**14. O que acontece se o banco produtor ficar indisponível?**
A conexão falha (com timeout de 5 s), a execução é registrada como FALHA com erro `BANCO_INDISPONIVEL` e nada é alterado no nosso banco. O sistema de pedidos continua funcionando com os últimos produtos integrados, e na próxima execução tudo é sincronizado.

**15. Como o consumidor deve reagir a uma alteração na estrutura do produtor?**
Detectar antes de processar, parar sem gravar nada, registrar exatamente o que mudou e avisar o produtor. Depois, os dois grupos atualizam o contrato e, se for o caso, o consumidor ajusta o código. Colunas novas que não estão no contrato podem ser ignoradas sem parar a integração.

**16. Vantagens da integração por banco de dados?**
É simples e rápida de implementar, usa uma tecnologia que todo mundo já conhece (SQL), funciona bem para grandes volumes, o próprio banco cuida de autenticação, permissões e transações, e não precisa de nenhum servidor intermediário.

**17. Principais limitações?**
Forte acoplamento à estrutura do outro sistema, exposição do banco na rede, dificuldade de aplicar regras de negócio do produtor, carga extra no banco de produção, dependência de mesmo tipo de SGBD/driver e dificuldade de versionar mudanças.

**18. Como essa integração aumenta o acoplamento?**
O consumidor passa a depender do nome do banco, schema, view, colunas, tipos, permissões e disponibilidade do servidor do produtor. Qualquer mudança de um lado exige mudança coordenada do outro. A view diminui, mas não elimina, essa dependência.

**19. Quando uma API seria mais adequada?**
Quando o produtor precisa aplicar regras de negócio antes de entregar o dado, quando há muitos consumidores diferentes, quando os sistemas estão em redes diferentes ou na internet, quando é preciso versionar o contrato (v1, v2) ou quando não se quer expor o banco.

**20. Quando mensageria seria mais adequada?**
Quando a informação precisa chegar quase em tempo real (ex.: "pedido confirmado" avisando entregas na hora), quando o consumidor pode estar fora do ar e não pode perder eventos, quando vários sistemas precisam reagir ao mesmo evento ou quando se quer desacoplar totalmente o tempo de produtor e consumidor (fila com RabbitMQ, Kafka etc.).
