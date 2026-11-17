# Tasks

## 1. Evidência de CI

- [x] 1.1 Implementar seleção fail-closed de run e jobs do SHA exato, com testes para ausente, falha, pendência, reexecução, SHA/branch/evento errados, paginação e jobs ausentes. Evidência: sete testes sintéticos e ruff F/E9 passaram; seleção aceita apenas push/main e jobs obrigatórios concluídos.
- [x] 1.2 Integrar consulta autenticada de leitura com permissões mínimas, sem segredos em logs, e validar falhas de API e seleção do candidato separadamente. Helper autenticado passou na main c36536b6, identificando CI 40429634039; workflow usa actions/contents read e recusa redirects; gate existente do candidato é mantido e seu inventário valida CI do candidato.

## 2. Continuidade protegida

- [x] 2.1 Adaptar operação manual designada a reutilizar CI comprovado, preservando checks em PR/push e nomes dos gates; testar workflow e recusa de skipped/falhas. Evidência: workflow separado sem push/PR, 10 testes de seleção, jobs e contrato passaram; etapas operacionais verificadas idênticas às originais, com escopo e gates preservados.
- [ ] 2.2 Encadear inventário apresentado, fingerprint e aprovação automática no escopo autorizado, com revalidação sob lock e testes de mudança de SHA/estado e autorização ausente. **Parte local validada:** o fluxo repassa o fingerprint do preflight, revalida inventário sob lock e recusa autorização divergente antes da mutação; 33 testes sintéticos de contrato, inventário e fluxo passaram. **Bloqueada para validação final:** falta comprovar o encadeamento sem mutação no runner e a integração de aprovação por executor autorizado. Essa prova exige PR/push e não foi acionada, pois o proprietário determinou que o primeiro push só ocorrerá quando o trabalho atingir 100%.
- [x] 2.3 Documentar limites da autorização, backup, impacto, recuperação e verificação pós-release; revisar duplicações e riscos no diff. Evidência: docs/AUTOMATED-AUTHORIZED-RELEASE.md; testes comparam as etapas operacionais ao workflow existente para detectar desvio.

## 3. Validação e publicação

- [x] 3.1 Executar testes focados dos gates, política de release, OpenSpec strict e revisão do diff; registrar evidência em `validation.md`. Em 08/11, inventário de ambiente + política do candidato + evidência de CI + contrato do workflow: **23 passed**; política estática do workflow passou; Ruff e `openspec validate --strict` passaram; diff da matriz e do fluxo foi revisado. A prova no runner real pertence à task 2.2 e permanece bloqueada.
- [ ] 3.2 Publicar PR em draft, acompanhar CI do SHA exato a cada 14 minutos e validar o fluxo sem mutação. Somente após reconciliar o release 0090 e seus SHAs, integrar conforme autorização vigente.

## Workflow follow-up
- Reconciliação em 2026-10-27: PR #306 integrada na main `80075b5dd0fc78e0b5a53ded72c40ceefc62fa82` após CI verde e prova real de preservação. A branch desta change incorporou essa main com resolução focada no CI, mantendo ambas as validações. Dez testes de reutilização/contrato e 36 testes de inventário/release passaram; política de release e OpenSpec strict passaram. O preflight anterior #40443842889 terminou com falha e não há preflight ativo a interromper. A integração da otimização poderá preceder a nova instalação/preflight, após CI da base e da PR atualizada; a nova operação ficará fixada no SHA integrado e não reutilizará fingerprint do run anterior. Aguarda CI push/main #40500230224 antes de publicar a atualização da PR que verifica essa base remotamente. As tasks operacionais continuam abertas até evidência do runner e do ambiente protegido.
- Sincronizar spec consolidada e arquivar somente após revisão humana conforme política do repositório.
