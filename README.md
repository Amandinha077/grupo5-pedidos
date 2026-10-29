# Grupo 5 — Sistema de Pedidos
### Integração de Aplicações por Banco de Dados (PostgreSQL) — UNIFAN

- **Consome:** Grupo 3 — Sistema de Produtos (`public.vw_integracao_produtos`)
- **Produz para:** Grupo 7 — Sistema de Entregas (`api_entregas.vw_integracao_pedidos` e `vw_integracao_itens_pedido`)
- **Tecnologia:** Python 3 + psycopg2 + PostgreSQL 16

## Estrutura do projeto

```
grupo5-pedidos/
├── main.py                      menu (CRUD + integração)  |  python main.py integrar
├── setup_ambiente.py            cria tudo com um comando
├── config.ini                   conexões (Grupo 5, Grupo 3, admin)
├── requirements.txt
├── app/
│   ├── conexao.py               conexão e autenticação nos dois bancos
│   ├── validacao.py             validação + transformação (contrato G3 -> G5)
│   ├── integracao_produtos.py   processo completo de integração
│   ├── crud.py                  CRUD das 6 tabelas
│   ├── consultas.py             histórico, erros e visão do Grupo 7
│   └── demonstracoes.py         opções 12 (falha de transação) e 13 (concorrência)
├── sql/
│   ├── 00_criar_bancos_usuarios.sql
│   ├── 01_schema_grupo5.sql
│   ├── 02_estrutura_integracao_grupo7.sql
│   ├── 03_dados_teste_clientes.sql
│   ├── 04_dados_teste_pedidos.sql      (rodar depois da 1ª integração)
│   └── 99_remover_tudo.sql
├── simulacao_grupo3/            banco do Grupo 3 "de mentira" para testar e ensaiar
│   ├── 10_grupo3_banco_usuarios.sql
│   ├── 11_grupo3_estrutura.sql
│   ├── 20_provocar_problemas.sql
│   ├── 21_corrigir_problemas.sql
│   ├── 22_alterar_produtos.sql
│   ├── 23_quebrar_estrutura.sql / 24_restaurar_estrutura.sql
│   ├── 25_dados_inconsistentes.sql / 26_corrigir_inconsistentes.sql
│   ├── 27_remover_permissao.sql / 28_devolver_permissao.sql
│   ├── 29_excluir_produto.sql
│   ├── 30_categoria_inexistente.sql / 31_corrigir_categoria.sql
│   └── 99_remover_grupo3_simulado.sql
├── config/acesso_remoto_postgresql.txt
├── docs/                        contratos, DER, relatório técnico, respostas
└── relatorios/                  relatório .txt de cada execução
```

## Instalação

1. Instale o PostgreSQL 16 e o Python 3.10+.
2. No terminal, dentro da pasta do projeto:
   ```
   pip install -r requirements.txt
   ```
3. Abra o `config.ini` e coloque a senha do seu usuário `postgres` na seção `[admin]`.
4. Crie tudo:
   ```
   python setup_ambiente.py
   ```
   Isso cria o banco do Grupo 5, os usuários e permissões, as views para o Grupo 7, um Grupo 3 simulado, roda a primeira integração e cria pedidos de teste.
   Para recomeçar do zero: `python setup_ambiente.py --resetar` (apaga só o Grupo 5 e o Grupo 3 **simulado**)
5. Rode o sistema:
   ```
   python main.py
   ```

> Sem Python para o setup? Rode os `.sql` no pgAdmin nesta ordem: 00 (banco postgres), 01, 02, 03 (banco grupo5_db), 10 (postgres), 11 (grupo3_db), integração pelo menu 7, depois 04.

## Ligando com o Grupo 3 real

O `config.ini` já está com os dados que o Grupo 3 passou (banco `grupo3_db`, usuário `grupo3_app`, senha `12345678`, porta 5432). O schema fica em branco: o sistema acha sozinho onde está a `vw_integracao_produtos`.

**Na aula:**
1. Pegue o IP com o Grupo 3 e coloque em `host` na seção `[produtor_grupo3]` do `config.ini`. Se o banco deles estiver no mesmo PostgreSQL que o de vocês, deixe `localhost`.
2. Rode `python setup_ambiente.py --resetar --sem-simulacao`. O `--sem-simulacao` garante que nada do Grupo 3 é criado nem apagado.
3. Rode `python main.py` e use a opção 7.

O simulado usa o mesmo usuário e senha (`grupo3_app` / `12345678`), então quem ensaiou em casa não precisa mudar mais nada além do IP.

## Liberando o acesso para o Grupo 7

Siga `config/acesso_remoto_postgresql.txt` (listen_addresses, pg_hba.conf, firewall) e passe ao Grupo 7: IP, porta 5432, banco `grupo5_db`, usuário `grupo7_integracao` e a senha. **Troque as senhas padrão dos scripts antes da apresentação.**

## Roteiro da demonstração

