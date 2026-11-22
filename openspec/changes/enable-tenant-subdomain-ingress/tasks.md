# Tasks

## 1. Compatibilidade e resolução de hostname

- [x] 1.1 Mapear consumidores de `tenant_hosts`, host canônico e `Host` em API, frontend, autenticação, links, notificações e workers; registrar matriz de busca e revisão em `consumer-inventory.md`.
- [x] 1.2 Implementar somente lacunas na resolução estrita do hostname, propagação de `Host` confiável e cookies host-only; verificar hostname exato, profundo, desconhecido, reservado, inativo e suspenso. **Nenhuma lacuna de runtime foi identificada**; os contratos existentes e o cookie host-only passaram nos testes focados de `tests/test_tenant_host_reservation.py` e `tests/test_tenant_hosts.py`.
- [x] 1.3 Cobrir dois tenants sintéticos em sessões, galerias, compras, URLs e workers; verificar acesso cruzado negado e ausência de fallback para o proprietário. Evidência: sessões A/B e spoof de `X-Forwarded-Host`, links canônicos por tenant, autenticação de compra entre hosts, entrega de notificação e worker após mudança de host; 21 testes direcionados passaram em 2026-11-07.

## 2. Ativação segura no console do proprietário

- [x] 2.1 Estender `PlatformAdminEvent` de forma aditiva com ações de ativação/recusa de hostname e `evidence_sha256` (64 caracteres hexadecimais); verificar DDL, append-only e downgrade que preserve eventos novos. Upgrade/downgrade, hash/contexto obrigatório, proteção dos eventos novos e cadeia real `0090→0107` passaram em PostgreSQL sintético local; ver `validation.md`.
- [x] 2.2 Implementar promoção transacional somente de `reserved` para `ready`, vinculada ao tenant/hostname persistidos, estado esperado, UUID da intenção e hash SHA-256 do relatório revisado; verificar concorrência, replay idempotente e ausência de SQL manual. Duas corridas PostgreSQL passaram: replay concorrente gera um evento e o mesmo passo TOTP não libera dois tenants, inclusive com proprietário previamente carregado na sessão.
- [x] 2.3 Testar autorização PlatformOwner, senha/TOTP de uso único, mesma origem, negativas de fotógrafo/operador, tenant cruzado, hash ausente/inválido, conflito de estado e ausência de segredo em resposta/auditoria. Testes direcionados de serviço e rota passaram em 2026-11-07.
- [x] 2.4 Integrar confirmação explícita no console, mostrando conta, estados e hostname, além do significado da atestação do relatório; verificar ação bloqueada sem hash e limpeza de atestação/credenciais ao trocar de conta. Sete testes Vitest da página passaram em 2026-11-07.

## 3. Preparação operacional DNS e Nginx Proxy Manager

- [x] 3.1 Fazer inventário somente leitura de zona/DNSSEC/origem e do Nginx Proxy Manager: versão/digest, plugin DNS-01, proteção/permissões de credenciais, hosts explícitos, upstream, redes, portas, saúde e recuperação; registrar relatório sem segredos. Concluído em `operations-inventory.md`: o token no SQLite do NPM é inadequado; a custódia/recuperação operacional real ainda não foi comprovada.
- [x] 3.2 Com autorização operacional específica, preparar apenas `*.pickyourpic.com.br` como DNS-only para a origem confirmada; verificar raiz, `markina` e registros explícitos inalterados. Concluída em 08/11/2026 após autorização expressa do proprietário: A wildcard para `132.145.193.169`, DNS-only, TTL Auto (300 s observado). Tabela antes/depois preservou os dois registros exatos; DNS público retornou A correto e AD=true para raiz, markina e hostname sintético. HEAD HTTPS: raiz 404 e markina 200, TLS válido. Ver `validation.md`. Certificado, rota e serviços não foram alterados.
- [ ] 3.3 Com autorização específica, instalar/configurar emissor separado e helper restrito, emitir wildcard Let's Encrypt via DNS-01 com token mínimo e verificar custódia/recuperação, cadeia TLS e renovação ensaiada. **Preparação local concluída:** `archive/2026-11-08-prepare-operational-wildcard-certificate-issuer` validou pacote isolado com segredos sintéticos, sem emissão pública ou instalação remota. **Bloqueada:** falta inventário/execução autorizada no Oracle, provisionamento da chave e token reais, comprovação de custódia/recuperação no host, emissão pública e ensaio de renovação; o token não deve ser guardado no SQLite do NPM.
- [ ] 3.4 Com autorização específica, configurar somente a rota wildcard Pick-your-Pic ao runtime SaaS validado; verificar precedência dos hosts existentes, propagação de `Host`, ausência de mudanças em projetos vizinhos e rollback delimitado. **Bloqueada:** não existe publicação autorizada do runtime SaaS desta change nem autorização de escrita no NPM.

## 4. Validação integrada e ativação controlada

- [ ] 4.1 Validar DNS, DNSSEC, TLS e rota com probes externos; verificar raiz e `markina` saudáveis, host desconhecido/reservado fechado e ausência de fallback ao proprietário. **Bloqueada pelas etapas 3.3–3.4**; DNS wildcard e DNSSEC foram verificados em 08/11, mas os probes dos hosts existentes são somente referência de saúde, sem comprovar TLS/rota ou isolamento de tenants.
- [ ] 4.2 Validar contrato de tenant em API/web/workers com fluxo sintético de login/OTP, sessões host-only, links de compra/galeria e tentativas A/B; registrar relatório operacional sem segredos e calcular SHA-256. **Bloqueada pelo ingresso/runtime ainda não publicados**; provas locais não substituem o relatório operacional.
- [x] 4.3 Revisar código afetado por obsolescência, duplicação e regressões; executar testes, lint, typecheck, build e `openspec validate --strict`; registrar evidências e limites. Validações focadas passaram; a execução ampliada PostgreSQL revelou um defeito preexistente do campo de estado Drive, registrado como bloqueio do release em `validation.md` e na change Drive.
- [ ] 4.4 Após autorização de publicação específica e revisão do relatório, ativar hostname individual pelo console; verificar auditoria/hash, URL canônica e recuperação sem impacto nos serviços existentes.

## Continuidade do fluxo

- Revisar artefatos e evidências antes de sincronizar specs e arquivar a change.
- A arquitetura DNS-only foi aprovada, mas essa decisão não autoriza mutação Cloudflare/NPM, publicação, migration remota ou ação no servidor; cada escrita exige inventário e autorização próprios.
