# Tasks

> Retomada em 04/11/2026 após troca de modelo. Checkpoint anterior em [pause-handoff.md](pause-handoff.md); progresso/evidência atual em `validation.md`.

## 1. Contratos e persistência

- [x] 1.1 Reconciliar a change com `add-photographer-signup-portal`, auth, carteira, checkout, console, PIX, WhatsApp e todas as rotas de upload; listar os pontos de gate e os consumidores legados em `validation.md`.
- [x] 1.2 Modelar estado exploratório, perfil contratual protegido e protocolos de aceite append-only em migration aditiva; testar upgrade/rollback não destrutivo e isolamento de tenant em PostgreSQL local.
- [x] 1.3 Definir serviço único de elegibilidade server-side com estados verificáveis de e-mail, perfil, termos, saldo, PIX e WhatsApp; não interpretar indisponibilidade de dependência como requisito concluído.
- [x] 1.4 Inventariar instância, segredos, pareamento, webhook, filas e unicidade do WhatsApp atual; modelar autoprovisionamento idempotente, credenciais protegidas por tenant, canal próprio por tenant/ambiente, migração preservadora do legado e testes de isolamento A/B antes de usar o estado como gate de upload.

## 2. Autenticação e recuperação

- [x] 2.1 Fazer verificação de e-mail + senha provisionar conta exploratória sem TOTP; preservar controles de OTP, anti-bot, idempotência, sessão restrita e rotas públicas fechadas por padrão. Testar criação e dois tenants sintéticos.
- [x] 2.2 Permitir login por senha apenas a fotógrafo elegível sem TOTP; exigir TOTP não reutilizado após ativação e manter proprietário/legados com MFA. Testar suspensão, replay, papéis, sessão e tenant cruzado.
- [x] 2.3 Implementar enrollment voluntário guiado de TOTP em Configurações, confirmação, códigos de recuperação e revogação de sessões. Cobrir recuperação de senha por e-mail sem TOTP e com TOTP/código vigente.
- [x] 2.4 Implementar revogação assistida owner-only com reautenticação forte, motivo, trilha auditável, invalidação de sessões/fatores e aviso ao e-mail verificado. Testar negativa de fotógrafo/operador, tenant errado e conta do proprietário.

## 3. Cadastro completo e aceite

- [x] 3.1 Revalidar identidade de ingresso, CPF e endereço do pagador. Endereço adicionado por decisão do proprietário em 05/11/2026: cifrado, obrigatório para a compra; telefone/complemento opcionais. API, cifragem, identidade de ingresso, migration 0104 e resposta de checkout validadas em `validation.md`.
- [x] 3.2 Implementar Termos versionados e protocolo de aceite; versão de teste somente em ambiente local sintético. Falhar fechado quando versão/identidade do provedor real estiver ausente; não copiar minuta como documento aprovado.
- [x] 3.3 Criar resumo autenticado de progresso para Configurações e comprovar que exploração não exige dados operacionais.

## 4. Gates e interface

- [x] 4.1 Aplicar gate de cadastro/aceite antes de preparar ou criar compra de créditos; preservar validação do pagador e reconciliação de Orders já iniciadas. Testar bypass por API, webhook e revisão financeira.
- [x] 4.2 Aplicar gate de cadastro, crédito, PIX e WhatsApp em todas as entradas/reservas de upload; testar API direta, concorrência, tenant cruzado e canais indisponíveis, preservando fluxos de pagamento e fotos existentes.
- [x] 4.3 Criar UI de cadastro inicial, esqueci a senha, Configurações com progresso, TOTP guiado e redirecionamento contextual sem perder dados não sensíveis; mostrar “WhatsApp” ao fotógrafo.
- [x] 4.4 Executar jornada local sintética em navegador: exploração → cadastro completo/aceite de teste → compra simulada → configuração PIX/WhatsApp → upload com crédito, incluindo negativas em cada gate. Evidência em `validation.md`, prova da jornada no Chrome de 05/11/2026.
- [x] 4.5 Reorganizar progresso em etapas recolhíveis com check visível por item obrigatório; usar nome/e-mail do ingresso e coletar CPF e endereço completo cifrado. Exigir o endereço para compra de créditos e pré-preenchê-lo no checkout, permitindo alteração apenas na transação. UI, componente do checkout e gates validados; evidência em `validation.md`.

## 5. Fechamento local e gates externos

- [x] 5.1 Rodar testes direcionados, suites de integração pertinentes, lint, typecheck, build, migrações locais e validação OpenSpec; revisar diff, segredos e refatoração proporcional. Evidências em `validation.md` (retomada local de 05/11/2026).
- [x] 5.2 Documentar resultados e bloqueios de texto jurídico/identidade do provedor, retenção, transporte real, anti-bot e publicação. Não marcar validação externa como concluída por prova sintética. Bloqueios e evidências em `validation.md` (retomada local de 05/11/2026).
- [x] 5.4 Validar a revisão da tela com teste direcionado, lint/typecheck aplicáveis e inspeção visual local; registrar evidências sem acessar produção. Testes, lint, typecheck, build, OpenSpec e observação em Chrome registrados em `validation.md`.
- [x] 5.3 Após revisão humana, sincronizar specs principais e arquivar somente quando os requisitos aplicáveis estiverem completos. Revisão e autorização expressa do proprietário em 07/11/2026; sete deltas sincronizados, 31 specs principais validadas sem falhas e comparação dos 18 requisitos do onboarding com as specs consolidadas aprovada. Arquivada em `openspec/changes/archive/2026-11-07-add-progressive-photographer-onboarding`. Nenhuma escrita remota, migration ou deploy.

## 6. WhatsApp obrigatório, personalização condicionada e avaliação de e-mail

- [x] 6.1 Preservar WhatsApp obrigatório nos gates/contagem de upload conforme decisão final do proprietário; registrar a retirada da proposta opcional e validar o bloqueio existente.
- [x] 6.2 Expor capacidade de edição WhatsApp por tenant e recusar alteração de texto/habilitação sem conexão própria, inclusive templates legados, permitindo salvar push independentemente. Testar isolamento, indisponibilidade e ausência de alteração parcial.
- [x] 6.3 Bloquear controles WhatsApp em Notificações com orientação e link Configurações; manter push editável, tratar falha fechada e evitar nomes técnicos na UI. Validar componentes, tipos e lint.
- [x] 6.4 Avaliar canal exclusivo WhatsApp/e-mail por tenant, remetente próprio, destinatários, autenticação cliente, filas, migração, entregabilidade e limites de reaproveitamento; registrar fontes e decisões pendentes. Validar OpenSpec e revisar diff focal, sem produção.
