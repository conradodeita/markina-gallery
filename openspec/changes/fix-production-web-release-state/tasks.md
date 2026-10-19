# Tasks

## 1. Contratos e implementação
- [x] 1.1 Registrar contratos, desenho e limites operacionais antes do código; reproduzir defeitos por testes isolados.
- [x] 1.2 Implementar identidade web compartilhada, adoção auditável, inventários sem escrita e locks sem truncamento.
- [x] 1.3 Implementar gates anteriores à mutação, preservação por ID, falhas intermediárias e recuperação exclusiva do web.
- [x] 1.4 Coordenar app após web/web após app e rollback, preservando gates, pin e escopo existentes.

## 2. Validação e integração
- [x] 2.1 Cobrir cenários críticos com stubs/mocks e executar políticas, regressões, sintaxe e OpenSpec estrito.
- [x] 2.2 Executar Code Review, investigar/corrigir achados e revisar diff/segredos/escopo.
- [x] 2.3 Publicar branch/PR, acompanhar CI e integrar somente com proteções satisfeitas e ausência comprovada de efeitos remotos; acompanhar CI final.
- [x] 2.4 Preparar runbook e solicitação operacional única com SHA final, imagem atual, gates, interrupção e recuperação autorizável; registrar evidências.

## Evidências deste checkpoint

32 contratos Linux aprovados em 156,953 s; flock real, mocks Docker/Git/HTTPS, wrapper verificado e falhas de recuperação. Políticas web/workflow, 11 testes de escopo e 12 de classificação aprovados. OpenSpec 1.14.0 estrito: 122/122. Três Code Reviews somente leitura sem defeitos acionáveis; ver `validation.md`. Nenhum teste ou comando SSH executado contra produção. CI/merge ainda pendentes.

## Fora desta autorização

Produção da dependência permanece na task 3.2 da change de segurança. Nenhum fetch, recibo, marcador, tag, lock, container ou banco na Oracle será modificado nesta fase. Não sincronizar/arquivar specs sem revisão humana.

## 3. Retomada pontual autorizada — Health opcional
- [x] 3.1 Reproduzir erro real com Docker CLI e fixtures fiéis, aplicar correção mínima e provar falha antes/sucesso depois.
- [x] 3.2 Validar running/exited, ausência/null de Health/Status, preservação dos parados e falhas de inspeção; repetir contratos/políticas/pins/OpenSpec e Code Review.
- [ ] 3.3 Publicar PR main, acompanhar checks, integrar sem bypass somente com automações seguras e acompanhar CI pós-merge.
- [ ] 3.4 Registrar SHA final e preparar solicitação operacional única; revalidar por leitura o estado mutável, sem escrita Oracle.

O PR #227 anterior foi integrado em 34d2afd5b8f407adb70b0dee165fa8d55a83b478; CI 39177622419 passou. A tentativa posterior ficou bloqueada antes de recibos/tags/build por Health ausente em migrate histórico. Somente fetch preparatório ocorreu. A autorização anterior não vale para o novo SHA. Os registros locais anteriores permanecem preservados em outra branch; esta branch começa na main atual e contém apenas a correção pontual e evidências pertinentes.
