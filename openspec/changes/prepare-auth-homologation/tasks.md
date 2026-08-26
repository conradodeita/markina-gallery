## 1. Inventário e aprovação

- [x] 1.1 Coletar inventário somente-leitura do servidor de homologação (containers, Compose, redes, volumes, serviços e portas) e registrar o resultado em documento técnico versionado.
- [x] 1.2 Propor porta, subdomínio, diretório e recursos exclusivos da Markina Gallery a partir do inventário e apresentar o plano de impacto zero ao proprietário para aprovação explícita.

## 2. Preparação isolada

- [x] 2.1 Atualizar o Compose, Dockerfiles e documentação para permitir a execução explícita da migration Alembic e o seed seguro do administrador, verificando que nenhum segredo é versionado.
- [x] 2.2 Criar o checklist de variáveis de homologação (banco, cookie, domínio e adaptador sandbox) e verificar que PostgreSQL e Redis não possuem portas públicas.
- [x] 2.3 Documentar o smoke test de autenticação e o rollback restrito ao projeto `markina-gallery`, verificando que não utiliza comandos globais de Docker.

## 3. Validação e gate de publicação

- [x] 3.1 Executar testes, lint, build, geração da migration e validação OpenSpec, registrando os resultados no change.
- [ ] 3.2 Após aprovação de 1.2, executar a homologação no ambiente isolado e verificar healthchecks, login de cliente, login administrativo e rollback; sem aprovação, registrar o bloqueio e não realizar mudanças externas.
- [x] 3.3 Registrar decisões, limitações e evidências de homologação no change antes de sincronizar ou arquivar qualquer spec.

## Registro de continuidade — 2026-08-25

- Inventário concluído por SSH somente-leitura e registrado em `docs/HOMOLOGACAO-AUTH-INVENTARIO-2026-08-25.md`. O servidor possui o projeto `clearbudget`, Nginx Proxy Manager e Portainer; nenhuma alteração externa foi executada.
- Gate original de 1.2 aprovado: diretório isolado e subdomínio de homologação. A revisão de entrada privada também foi aprovada: conectar somente `nginx` da Markina à `npm-network`, com alias exclusivo, e criar apenas um host novo no Nginx Proxy Manager. Não enviar senha, chave privada, token ou outro segredo pelo chat; o acesso deve estar configurado no ambiente ou ser concedido por canal seguro.
- DNS confirmado: `markina-homolog.duckdns.org` resolve para `132.145.193.169`. A proposta de porta/subdomínio foi aprovada pelo proprietário.
- Validação local concluída: backend (9 testes e Ruff), frontend (testes, lint e build), geração SQL Alembic, `docker compose ... config` e OpenSpec estrito válidos.
- Próximo dado necessário para 3.2: e-mail da conta administrativa inicial. A senha e o segredo TOTP serão gerados no servidor e não serão armazenados no Git nem enviados pelo chat.
- Homologação isolada iniciada no commit `17911c8`: migration, healthchecks, seed do administrador `conradodeita@gmail.com`, autenticação administrativa interna e desafio de cliente sandbox foram aprovados. Evidências sem segredos em `docs/HOMOLOGACAO-AUTH-RESULTADO-2026-08-25.md`.
- Revisão de arquitetura: como o Proxy Manager é um container, `127.0.0.1:8080` não é um destino válido para ele. O nginx da Markina usará somente a rede externa `npm-network`, sob o alias `markina-homolog-nginx`; nenhum recurso será conectado à rede do ClearBudget. A execução da revisão foi aprovada explicitamente pelo proprietário em 2026-08-25.
