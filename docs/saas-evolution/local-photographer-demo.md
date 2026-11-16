# Demonstração local do cadastro de fotógrafo

Esta demonstração existe somente em `127.0.0.1`; usa PostgreSQL descartável e adaptadores sintéticos de e-mail/anti-bot. Não use endereço de e-mail, senha, autenticador, fotos ou dados de cliente reais. O cadastro público normal continua fechado.

## Experimentar pela UI

1. Abra `http://127.0.0.1:3039/photographer-signup` no mesmo PC.
2. Informe um nome de teste e e-mail terminado em `@example.test`, por exemplo `fotografo-teste@example.test`, e clique em **Receber código**.
3. Abra `http://127.0.0.1:3039/api/local-demo/mailbox` em outra aba; copie apenas o código do seu e-mail sintético. Volte ao cadastro e verifique-o.
4. A tela mostra a chave TOTP desta conta sintética. Adicione-a a um autenticador, crie senha de teste com pelo menos 12 caracteres e informe o código gerado.
5. Clique em **Entrar no painel**. A conta possui tenant próprio e carteira finita sem créditos. O console global do proprietário não é acessível para esse fotógrafo.

Os códigos de e-mail ficam somente na memória do processo da demonstração. O banco usa `tmpfs` e desaparece quando o container próprio é parado. O proprietário sintético criado para satisfazer a migration de créditos não tem login utilizável.

## Operação e encerramento

O runner `scripts/local_photographer_demo.py` exige explicitamente `--initialize-disposable-db-and-serve`, `APP_ENV=development`, `PUBLIC_APP_ORIGIN=http://127.0.0.1:3039`, banco PostgreSQL vazio em `127.0.0.1:15472/pyp_ui_demo` e API em `127.0.0.1:8000`. Aplica no banco descartável a revisão-base `20261026_0090`, cria o proprietário sintético antes da migration de créditos e avança até `20261113_0126`. Recusa parâmetros de query na URL, `PGSERVICE` herdado e `PGHOSTADDR` fora de `127.0.0.1` para impedir redirecionamento da conexão. O frontend é servido em `127.0.0.1:3039` com o build local atual. Para retomar a API sem alterar o banco, o modo `--serve-existing-disposable-db` exige a revisão `20261113_0126`; chaves anteriores são efêmeras, portanto uma conta criada antes da retomada pode não autenticar e deve ser tratada apenas como dado descartável de demonstração.

Ao encerrar, parar apenas os processos locais da API/Next iniciados para esta demonstração e o container exclusivo identificado no inventário local, após confirmar sua identidade. Não usar `docker compose down`, prune, comandos globais de parada ou limpeza de outros serviços. Uma nova sessão exige banco vazio e novas chaves sintéticas; contas anteriores não são restauradas.

Esta prova não valida SMTP, anti-bot, DNS/TLS, Termos, Google Drive, operações em produção ou release do SaaS.
