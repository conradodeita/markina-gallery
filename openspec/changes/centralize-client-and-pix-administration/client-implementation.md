# Continuidade — diretório e lifecycle de clientes

## Inventário reproduzível anterior ao código

Executar a partir da raiz:

```powershell
rg -n "class (Client|ClientPhone|SaleOrder|PaymentCommunication|DerivedGallery|FacialSearchRequest)" backend/app/auth.py
rg -n 'admin/clients|ParentGalleryRegistration|DerivedGalleryMembership|client_id' backend/app/main.py backend/app
rg -n '/api/admin/clients|Cadastro existente|Desvincular cliente' frontend/app
npx --yes @fission-ai/openspec@latest list --json
git status --short
git diff --stat
```

O inventário confirmou uma identidade canônica `Client` + histórico de telefones
em `ClientPhone`; a interface de administração existia somente dentro da etapa 05.
A exclusão anterior tratava vínculos operacionais como bloqueadores e não possuía
recibo próprio. Pedidos, itens, comunicação/notificação de pagamento,
`CommercialHistoryMedia` e entregas WhatsApp formam o histórico protegido.
Sessões, OTPs, capabilities, registros/memberships, interações e buscas faciais são
estado operacional.

## Convivência com as changes ativas

- `consolidate-shared-private-galleries-and-progressive-sales` define a identidade
  única por telefone e as privadas com vários membros. Esta implementação preserva
  uma privada compartilhada e as interações de terceiros; uma pessoa não é
  duplicada nem mesclada.
- `improve-gallery-and-client-data-lifecycle` preserva o histórico comercial quando
  galerias são excluídas. Esta implementação aplica a mesma fronteira: qualquer
  pedido ou dependência comercial bloqueia o delete global da cliente.
- `integrate-private-facial-filter` define referência e resultados faciais como
  transitórios. Eles são removidos somente para a cliente alvo; JPEGs da Galeria
  pública permanecem.
- As changes de pagamentos e PIX mantêm snapshots imutáveis. Nada nessa entrega
  recalcula pedidos, altera PIX ou remove comunicações comerciais.

Não foi encontrado conflito que exigisse substituir requisitos. A associação de
entregas comerciais foi deliberadamente feita pelo `source_id` da comunicação ou
outbox, e não pelo telefone, para evitar falso bloqueio e remoção cruzada quando um
número aposentado for reutilizado.

## Implementação

- `GET /admin/clients` agora fornece busca, cursor e agregados em uma consulta de
  tamanho constante.
- `/admin/clients` no frontend funciona sem Galeria pública e compartilha cadastro,
  edição, troca verificada de telefone e diálogo de exclusão com a etapa 05.
- `client_lifecycle.py` classifica inventário, bloqueia a identidade, remove o grafo
  operacional por operações set-based, reclassifica corridas e cria recibo/auditoria
  sanitizados no mesmo commit.
- `client_deletion_receipt` é aditivo, persiste somente o fingerprint SHA-256 da
  chave idempotente, não contém FK para o UUID apagado e não contém colunas de PII.
- A privada exclusiva sem histórico é removida; a compartilhada e seus outros
  membros permanecem. Galerias públicas, pastas, JPEGs e histórico comercial não
  entram no delete.

## Evidências e limites

Os testes direcionados cobrem autorização, paginação/busca/ordem, ausência de N+1,
sucesso e retry, privada exclusiva/compartilhada, isolamento de terceiros, OTP,
arquivo facial, bloqueio comercial, corrida com rollback, migração e ausência de
PII. Na árvore final, esse recorte aprovou **15 testes** e a suíte backend integral
aprovou **380 testes, com 1 skip esperado**. Ruff passou em `app`/`tests` e na
migration nova.

O frontend aprovou **154 testes em 28 arquivos**, lint sem erros (22 avisos
preexistentes), typecheck e build de produção com a rota estática
`/admin/clients`. Os componentes afetados somaram 50 testes dirigidos. A interface
usa cards responsivos em duas colunas e reduz para uma coluna nos breakpoints de
900/560 px; a verificação visual autenticada remota permanece em 7.6.

Em PostgreSQL 17 descartável e isolado em `127.0.0.1:55447`, o ciclo
`0046 → 0047 → 0046 → 0047` terminou no head único `20260907_0047`, confirmou o
fingerprint idempotente como `VARCHAR(64)` e a ausência de FK no UUID alvo. O
container não usou volume e foi removido após o teste. OpenSpec estrito, gitleaks
no diff/arquivos novos e `git diff --check` também passaram.

A redação estrita de 1.2 exige teste inicialmente falho. O ciclo red/green foi
observado para o diretório/lifecycle antes desta implementação. A redação estrita
de 1.3 continua sem evidência retroativa completa no recorte PIX e permanece
aberta. Deploy, migration em homologação e conferência humana pertencem a 7.6 e
continuam condicionados a autorização explícita posterior.
