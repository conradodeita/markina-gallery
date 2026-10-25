## Mercado Pago Integration Review

**Scope**: security
**API detected**: Orders API
**Products detected**: Checkout Transparente, cartões em uma parcela e Pix
**Files analyzed**: módulos `backend/app/mercadopago_*.py`, modelos/migration 0088, checkout/projeções/worker/entrega, frontend checkout/carrinho/Compras/configuração/painel e testes relacionados; inventário completo em `implementation-report.md`.

### CRITICAL

- Validação externa de desenvolvimento executada; secret store/worker/HTTPS de ambiente operacional não foram publicados ou validados em produção. Não declarar pronto para produção com base no ensaio.
- Nenhuma autorização de produção foi concedida. Gate de cobrança real permanece fechado.

### WARNINGS

- GitHub retornou 50 alertas abertos na main em consulta read-only (5 críticos/25 altos/19 médios/1 baixo); aplicabilidade ao candidato/runtime exige revisão antes da publicação. Não se trata de conclusão de auditoria de dependências nem de regressão atribuída ao SDK novo.

- Cofre/chaves do servidor e URL HTTPS/registro de webhook não foram configurados em ambiente operacional nesta missão.
- Refund parcial/integral comprovados na conta de teste, inclusive por dois callbacks genuínos. Chargeback/expiração/aprovação tardia real permanecem limitados aos cenários contratuais. Sem iniciação automática de reembolso no produto.
- Compartilhamento externo já conhecido não é revogado pela suspensão interna de entrega.
- Cópia genérica da skill sobre Bricks/tópico foi confrontada com documentação específica: Card Payment é documentado para Orders e o tópico online é `order`.

### PASS

- SDK oficial e endpoints Orders; não há integração Checkout Pro nova.
- Cotação/snapshot no servidor, idempotência anterior à rede, locks PostgreSQL e proteção de resultado desconhecido.
- Credenciais cifradas e versionadas por tenant, contexto de AAD, senha/OTP/sessão/origem/versão.
- Estados financeiros separados, aprovação autoritativa, eventos atrasados, refund/parcial/contestação e duplicidade em revisão.
- Inbox HMAC, persistência antes de ACK, deduplicação, backoff, lease/fencing e polling após finalização.
- PIX manual preservado, flags independentes e proteções de lifecycle/histórico.

### Quality Standards

Not requested for this scope. MCP Mercado Pago não expõe `quality_checklist`/`authenticate` nesta sessão; não foram inventados critérios oficiais, pontuação ou certificação. Reconsulta oficial de 24/10 confirma quality_evaluation com order_id, porém exige pagamento produtivo: não realizado no escopo autorizado. Isso corrige a limitação Orders-only da skill instalada. Formulário de homologação não foi submetido. Resultados externos de desenvolvimento estão em external-validation.md.

#### Required fields

Não avaliados por checklist oficial MCP; sem pontuação presumida.

#### Best practices

Não avaliadas por checklist oficial MCP; as verificações locais abaixo não substituem a homologação externa.

### Security checklist (cross-cutting)

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Token no servidor, sem segredo fixo | Implemented | `mercadopago_settings.py`, IntegrationCipher/AAD; strings de teste são sintéticas |
| 2 | `.env` ignorado, `.env.example` permitido | Implemented | `.gitignore`, nenhum arquivo de credencial alterado |
| 3 | Webhook HMAC-SHA256 | Implemented | `mercadopago_webhook.py:receive_notification`, testes de assinatura/conta/ID |
| 4 | HTTPS para notificação pública | Implemented in development | Túnel restrito autorizado, TLS e HMAC verificados; duas entregas genuínas processadas. Ambiente operacional requer configuração própria; túnel já encerrado |
| 5 | Estado confirmado no servidor | Implemented | GET Orders + `apply_order`, total/referência/método/recebedor e bloqueio de regressão |
| 6 | Chave de idempotência na criação | Implemented | `OrdersProvider.create`, UUID durável antes do POST; teste concorrente PostgreSQL |
| 7 | external_reference em toda order | Implemented | `submit_payment`, UUID da tentativa |
| 8 | Segregação efetiva de credenciais de teste/produção no deploy | Partial | Nenhuma credencial real foi adicionada; conta real bloqueada por padrão. Deploy e cofre operacional não foram inspecionados/alterados |
| 9 | Ausência de sandbox_init_point na integração | Implemented | Adaptador Orders e CTA próprio, sem URL de checkout hospedado |

