# Tasks

## 1. Diagnóstico e decisão

- [x] 1.1 Reproduzir as três referências autorizadas e o controle por toque; registrar estados, contadores e lifecycle sem imagens/vetores no Git. Evidência em validation.md e registro da investigação anterior.
- [x] 1.2 Conferir versão, pesos, configuração não secreta, integridade do índice e rejeição do par positivo em transação remota somente-leitura. Evidência em validation.md.
- [x] 1.3 Delimitar rolagem da busca por toque versus upload e identificar o bloco de resultados abaixo da capa. Evidência estática em validation.md; validação visual do comportamento corrigido permanece em 4.2.
- [x] 1.4 Receber revisão humana da faixa inicial de possibilidades 500 e da navegação ao bloco de resultados. Proprietário respondeu em 17/10/2026: “Aprovar a proposta e implementar”; posteriormente pediu também mínimo 600 por toque, reconhecendo possíveis pessoas erradas. Isso não constitui calibração formal nem aprovação operacional de deploy.

## 2. Correspondência de referência enviada

- [ ] 2.1 Implementar configuração opcional e escolha de faixa por origem SFace (upload/câmera 500, toque 600); preservar correspondências firmes, Gemma e critérios gerais existentes. Criar regressões de limites/classificação, origem/engine e desativação.
- [ ] 2.2 Verificar isolamento, snapshot, fingerprints, retenção e ausência de scores/vetores na API/logs pelos testes relevantes do CI.

## 3. Apresentação do resultado

- [ ] 3.1 Unificar acompanhamento das consultas iniciadas na página, incluindo confirmação recuperada de upload; conduzir ao bloco e fechar ampliação uma única vez quando `ready` possui candidatas renderizáveis.
- [ ] 3.2 Cobrir no CI upload/câmera, toque, percentual 100 antes de ready, consulta restaurada, repetição de polling, falha/ausência de candidatas, foco e carga tardia de fotos.

## 4. Integração e entrega

- [ ] 4.1 Revisar diff, validar OpenSpec, executar os gates aplicáveis pelo CI (backend, frontend, lint/typecheck/build e políticas operacionais) e corrigir falhas relacionadas.
- [ ] 4.2 Preparar inventário/plano e publicar somente após aprovação operacional protegida; repetir os casos autorizados e confirmar visualmente o direcionamento aos resultados. Registrar revisão humana das possibilidades e seus limites.
- [ ] 4.3 Reconciliar evidência final, bloqueios e rollback; sincronizar/arquivar somente após revisão humana.
