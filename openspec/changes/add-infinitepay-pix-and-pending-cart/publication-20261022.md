# Publicação coordenada de pagamentos — 22/10/2026

## Autorização e resultado

Após apresentação do inventário/plano concreto0084→0086/API/web com API interna temporária, o proprietário autorizou expressamente a execução (“Autorizado”), reiterando “Então continue”. Operação entre10:06:55 e10:07:37 de São Paulo, sob lock comum exclusivo. **Resultado: publicada e saudável.**

Git implantado:`d7944baef5191ade6ac26fa86cd631bd5ad464d1`, candidato conjunto dos PRs262/266 já integrados. CI788 integral aprovado; CI789 aprovou os jobs técnicos e recusou corretamente o escopo protegido no workflow0084. O release atual foi uma operação separada autorizada: nenhum gate, allowlist ou manifesto0084 foi relaxado. Nenhum código de manutenção Python/#261 foi integrado.

Host clearbudget-vnic, checkout `/opt/markina-gallery`, Compose `-p markina-gallery -f docker/docker-compose.yml`, domínio `https://markina.pickyourpic.com.br`, única publicação do projeto `127.0.0.1:8080`. Sem novo subdomínio/porta, alteração de recursos de terceiros ou mudança de dependências/runtime.

## Identidades implantadas

| Papel | Identidade |
|---|---|
| API e migrate ARM64 | sha256:166a4cbab9df9eccbb4ed877e342a8f30157fbdb5406517b7051568c52a7a04e |
| Web ARM64 | sha256:68a3267b1d7cd1fdc72fca58b5a02faeb981d50ef0fb5c038ba40dd598e4d4f2 |
| API ativa | 676b4b7149c5f11a0465ab6669a412b233a0b4b18e72c2efee94f031723c593c |
| Web ativa | af6c5c9a91486f224df0029ecb86df6760c057d3ecf2f923bf72ed564107eecf |
| Alembic | 20261021_0086 |

Os cinco overlays anteriores foram preservados, acrescentando **obrigatoriamente** `/var/lib/markina-gallery/deploy-state/payments0086-active-images.compose.json` para as identidades fixas de api/web/migrate e APP_VERSION da API. SHA256 desse overlay:`899df26fa54fbdd369d66aa0f446340853591e9163a27ae5963564961f0d8e60`. Sem o overlay uma futura execução Compose não representa esta publicação. Arquivos ativos, em ordem:

1. `/opt/markina-gallery/docker/docker-compose.yml`
2. `/var/lib/markina-gallery/deploy-state/branding.compose.yml`
3. `/opt/markina-gallery/docker/docker-compose.raw-development.yml`
4. `/opt/markina-gallery/docker/docker-compose.preview-adjustment.yml`
5. `/opt/markina-gallery/docker/docker-compose.system-monitor.yml`
6. `/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml`
7. `/var/lib/markina-gallery/deploy-state/payments0086-active-images.compose.json`

## Sequência comprovada

- Pré-condições renovadas: checkout21b89c3 limpo,15containers/IDs/imagens/StartedAt/saúde idênticos ao inventário, schema0084, configurações/hash preservados, nenhum marcador pendente, backup e homologação aprovados. Objeto Git alvo obtido por fetch do SHA exato, sem pull/reset/force.
- Imagens antigas preservadas em tags explícitas de recuperação; configuração nginx real e recibos anteriores preservados no diretório da operação. Checkout trocado sem descartar alterações.
- Barreira habilitada10:06:59, saúde/retorno preservados e novo webhook400 para retry antes da API0086 disponível. Sem falsas confirmações; novas operações503.
- `migrate` explícito da imagem fixa, `run --rm --no-deps --pull never`, `alembic upgrade 20261021_0086`, lock_timeout5s/statement_timeout120s. Nenhum segredo mestre fornecido ao migrate.
- Após0086, API temporária interna da mesma imagem/configuração, sem porta publicada ou alias `api`; cofre/binding/saúde conferidos. Barreira apontada para ela às10:07:15. Principal recriada e saudável às10:07:24; web recriada e saudável às10:07:30. Sem dependências/build/pull.
- Callbacks devolvidos à principal; configuração nginx original restaurada com nginx-t/reload. HTTPS normal comprovado às10:07:32. Temporária parada/removida exclusivamente por ID/rótulo, sem remover volumes compartilhados.
- Recibos saudáveis APP/web atualizados e marcador próprio retirado somente após sucesso. Quinze serviços healthy;13outros serviços mantiveram IDs/StartedAt, inclusive DB/Redis/workers/nginx. Nenhum restart de terceiros ou atualização do binário nginx.

## Verificações em produção e limites

