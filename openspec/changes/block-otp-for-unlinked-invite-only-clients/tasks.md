# Tasks

## 1. Integração ao baseline atual

- [x] 1.1 Adaptar elegibilidade e primeira entrega à autenticação multitenant atual; validar ausência de entrega/cadastro/vínculo/sessão para inelegíveis e isolamento por fotógrafo. Evidência: regressões de resposta neutra, ausência de outbox/sessão e mesmo telefone nas contas A/B em test_invite_only_otp.py.
- [x] 1.2 Revalidar elegibilidade no reenvio, preservar rotação/expiração de entregas e comprovar vínculo posterior, vínculo removido, convite divergente/revogado/expirado. Evidência: vínculo posterior exige novo envio e permite login; convites divergentes não geram outbox; convites inválidos impedem reenvio; três estados de revogação passaram com entrega criptografada pendente (3/3).
- [x] 1.3 Preservar modos e contextos existentes, reautenticação contextual, link privado compartilhado e privadas após exclusão da origem; executar regressões pertinentes. Evidência: seis combinações privadas active/deleted e três escopos passaram; 27 testes multitenant existentes e 18 regressões legadas passaram.

## 2. Integração e evidências

- [x] 2.1 Executar testes de autenticação/outbox no baseline atual, Ruff backend, OpenSpec estrito e diff-check; revisar diff e registrar evidências antes de preparar PR. Evidência: 17/17 regressões novas, 27/27 testes multitenant existentes e 18/18 regressões legadas; Ruff backend completo e OpenSpec 1.14.0 estrito (80/80) aprovados; diff limitado aos arquivos desta change.
- [ ] 2.2 Criar commit focado e PR para develop, anexar PR e registrar estado do CI sem merge/deploy automático.

## Workflow follow-up

Revisão humana antes de sincronizar specs e arquivar. Deploy exige inventário/plano de impacto zero e autorização própria. As validações no checkout antigo ficam em validation.md somente como histórico, não substituem a validação desta integração.
