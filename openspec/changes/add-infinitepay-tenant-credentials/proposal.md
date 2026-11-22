# Proposal

## Why

O fotógrafo precisa cadastrar a própria credencial InfinitePay no card já existente, sem intervenção operacional por conta. O PR #260 resolve autenticação e proteção financeira, mas recebe a chave somente por binding do servidor.

## What Changes

- Completar o card existente com entrada secreta, cadastro/substituição e desconexão protegidos por senha e confirmação local já existentes.
- Guardar somente ciphertext autenticado em tabela dedicada, por tenant e versão; manter chave mestra externa ao banco e ao Git.
- Congelar a referência da credencial na compra e preservar versões necessárias a pagamentos pendentes; impedir desconexão que abandone uma transação incerta.
- Mostrar cadastro e indisponibilidade de validação remota como estados distintos, sem testar cobranças ou inventar endpoint de validação.
- Preservar bindings legados estritamente por tenant e o PIX manual, sem fallback após adesão à gestão pela UI.
- Preparar migration aditiva, ensaio isolado, rotação/recuperação criptográfica e publicação coordenada com #260.

## Capabilities

### New Capabilities

- `gallery-sales/infinitepay-credentials`: gestão autenticada de credenciais versionadas e sua vinculação financeira por fotógrafo.

### Modified Capabilities

- `deployment-operations`: admitir ciphertext em armazenamento dedicado; material criptográfico permanece externo, com backup e rotação próprios.

## Impact

Depende do PR #260, SHA base `0959c64f00c60e6674675a9d90b43f0d7f9428b7`, aberto em draft e não mesclado no início. Branch/worktree próprios; PR dependente com diff limitado a esta change. API, card InfinitePay, modelos/migration PostgreSQL e configuração criptográfica exclusiva da API. Reutiliza `cryptography` já instalada, sem serviço pago ou cofre externo adicional. Não altera Oracle, credenciais reais, compras reais, PIX, módulo Python de manutenção nem publica serviços.

## Authorization

Pedido explícito do proprietário em 20/10/2026 autoriza implementação local, testes isolados e PR próprio, incluindo ciphertext autenticado no banco dedicado. Isso especializa a regra anterior de segredos somente em configuração de servidor; a chave mestra continua exclusivamente nessa configuração. Não autoriza merge, deploy, migration remota ou provisão de segredo real.

## Continuidade após a publicação de pagamentos

Em 21/10/2026, após o release bem sucedido de #263/#265 em main `21b89c332c6937b7079679888d52bd6a8aefe25d`, o proprietário solicitou retomar este fluxo. O candidato `c0746a7` possui todos os checks obrigatórios aprovados contra a base antiga. Integrar main por merge preservando commits, retargetar o mesmo PR #262 e validar o candidato resultante, sem reimplementar o cofre. Conservar a reabertura auditada de carrinho, respostas tardias e fotos escolhidas junto com os snapshots de credencial. Corrigir somente a orientação do card sobre PIX global para refletir opções por link do contrato autenticado já existente. A autorização desta etapa continua restrita a código/testes/documentação/PR; migration, mestre e publicação deste cofre permanecem operações separadas.