HTTPS200:`/healthz`, `/api/health`, `/`, `/admin/settings`, `/library/cart`, `/library/purchases`. APIs administrativas InfinitePay e Carrinho recusaram chamada anônima403. Webhook com corpo inválido400; retorno sem candidatos303 durante a barreira. Estes probes não consultaram a InfinitePay nem criaram pagamento. Páginas200 comprovam entrega HTTP; não equivalem a revisão visual autenticada do card ou fluxo completo no navegador.

API com APP_VERSION d7944bae, ambiente legado staging preservado e `IntegrationCipher` disponível. `credential_status` read-only da conta existente comprovou cofre disponível e APIKey configurada pelo binding histórico. Material mestre presente somente na API; web/migrate/outros serviços sem ele. `.env.homolog` não foi alterado. **Zero credenciais geridas cadastradas no banco ao término:** o deploy habilitou a funcionalidade, não migrou/substituiu a APIKey existente. Nova configuração pela UI exige os desafios de autenticação/OTP já implementados.

Digests e contagens das colunas originais de provider_payment, payment_group, sale_order e infinitepay_settings idênticos antes/depois da migration e ao término. Nove ProviderPayments:2confirmed,1verification_required,1awaiting_payment,5exception. Snapshots antigos exclusivos de cartão, capture_method/cart_dismissed_at/credential_id nulos e configurações server_binding preservados. Nenhuma liberação, reabertura, cancelamento, reemissão ou correção financeira foi executada.

Conferência posterior independente às10:08:46SãoPaulo: checkout limpo no alvo,15serviços healthy, mesmos IDs/imagens/StartedAt do recibo final, configuração nginx original restituída, portas preservadas, material mestre somente API, nenhum marcador pendente. Logs de inicialização API/web sem Traceback, FATAL ou linhas ERROR na classificação limitada desde seus respectivos StartedAt; não equivale a auditoria histórica de logs.

Ensaios financeiros A/B, rotação, PIX manual/misto, webhook válido/tardio/duplicado e troca com canary foram feitos na homologação sintética documentada em release-preparation-20261022.md; a fronteira InfinitePay foi simulada. **Não alegar pagamento real ou webhook financeiro real validado nesta publicação.**

## Recibos e recuperação

Recibo primário restrito:`/var/lib/markina-gallery/deploy-state/payments0086-publication-20261022/receipt.json`, SHA256 `a373760480522874796f9350fd67dfe6e99af161510252b8909fecf67214f144`. Contém etapas UTC, identidades/saúde, hashes e resultados sem segredos ou payloads do provedor. Referência ativa:`/var/lib/markina-gallery/deploy-state/payments0086-current.json` registra explicitamente que rollback automático0084 não é permitido.

No mesmo diretório, executor exato arquivado como `executor.py`,0600,SHA256 `a8cf672eb28864b0d6e7b1c37d3d9588c5a157a4ede87661667472ff99a64e4a`; é evidência da operação única, não um helper para repetição cega. Nova conferência independente às10:11:44SãoPaulo aprovada, armazenada em `postcheck.json`,0600,SHA256 `0420263b529299b0c2b89c5bcd1acdb4a63553d3b965a97d2763e3032a903761`. Sem segredos nesses arquivos; material mestre continua somente na configuração segura já provisionada.

Backup real restaurado e backup cifrado do keyring sob guarda externa continuam preservados, conforme a preparação. Schema é aditivo, mas eventual adoção nova exige API0086/cofre/métodos compatíveis. Não executar downgrade, restaurar dump antigo ou retornar cegamente à API #260: preservar transações/ciphertext/snapshots/callbacks e usar recuperação compatível ou correção progressiva com novas emissões restritas. Imagens anteriores preservadas não constituem autorização para apagar estado novo.

## Pendências de uso e decisão

- Proprietário pode agora habilitar PIX no Checkout Integrado InfinitePay. O executor não alterou essa preferência. Somente novas emissões seguem snapshot misto; links legados continuam exclusivos de cartão.
- Proprietário pode usar o card publicado para configurar/substituir/desconectar credenciais, quando desejar, respeitando senha/OTP. Binding existente permanece funcional; não há necessidade de recadastrar segredo apenas por causa do deploy.
- Conferência visual autenticada e emissão/pagamento real continuam fora desta operação; exigir autorização própria para criar cobrança. Não deixar essas limitações parecerem testes executados.
- Sincronização/arquivo das specs requerem revisão humana. Esta entrega registra a publicação sem arquivar automaticamente as changes ou alterar a missão Python.

**Decisão:** GO operacional concluído para este release; GO para habilitação do PIX pelo proprietário e uso da configuração segura publicada. Recuperação de compra específica não foi executada nem autorizada por este recibo. Sem novas alterações funcionais necessárias identificadas nesta execução; não houve oportunidade de refatoração no escopo documental/operacional.

Validação dos registros após a operação: OpenSpec strict das duas changes aprovado e git diff --check sem erros. Runtime não foi alterado após CI/homologação; nenhuma nova suíte de aplicação foi apresentada como executada nesta etapa documental.
