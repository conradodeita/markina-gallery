# Pacote operacional para revisão — homologação

## Estado

Tasks 1–7 concluídas localmente. Task 8.1 aguarda autorização explícita; nenhum deploy, conta adicional, grant operacional ou canal foi alterado. Este pacote é a proposta concreta para revisão, não um registro de execução.

Implementação local: `0446177c3684ff5cb5dede54202c7b3e9b0de02e`; atualização documental com develop: `91d83bcadbaf8ea2c2d3c1b3f323929ab3499930`. Esses dois commits têm o mesmo conteúdo operacional. O SHA de publicação deverá ser o head exato do PR com CI verde aprovado pelo proprietário; commits posteriores de pacote/documentação não mudam o candidato operacional. Não publicar SHA não revisado, nem assumir autorização por aprovação antiga de outra change.

## O que será entregue

Clientes/telefones, acervo, comércio/PIX/configurações, arquivos e execução assíncrona próprios de cada fotógrafo. O mesmo telefone pode existir em contas distintas sem compartilhar cadastro, seleção, compra ou histórico. Cadastro público de fotógrafo continua ausente; a publicação não cria automaticamente B ou seis clientes.

Diagnóstico agregado exige permissão explícita de operador. Migration 0071 não concede essa permissão automaticamente. A proposta de concessão abaixo se refere exclusivamente ao administrador atual do proprietário e não permite acesso comercial a outras contas.

## Inventário somente-leitura

Coleta SSH em **2026-10-01 18:56:44 UTC (15:56:44 em Brasília)**, `/opt/markina-gallery`, host Oracle ARM64 `132.145.193.169`. Evidência completa externa `C:/codex-data/test-runs/homolog-inventory-20261001.json`, sem env/credenciais, telefones ou nomes de clientes. Consulta complementar confirmou somente UUIDs e igualdade da origem pública configurada.

| Item | Estado verificado |
|---|---|
| Git/last-healthy | `137e1e4c2e4d162d3d231b73e58b6eed75248429`, checkout rastreado limpo |
| Schema | `20260929_0069`, PostgreSQL 17.11; pertence à cadeia local ensaiada |
| Conta atual | 1 tenant, UUID `1531dbaa-215c-4583-b1f0-77d185ad7f07` |
| Admin atual | 1 admin, UUID `f4606e36-a74c-4b31-b123-9ee2059412e5` |
| Clientes/fotos | 0 / 0; configurações/admin/Evolution preservados, não autoriza apagar registros |
| Projeto | `markina-gallery`, 13 serviços em execução; serviços próprios saudáveis |
| Compose efetivo | `docker/docker-compose.yml`, override persistente de branding e `docker/docker-compose.preview-adjustment.yml` |
| Entrada | Nginx próprio `127.0.0.1:8080`; `https://markina-homolog.duckdns.org` |
| Origem pública | `PUBLIC_APP_ORIGIN` já corresponde ao endereço esperado; não reescrever `.env` |
| Flags atuais | facial processing/highres true nos serviços próprios; não alterar flags/modelos/allowlist/credenciais nem executar lote biométrico |
| Health | `/healthz` e `/api/health` locais, `/api/health` público: sucesso |
| Disco | 119 GB livres de 194 GB, 39% ocupado |

Escritores próprios identificados: `api`, `worker`, `face-search-worker`, `face-index-worker`, `face-maintenance-worker` e `preview-adjustment-worker`. Somente esses serão interrompidos para migration; `web` e Nginx próprios serão atualizados depois. DB/Redis próprios e os três serviços Evolution permanecem preservados.

Recursos vizinhos protegidos: Firefly (frontend público 3000, API/bot/db), Nginx Proxy Manager (80/81/443), Portainer (8000/9443), redes `clearbudget_default`, `nginx-proxy-manager_default` e `npm-network` e volumes alheios/anônimos. Não alterar proxy, DNS, certificado, firewall, porta de terceiro ou configuração de rede. DB/Redis/Evolution da Pick-your-Pic continuam sem portas publicadas no host.

## Backup verificável e preservação

Último dump existente: `/var/lib/markina-gallery/backups/predeploy-20261001T005443Z-137e1e4c2e4d.dump`, **374.943 bytes**, SHA-256 `d057fe8beeba50eb3302ad2509dd8eb3821d6a451d617c33ca40a798b2b452a4`. Leitura estrutural `pg_restore --list` aprovada, **689 entradas**. Não foi feita restauração desse dump; estrutura legível não comprova restauração completa. Dump restrito permanece no servidor, sem download/conteúdo no Git.

O deploy autorizado cria novo dump próprio antes da migration pelo fluxo existente. Registrar arquivo, SHA-256, bytes, modo restrito e TOC antes de permitir Alembic. Backup pré-deploy pode anteceder a parada dos escritores: não prometer reversão de banco sem perda das escritas posteriores. Se essa janela não for aceitável, a publicação permanece bloqueada até definir/aprovar backup após quiescência. Nenhum banco será restaurado automaticamente.

