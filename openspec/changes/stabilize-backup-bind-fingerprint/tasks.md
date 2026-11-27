> **SUPERCEDIDA — NÃO EXECUTAR tarefas pendentes nem despachar workflows.** As caixas abertas registram passos não concluídos do vínculo do runtime Google Picker cancelado em 25/11/2026. O trabalho vigente é [retire-platform-backup-runtime](../retire-platform-backup-runtime/tasks.md), seguido pela prova em [prove-open-source-backup-and-recovery](../prove-open-source-backup-and-recovery/tasks.md).

## 1. Implementação

- [ ] 1.1 Selecionar a projeção v2 no workflow e no wrapper para bind-and-rehearse, revalidar precondições sob lock e preservar reconcile.
- [ ] 1.2 Validar guardas, OpenSpec e CI antes de eventual operação protegida em produção.

- [ ] 1.3 Corrigir a recusa do runtime instalado no run 45630729052. Preservar o manifesto em 0400 e provar, com o instalador e o verificador reais em Linux, que a instalação bem-sucedida é elegível para vínculo. Atualizar o pin.

Validação local: 48 testes em Linux root, inclusive instalação seguida pela atestação usada no vínculo; OpenSpec estrito, Ruff, guarda do workflow e diff check passaram. CI da PR pendente.
