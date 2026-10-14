# Resultado do deploy em homologação

Deploy autorizado pelo proprietário e executado em 2026-09-01 pelo fluxo
protegido, sem ação manual no servidor e sem alteração de recurso externo à
Markina Gallery.

## Integração e CI

- PR: `#24`, integrado em `develop`.
- SHA publicado: `76f64a66511ac9c87cf35615dd46b6d7ba087e2c`.
- Workflow: `CI`, run `33505293686`.
- Jobs aprovados: `backend`, `frontend`, `openspec`, `gitleaks` e
  `deploy-homolog`.
- Deployment GitHub: `6200715781`, estado final `success` em
  `2026-09-01T12:03:49Z`.

## Banco, backup e serviços

O log sanitizado do job registra:

```text
backup lógico exclusivo da Markina criado
migration Markina: 20260831_0032 (head) -> 20260831_0033 (head)
deploy-homolog concluído para 76f64a66511ac9c87cf35615dd46b6d7ba087e2c
```

O script só conclui depois de `api`, `web`, `worker` e `nginx` ficarem
saudáveis, validar os healthchecks interno e externo e gravar o SHA como
`last-healthy`. Nenhum downgrade, prune, restauração, alteração de proxy, DNS,
firewall, certificado, credencial ou configuração Evolution foi executado.

## Healthchecks e smoke externo

Verificação independente após o job, em
`https://markina-homolog.duckdns.org`:

| Rota | Resultado esperado e observado |
|---|---|
| `/healthz` | `200`, `text/plain` |
| `/api/health` | `200`, JSON com `status=ok` e `service=api` |
| `/` | `200`, entrada HTML da aplicação |
| `/api/branding` | `200`, configuração pública sanitizada |
| `/api/admin` sem sessão | `403`, acesso administrativo protegido |
| `/api/public-galleries/00000000-0000-0000-0000-000000000001` sem contexto | `403`, grade protegida |

O smoke foi somente leitura e usou UUID sintético; não criou cliente, galeria,
foto, pedido, comunicação, OTP ou sessão. A aceitação autenticada e visual segue
pendente na task 7.7 e pertence ao proprietário.