### Recommendations

1. Registrar a restrição do formulário à retirada da URL de Teste; substituir a URL encerrada antes de novo ensaio e revisar a evidência externa.
2. Conferir secret store e operação do worker no ambiente que vier a ser autorizado.
3. Reexecutar revisão com evidência externa antes de qualquer autorização separada de publicação.

**Summary**: Official quality: not requested/not verified. 8/9 security checks comprovados em desenvolvimento; segregação do deploy produtivo não foi inspecionada/alterada.

---

### Revisão adicional para o ensaio restrito — 24/10/2026

Achados corrigidos antes do PR: disponibilidade geral de conta de teste, ausência do binding de cofre no worker e inclusão de simulações em receita/CSV. Política do servidor agora restringe pares tenant/cliente, revalida envio e mantém conciliação; simulações ficam identificadas sem gerar receita real. Join de projeção inclui conta e tenant; identidade/mode externo divergente é recusado. Teste HTTP com dois fotógrafos comprova contas/flags/desafios separados.

Card e escolhas de pagamento revisados visualmente com componentes reais/dados sintéticos: 24 capturas, sem overflow/erro JS; hints/clipboard/origem/segredos cobertos por testes. 58 contratos PostgreSQL/operacionais e 87 testes frontend aprovados; configuração ampliada, 5 aprovados. Runtime operacional/cofre e liberação restrita ainda não foram verificados no servidor.

O aceite final foi solicitado pelo proprietário no ambiente de produção com credenciais **Teste** e seu próprio cliente. Gate operacional concreto em release-plan.md; não executar cobrança real. O classificador mantém este delta protected; fluxos antigos não autorizam migration/worker/Compose Orders. Operação específica de release e recuperação compatível continuam pendentes; nenhum gate foi relaxado.

## Implementation Report

### Verified

- [x] Integração Orders implementada com PIX preservado e isolamento por tenant.
- [x] SDK oficial, idempotência, HMAC, estados autoritativos e snapshots cobertos por testes locais.
- [x] Build, validações estáticas e matriz visual local registrados em `validation.md`.
- [x] SDK/tokenização, Orders/GET, refund/Pix e duas notificações genuínas de teste comprovados em `external-validation.md`.

### Needs attention

- [x] Validar tokenização e pagamentos externos conforme `integration-guide.md`, seção 6.
- [x] Registrar webhook HTTPS de desenvolvimento e comprovar callback real; túnel encerrado após ensaio.
- [ ] Retirar URL temporária: formulário recusa URL vazia e não salva sem eventos; sem controle de exclusão visível/MCP disponível. Túnel e servidores já encerrados. Substituir por nova URL autorizada antes de outro ensaio.
- [ ] Executar revisão humana da change; specs principais e arquivo aguardam essa revisão.

### Blockers (must fix before production)

- [ ] Aceite operacional do proprietário na instalação de produção, configuração segura/cofre API-worker/webhook e recuperação compatível, conforme release-plan.md.
- [ ] Publicação e migration operacional exigem autorização humana separada; não foram executadas.

### Next steps

1. Revisar PR/CI e preparar inventário/fluxo de release específico, mantendo o escopo protected fechado.
2. Apresentar inventário, serviços/portas, backup/recuperação e plano restrito para autorização concreta. Substituir a URL de Teste encerrada somente no ensaio autorizado.
3. Re-run the `mp-review` skill after fixes to confirm the report.

### Resources used

- Local: inspeção do código, testes contratuais/concorrentes, matriz visual e checklist transversal.
- Skill: `mp-review` v1.0.0; `mp-integrate`, `mp-webhooks`, `mp-test-setup` e documentação oficial Orders.
- MCP: nenhuma operação Mercado Pago disponível/executada.

**Scores**: official quality: N/A, 8/9 security in development. **Verdict**: Development validated — production operational checks and human review pending.
