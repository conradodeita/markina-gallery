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

- [x] 3.1 Unificar acompanhamento das consultas iniciadas na página, incluindo confirmação recuperada de upload; conduzir ao bloco e fechar ampliação uma única vez quando `ready` possui candidatas renderizáveis. CI #39050114763 (`a0359be`): frontend aprovado.
- [x] 3.2 Cobrir no CI upload/câmera, toque, percentual 100 antes de ready, consulta restaurada, repetição de polling, falha/ausência de candidatas, foco e carga tardia de fotos. CI #39050114763: 549 testes frontend, lint, TypeScript e build aprovados; teste visual remoto permanece em 4.2.

## 4. Integração e entrega

- [x] 4.0a Receber revisão da preparação operacional restrita: proprietário respondeu “Aprovar a preparação do gate restrito” em 17/10/2026, preservando inventário/aprovação final antes de mutação remota.
- [x] 4.0b Preparar manifesto/listas exatas, verificação de Compose no inventário/release, pin versionado e regressões negativas/positivas no CI; manter autorização operacional falsa e wrapper remoto intacto. CI #39050114763: política de inventário/publicação aprovada, incluindo equivalência Compose arquivo/stdin, recusas de autorização/hash/manifesto e arquivo fora do escopo.
- [ ] 4.1 Revisar diff, validar OpenSpec, executar os gates aplicáveis pelo CI (backend, frontend, lint/typecheck/build e políticas operacionais) e corrigir falhas relacionadas.
  - CI inicial identificou hashes anteriores no manifesto de manutenção. Preparar hashes atuais com autorização operacional falsa, preservando validação de escopo e gates; repetir CI.
  - Revisão posterior aprovada: “Integrar na develop atual e validar”. Integrar `25cd338` preservando schema 0083 e mudanças externas, redirecionar PR e repetir gates afetados; não reaproveitar a validação backend incompleta da base anterior.
- [ ] 4.2 Preparar inventário/plano e publicar somente após aprovação operacional protegida; repetir os casos autorizados e confirmar visualmente o direcionamento aos resultados. Registrar revisão humana das possibilidades e seus limites.
  - Inventário posterior encontrou deploy externo em develop `25cd338` e schema 0083. Plano anterior de produção/main/0082 bloqueado; proposta de redirecionar integração para develop e usar homolog protegido aguarda revisão do proprietário. Não reverter a atualização externa.
- [ ] 4.3 Reconciliar evidência final, bloqueios e rollback; sincronizar/arquivar somente após revisão humana.