0070 conserva UUIDs, relações, snapshots, valores, hashes/envelopes, configurações e storage keys. Recusa contexto ambíguo/órfãos e falha transacional ensaiada. 0071 cria privilégio técnico vazio. Cadeia alvo: **0069 → 0070 → 0071**; sem downgrade, stamp ou limpeza de dados.

## Janela e plano de impacto zero nos vizinhos

Janela proposta: depois da autorização, com o proprietário ciente da interrupção breve da aplicação Pick-your-Pic para migration/retomada; não há duração garantida. Imagens construídas antes da parada. Recursos de terceiros permanecem ativos.

1. Conferir novamente SHA/schema, checkout, Compose efetivo/overrides, saúde, espaço e inventário imediatamente antes da execução. Qualquer divergência material cancela o início; não adaptar destino sem registrar/revisar.
2. Exigir CI verde e SHA exato aprovado; integrar pelo PR para develop somente com autorização que reconheça o gatilho de deploy. Não usar force push nem comandos que descartem trabalho.
3. Confirmar backup restrito novo e evidência estrutural. Conservar branding persistente, origem pública, flags e segredos já configurados.
4. Parar somente os seis escritores identificados, com timeout de 60 s, e provar que nenhum continua ativo. Falha impede Alembic; jobs duráveis ficam no banco para retomada compatível.
5. Aplicar migrations do SHA aprovado e confirmar head 0071. Subir binários compatíveis e verificar API/web/worker/Nginx, ajustes e workers faciais já ativos, preservando DB/Redis/Evolution e vizinhos.
6. Conferir admin/vínculo/configurações legados, contagens anteriores, origem pública, health local/público e ausência de exposição comercial cruzada. Registrar SHA/schema/UTC e resultado; não chamar publicação de validada enquanto faltar aceite aplicável.
7. **Somente se aprovada separadamente neste pacote:** conceder permissão técnica ao admin UUID acima usando CLI offline, dry-run e confirmação exata, com referência da autorização. Revalidar capacidade/painel/cópia; não copiar credenciais nem criar conta adicional.

## Reversão compatível

Antes de iniciar Alembic, pode-se retomar somente binário/serviços anteriores quando a revisão estiver comprovadamente inalterada e o fluxo existente permitir. Depois do início da migration, interromper retorno automático e manter banco para revisão humana. Código de conta única anterior não é presumido compatível com 0070/0071.

Após migration bem-sucedida, preferir correção compatível com o schema novo. Reversão de banco exige autorização própria, backup selecionado/verificado, parada dos escritores, avaliação da janela de escritas posteriores e validação de restauração. Não apagar proprietário/constraints para fazer o código antigo funcionar; não executar downgrade destrutivo ou restore automático.

## Validação e limites

Backend amplo: 1.166 aprovados na execução original, 17 casos afetados pelo executor Windows repetidos e aprovados, variantes PostgreSQL/migrations/concorrência revalidadas. Frontend 398 aprovados, lint/typecheck/build; Ruff fontes/migrations novas e OpenSpec estrito aprovados. CI do PR ainda precisa executar backend/frontend/OpenSpec/gitleaks no SHA candidato, com PostgreSQL sintético exclusivo para a integração A/B.

Piloto local completo: 2 × 3, seis sessões concorrentes, seis pedidos/oito itens, 51 negativas, 12 jobs/36 derivados e três cópias reais do monitor. Durante foi cache; depois amostra nova respeitando 30 s. Dados e pagamentos sintéticos; sem face/modelo/canal real, p95/SLO/capacidade máxima ou orçamento global. Ver `pilot-results.md` e `validation.md`.

Fundação anterior já sincronizada/arquivada em develop. Sua task histórica 6.2 continua aberta para autoria/janela/autorização da primeira aplicação 0069; este pacote não inventa nem encerra essa evidência. Paridade atual de SHA/schema foi demonstrada em modo somente-leitura.

## Autorizações pendentes

- Publicação deste PR/SHA em homologação, janela com interrupção apenas da Pick-your-Pic e novo backup/migrations 0070/0071 segundo o plano acima.
- Concessão técnica ao administrador atual identificado, se o proprietário quiser usar o novo painel logo após a publicação.
- Provisionamento de B, conjunto de até seis clientes/12 JPEGs, bindings, canais e destinatários reais do piloto: exigir inventário/aceite específico após a publicação. Não alterar `.env` ou canal atual com autorização genérica de deploy.
- Revisão humana desta change para sincronização/arquivo, somente depois das validações/aceites e sem marcar tasks bloqueadas como concluídas.

Até o primeiro aceite, tasks 8.1–8.4 permanecem abertas; não há trabalho local independente pendente de implementação. O proprietário aprova um pacote concreto e revisável, com CI e versão identificadas.