| Parte | O que mostrar | Como |
|---|---|---|
| 1. Produtor | Aplicação, banco, dados e estrutura de integração | Menu 1–6 (CRUD); pgAdmin com schemas `pedidos`, `controle`, `api_entregas`; menu 11 |
| 2. Configuração | Usuário, permissões, conexão | `config.ini`; scripts 00 e 02 (GRANTs); testar `SELECT * FROM pedidos.pedido` com `grupo7_integracao` → permission denied |
| 3. Contrato | Regras principais | `docs/01_...` e `docs/02_...` |
| 4. Consumo | Executar o consumidor | Menu 7 |
| 5. Transformação | Produtor → consumidor | Mostrar a view do Grupo 3 (`id_produto`, `categoria` em texto, `unidade_medida`, `ativo`) e as tabelas `pedidos.produto` (`id_produto_origem`, `categoria_id`, `unidade`, `disponivel`) e `pedidos.categoria` |
| 6. Processamento | Dados gravados no nosso banco | `SELECT * FROM pedidos.produto` / menu 5 |
| 7. Problemas | Professor provoca um erro | Menu 7 → relatório; menu 9 (erros pendentes) |
| 8. Relatório | Resultado | Relatório na tela e em `relatorios/` ; menu 8 (histórico) |
| Reprocessamento | Corrigir e rodar de novo | Grupo 3 corrige → menu 7 → seção "REPROCESSADOS" |
| Atualização | Detectar alteração | Grupo 3 altera preço/nome → menu 7 → "REGISTROS ATUALIZADOS (antes -> depois)" |

### Ensaio com o Grupo 3 simulado

```
psql -U postgres -d grupo3_db -f simulacao_grupo3/20_provocar_problemas.sql   -> menu 7: CONCLUÍDA COM ERROS
psql -U postgres -d grupo3_db -f simulacao_grupo3/21_corrigir_problemas.sql   -> menu 7: REPROCESSADOS
psql -U postgres -d grupo3_db -f simulacao_grupo3/22_alterar_produtos.sql     -> menu 7: ATUALIZADOS (antes -> depois)
psql -U postgres -d grupo3_db -f simulacao_grupo3/23_quebrar_estrutura.sql    -> menu 7: FALHA (estrutura alterada)
psql -U postgres -d grupo3_db -f simulacao_grupo3/24_restaurar_estrutura.sql  -> volta ao normal
psql -U postgres -d grupo3_db -f simulacao_grupo3/25_dados_inconsistentes.sql -> 15.16 DADO_INCONSISTENTE
psql -U postgres -d grupo3_db -f simulacao_grupo3/26_corrigir_inconsistentes.sql
psql -U postgres -d grupo3_db -f simulacao_grupo3/27_remover_permissao.sql    -> 15.12 SEM_PERMISSAO
psql -U postgres -d grupo3_db -f simulacao_grupo3/28_devolver_permissao.sql
psql -U postgres -d grupo3_db -f simulacao_grupo3/29_excluir_produto.sql      -> 15.18 REGISTRO_REMOVIDO_ORIGEM
psql -U postgres -d grupo3_db -f simulacao_grupo3/30_categoria_inexistente.sql -> 15.15 INTEGRIDADE_REFERENCIAL
psql -U postgres -d grupo3_db -f simulacao_grupo3/31_corrigir_categoria.sql
```

- **15.11 / 15.13 (banco indisponível):** troque `port = 5432` por `port = 5999` em `[produtor_grupo3]` no `config.ini` e rode a opção 7. Depois volte para 5432.
- **15.14 (registro reenviado):** rode a opção 7 duas vezes seguidas.
- **15.19 (transação):** opção 12 do menu.
- **15.20 (concorrência):** opção 13 do menu (teste com 8 s e com 3 s).

O passo a passo de cada problema, com o que mostrar e o que falar, está em `docs/Roteiro_Problemas_Integracao.docx`.

## Onde está cada conceito no código

| Conceito | Onde |
|---|---|
| Conexão / autenticação | `app/conexao.py` |
| Verificação de estrutura (contrato) | `_consultar_produtor()` em `integracao_produtos.py` |
| Validação e transformação | `app/validacao.py` |
| Duplicidade | `Counter` em `executar()` + UNIQUE `id_produto_origem` |
| Integridade referencial | categoria em `validacao.py` + upsert da categoria em `_gravar_registro()` |
| COMMIT / ROLLBACK | `executar()` — uma transação por registro |
| Locks / concorrência | `pg_try_advisory_lock` e `SELECT ... FOR UPDATE` |
| Registro de execução e erros | tabelas `controle.integracao` e `controle.erro_integracao` |
| Reprocessamento | `UPDATE controle.erro_integracao SET resolvido = TRUE` |
| Atualização | comparação campo a campo em `_gravar_registro()` |
| Produtor / permissões mínimas | `sql/02_estrutura_integracao_grupo7.sql` |

**Integrantes:** Amanda Carmo dos Santos · Ana Carolina Carmo dos Santos · Nathalia Marcelino Lima
