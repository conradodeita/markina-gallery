# Execução SaaS Pick-your-Pic

Continuidade operacional atualizada em 25/11/2026: [higienização da tentativa de backup próprio e plano open source](backup-global-reuso-arquivo-midia.md). O código anterior foi aposentado; snapshots históricos abaixo conservam suas datas e não representam estado atual.

A matriz [requirements.json](requirements.json) rastreia as 694 unidades do mandato EXECUÇÃO INTEGRAL recebido em 31/10. O [status vigente](status.md) distingue implementação local, evidência histórica e produção. Leia o checkpoint de 03/11 antes dos snapshots anteriores. [Decisões](decisions.md), [riscos](risks.md) e OpenSpec devem acompanhar código/testes.

## Estado em 03/11/2026

- Worktree ativa: `C:/codex-data/worktrees/pickyourpic-saas-main/Photo Delivery`, branch `feature/pickyourpic-saas-mainline`, baseline `6af538ec` com diff SaaS preservado. Main remoto está em `855be42b`; [reconciliação](reconciliation-2026-11-03.md) separa patches faciais posteriores, sem rebase/overwrite na árvore suja.
- TOTP, carteira/upload e compras Mercado Pago implementados/testados localmente. Última suíte ampla de 02/11: 1.860 aprovados e 32 skips classificados; reset PostgreSQL 31/2. Evidências e gates nas changes, sem confundir testes com publicação.
- Fase R14 atual: console do proprietário, implementado e validado no escopo local; integrações externas pendentes. Identidade `PlatformOwner` autoriza gestão comercial por decisão explícita; grants de monitor/instalação continuam técnicos. Inventários de acessos e fontes na change `add-platform-owner-console`.
- Cadastro: decisão nova de 03/11 substitui aprovação manual por ativação automática pelo website após verificar e-mail e MFA. Prova sintética Next/FastAPI/PostgreSQL/Edge com dois fotógrafos concluída; domínio/SMTP/anti-bot e abertura pública permanecem gates externos. Termos reservados para lançamento.
- Drive/backup/arquivo e fidelidade mantêm changes próprias/dependências. Snapshot de backup 02/11 não é estado atual nem prova de recuperação integral. Nenhuma fonte ausente vira saudável.
- A restauração facial ocorreu em outra worktree; a cópia antiga neste checkout não é a fonte operacional. Pendências humanas dessa frente não bloqueiam SaaS local.
- Não há autorização para publicar SaaS, aplicar migrations remotas, alterar .env/segredos ou transferir dados reais ao PC. Não há piloto integrado concluído.

## Atualização

Classifique cada unidade somente com evidência verificável; preserve texto/linhas originais de requisitos históricos e registre decisões substitutivas nas notas. Recalcule contagens a partir dos itens. Não inclua PII, tokens, senhas, OTP, fotos ou backups. Spec consolidada/sync/archive exigem revisão humana.

Google Workspace, projeto Cloud Pick-your-Pic, Drive API e cliente OAuth Web Enabled foram declarados pelo proprietário no checkpoint de 03/11; não foram revalidados nesta execução e nenhuma credencial/JSON foi lida. Continuam pendentes o callback publicado/roteado, consentimento owner-only, custódia de credenciais, destino privado, quota/permissões observadas e ensaio real de readback/restore. A identidade dedicada e o caller/scheduler da rotina também aguardam configuração e release próprios. O histórico de preparação está em [google-workspace-setup.md](google-workspace-setup.md).
