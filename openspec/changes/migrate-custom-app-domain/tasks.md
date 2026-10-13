## 1. Permitir origens temporárias explícitas

- [x] 1.1 Implementar `PUBLIC_APP_ORIGINS` com parsing e validação estritos de origens HTTPS exatas, sem wildcard; manter `PUBLIC_APP_ORIGIN` como origem canônica e adaptar a verificação de origem sensível. Evidência: parser restrito em `backend/app/email_delivery.py`, verificação em `backend/app/main.py` e variável disponível somente na API via Compose.
- [x] 1.2 Adicionar testes para origem canônica, domínio antigo explicitamente permitido, origem externa recusada e configuração inválida; executar validação direcionada e OpenSpec. Evidência (2026-10-13, branch `feature/migrate-custom-app-domain`): `pytest tests/test_admin_security.py tests/test_admin_origin_allowlist.py -q` → 27 passaram; `ruff check app/main.py app/email_delivery.py tests/test_admin_origin_allowlist.py` → aprovado; `docker compose -f docker/docker-compose.yml config --quiet` → aprovado; `npx -y @fission-ai/openspec@1.14.0 validate migrate-custom-app-domain --type change --strict --no-interactive` → change válida; `npx -y @fission-ai/openspec@1.14.0 validate --strict --all --no-interactive` → 96 itens aprovados, zero falhas. Permaneceram avisos preexistentes de depreciação FastAPI `on_event` e advertências SQLAlchemy em fixtures de limpeza.

## 2. Registrar inventário e obter autorização operacional

- [ ] 2.1 Atualizar o inventário somente de leitura antes da operação e confirmar o estado do proxy/host antigo, redes, portas, certificados, DNS público e checkout/serviços Markina.
- [x] 2.2 Apresentar inventário, hostname, registro A, portas/subdomínio e plano de impacto zero; aguardar aprovação explícita antes de qualquer alteração em homologação/Registro.br. A aprovação explícita do proprietário foi recebida em 2026-10-13 para o escopo completo descrito na proposta; alterações externas permanecem aguardando a janela de transição do Registro.br.

## 3. Configurar e validar domínio novo

- [ ] 3.1 Depois da transição do Registro.br, criar apenas `A markina -> 132.145.193.169`; verificar resolução nos servidores autoritativos e resolvedores públicos, sem alterar a raiz, MX ou nameservers.
- [ ] 3.2 Criar no Nginx Proxy Manager somente o host `markina.pickyourpic.com.br` apontando para `markina-homolog-nginx:80`; emitir certificado Let's Encrypt próprio e preservar o host/certificado DuckDNS.
- [ ] 3.3 Publicar a configuração de origens pelo fluxo protegido existente, usando a URL nova como canônica e permitindo explicitamente o endereço DuckDNS antigo; verificar HTTPS, certificado, roteamento, healthchecks, login, cookies, redirecionamentos, operação sensível e logs relevantes.
- [ ] 3.4 Confirmar acesso pelos dois endereços, documentar resultados reais e rollback. Manter o hostname antigo até revisão humana; não arquivar nem sincronizar a change sem revisão humana.

## Inventário somente de leitura — 2026-10-13

- Servidor `132.145.193.169`, checkout `/opt/markina-gallery`; projeto Compose `markina-gallery` em `docker/docker-compose.yml`.
- Nginx Markina publica somente `127.0.0.1:8080 -> 80`; web `3000`, API `8000`, PostgreSQL e Redis são internos ao Compose.
- Markina está conectado à rede externa compartilhada `npm-network`, com alias existente `markina-homolog-nginx`. Nginx Proxy Manager é compartilhado e escuta nas portas públicas `80`, `81` e `443`; não alterar seu container/rede/portas.
- Outros containers/projetos estão no host (ClearBudget e Portainer); a porta pública `3000` também pertence ao frontend ClearBudget. Firewall UFW aparece inativo. Nada disso deve ser alterado nesta mudança.
- `markina-homolog.duckdns.org` resolve para `132.145.193.169`, responde HTTP 200 por HTTPS e apresenta certificado Let's Encrypt válido até 2026-11-24. A origem canônica atual da API é `https://markina-homolog.duckdns.org`.
- `pickyourpic.com.br` está publicado no Registro.br, usa DNS automático `a.auto.dns.br`/`b.auto.dns.br` e não tinha resposta A pública durante a inspeção. O subdomínio `markina.pickyourpic.com.br` não resolvia.
- No painel do Registro.br, o modo DNS avançado foi confirmado; o domínio aparece em transição com liberação estimada em cerca de 2h05. Nenhum registro foi salvo. A zona raiz/MX permanecem sem configuração de aplicação.
- O hostname DuckDNS é roteado pelo proxy compartilhado para o projeto Markina. O inventário dos metadados do host virtual deverá ser repetido de forma não sensível imediatamente antes da criação do novo host.
- A árvore Git já tinha muitas modificações locais não relacionadas antes desta change; elas permanecem intocadas.

## Bloqueios atuais

- O painel do Registro.br informa janela de transição de aproximadamente duas horas depois de selecionar o modo avançado; a configuração da zona ainda não está liberada.
- A inspeção visual autenticada de login e funcionalidades essenciais depende de sessão humana válida no navegador e será executada quando o novo HTTPS estiver ativo, sem compartilhar credenciais.

## Atualização após aprovação e implementação local — 2026-10-13

- O proprietário aprovou explicitamente o escopo da change, o inventário e o plano de impacto zero em 2026-10-13.
- A implementação local da allowlist adicional passou os testes direcionados, Ruff, validação estrutural do Compose e validação OpenSpec estrita da change.
- Nenhum código foi implantado e nenhum arquivo `.env`, registro DNS, host virtual ou certificado foi alterado até este registro.
- A suíte completa `test_admin_security.py` foi executada também no worktree limpo baseado em `develop`: 27 testes passaram em 135,61s; foram emitidos 27 avisos de depreciação SQLAlchemy/FastAPI sem falhas.
