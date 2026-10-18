# Tasks

## 1. Contratos e implementação
- [x] 1.1 Registrar contratos, desenho e limites operacionais antes do código; reproduzir defeitos por testes isolados.
- [x] 1.2 Implementar identidade web compartilhada, adoção auditável, inventários sem escrita e locks sem truncamento.
- [x] 1.3 Implementar gates anteriores à mutação, preservação por ID, falhas intermediárias e recuperação exclusiva do web.
- [x] 1.4 Coordenar app após web/web após app e rollback, preservando gates, pin e escopo existentes.

## 2. Validação e integração
- [x] 2.1 Cobrir cenários críticos com stubs/mocks e executar políticas, regressões, sintaxe e OpenSpec estrito.
- [x] 2.2 Executar Code Review, investigar/corrigir achados e revisar diff/segredos/escopo.
- [ ] 2.3 Publicar branch/PR, acompanhar CI e integrar somente com proteções satisfeitas e ausência comprovada de efeitos remotos; acompanhar CI final.
- [ ] 2.4 Preparar runbook e solicitação operacional única com SHA final, imagem atual, gates, interrupção e recuperação autorizável; registrar evidências.

## Evidências deste checkpoint

30 contratos Linux aprovados em 164,262 s; flock real, mocks Docker/Git/HTTPS, wrapper verificado e falhas de recuperação. Políticas web/workflow, 10 testes de escopo e 12 de classificação aprovados. OpenSpec 1.14.0 estrito: 122/122. Dois Code Reviews somente leitura sem defeitos acionáveis; ver `validation.md`. Nenhum teste ou comando SSH executado contra produção. CI/merge ainda pendentes.

## Fora desta autorização

Produção da dependência permanece na task 3.2 da change de segurança. Nenhum fetch, recibo, marcador, tag, lock, container ou banco na Oracle será modificado nesta fase. Não sincronizar/arquivar specs sem revisão humana.
