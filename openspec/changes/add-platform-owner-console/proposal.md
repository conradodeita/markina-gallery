# Proposal: Painel do proprietário da plataforma

## Contexto

A base publicada tinha monitor técnico restrito por `PlatformOwner` e grants específicos. A evolução local de carteira/compras já autorizou operações comerciais exclusivamente pela identidade persistida do proprietário. Esta change acrescenta console separado, preservando os grants técnicos. Provisionamento CLI permanece offline; ingresso de fotógrafos ocorrerá automaticamente pelo website conforme decisão substitutiva de 03/11/2026.

## Goals

- Oferecer área administrativa global separada do painel do fotógrafo, com autorização explícita ligada à identidade administrativa verificada.
- Permitir consultar tenants e estado agregado; suspender/reativar somente por operações explícitas e auditáveis, sem apagar histórico. Cadastro/ativação seguem o website após e-mail verificado e MFA, sem convite ou aprovação manual no console.
- Reunir estados comerciais e operacionais por capabilities específicas, sem ampliar o grant técnico do monitor.
- Revalidar a sessão e a identidade do proprietário imediatamente antes de persistir cada mutação sensível, revertendo a transação se a autorização tiver mudado.
- Mostrar fontes, horário e disponibilidade de cada dado, diferenciando estado desconhecido, fonte indisponível e resultado vazio.
- Auditar ator, tenant relacionado, ação, objeto, data, resultado e origem quando disponível, sem registrar segredos ou PII desnecessária.

## Non-goals

- Usar e-mail isolado como autorização, alterar o login administrativo existente ou criar acesso por impersonação.
- Exibir fotos, biometria, clientes ou documentos financeiros detalhados sem necessidade operacional e permissão apropriada.
- Criar pagamentos, política de créditos/fidelidade, serviço de backups/Google Drive ou executar operações reais remotas; esses domínios têm changes próprias.
- Alterar status, provisionar contas reais, ler backups ou publicar dados em produção nesta proposta.

## Evidência inicial

- `PlatformOwner` é associado ao UUID de `AdminUser`; `MonitorGrant` concede apenas `metrics`, `tree`, `incidents` e `export` do monitor. A capability de instalação separada é somente `capacity_diagnostics`.
- A árvore do monitor consulta fotógrafos em modo de leitura. `provision_photographer.py` cria conta somente em modo `--apply` confirmado, exigindo credenciais externas e preservando vínculos existentes; não existe UI de provisionamento.
- `Tenant.status` distingue `active`/`suspended`, mas nenhuma rota/UI global de suspensão foi encontrada. Suspender não equivale a apagar.
- `AuditEvent` guarda tenant opcional, evento, subject e timestamp. Esses campos não explicitam todos os detalhes exigidos pelo novo log administrativo.
- Monitor lê agregados de jobs, uploads, disco e alertas. No repositório, backups encontrados são de transição/configuração; não foi localizada integração Google Drive de backup/arquivamento para alimentar o painel. Runtime externo permanece desconhecido.

## Decisões reconciliadas e dependências

- Identidade global exclusiva do `PlatformOwner`, sem grants comerciais delegáveis nem autoridade derivada de grants técnicos. Senha + TOTP one-time para status, rate limit, locks, precondição e idempotência.
- Website automatiza o ingresso; fotógrafo define sua própria senha/TOTP após OTP. Prova local simples autorizada em 03/11; publicação segue gates próprios.
- Suspensão local autorizada: pausar acessos/uploads/jobs/mensagens, preservar dados e conciliar pagamentos já iniciados. Reativação explícita; não suspender a conta proprietária pelo console. Detalhes em design.md.
- Nome informado/e-mail administrativo, estado/host, contagens e estados comerciais já autorizados; sem conteúdo de clientes, fotos, biometria, segredos ou impersonação. Novo log global é sanitizado/append-only e não expõe subject bruto do log legado.
- Identificar fontes operacionais autorizadas de backup e Google Drive antes de apresentar estado ou integridade no painel.

## Impacto de refatoração contínua

Reutilizar a identidade `PlatformOwner`, a separação de grants do monitor e o provisionamento offline somente onde os contratos couberem. Não transformar o monitor em painel financeiro nem remover o fluxo offline até provar compatibilidade e todos os consumidores.
