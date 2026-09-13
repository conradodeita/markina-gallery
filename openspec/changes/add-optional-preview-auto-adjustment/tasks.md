## 1. Persistência e contrato do motor

- [x] 1.1 Criar modelos exclusivos e migration aditiva; verificar criação, constraints, padrão desligado e cascata em banco temporário. Evidência: teste isolado de metadata, configuração e cascata aprovado; execução da cadeia Alembic será verificada em 4.1.
- [x] 1.2 Implementar adaptador RawTherapee com perfil moderado versionado, timeout, diretório temporário e mistura; verificar contrato do subprocesso e preservação da entrada. Evidência: contrato simulado verifica ausência de shell, timeout 90 s, uma thread, mistura e entrada intacta; motor real pertence à task 4.2.

## 2. Processamento e reversão

- [x] 2.1 Implementar fila idempotente, reserva recuperável, publicação condicionada e agendamento isolado após prévias; testar falha, desligamento em execução, mudança de proteção/fonte e repetição. Evidência: nove testes focados aprovados em 31,49 s; cenários incluem exclusão em execução, ausência do resultado, reserva abandonada e preservação byte a byte dos derivados convencionais.
- [x] 2.2 Integrar resolução nas rotas de foto públicas/privadas autorizadas e comparação administrativa; testar fallback, acesso indevido e não alteração da entrada facial/convencional. Evidência: 17 testes do módulo aprovados em 57,20 s, incluindo acesso público com registro/pasta liberada, privado com vínculo, comparação admin, desligamento imediato e preservação byte a byte.
- [x] 2.3 Integrar exclusão de arquivos e CLI de inventário/limpeza exclusiva; testar que originais, prévias convencionais e dados comerciais permanecem preservados. Evidência: testes do módulo cobrem cleanup, exclusão de foto e manifesto com referência privada preservada; três testes existentes de exclusão/lifecycle aprovados na execução integrada focalizada.

## 3. Operação e interface

- [x] 3.1 Adicionar painel administrativo com chave, intensidade, progresso por galeria, processamento paginado e antes/depois; validar interações e layout responsivo com testes focados e inspeção disponível. Evidência: 12 testes frontend aprovados em 19,62 s; navegador Chromium com API simulada em 390/768/1440 px, sem overflow no painel nem erro JavaScript; comparação empilhada no mobile e em duas colunas no desktop. Capturas locais inspecionadas; não representa avaliação das fotos reais.
- [x] 3.2 Entregar worker/Compose opcionais com limites e manual de ativação, desligamento e retirada; validar configuração e documentar licença/runtime. Evidência: build Docker real aprovado, override validado com config --quiet; manual em docs/MODULO-AJUSTE-DE-PREVIAS.md. Imagem exclusiva sem alterar serviços/portas existentes.

## 4. Validação integrada

- [x] 4.1 Executar testes direcionados backend/frontend, lint, typecheck, build aplicável, migration temporária, OpenSpec estrito e revisão do diff; registrar evidências e limitações. Evidências detalhadas no manual: checkpoint de 67 testes mídia/módulo; rodada final 17 módulo + três lifecycle + 12 frontend aprovados; Ruff, ESLint/typecheck, build frontend, cadeia Alembic temporária até 0054, OpenSpec estrito e diff revisados. Apenas avisos de depreciação/imagem preexistentes. Nenhuma suíte geral executada.
- [ ] 4.2 Validar motor real em amostra e obter avaliação estética do fotógrafo antes de recomendar ativação ampla; registrar tempo e resultado sem extrapolar o benchmark facial.

## Continuidade

- Implementação na branch `codex/optional-preview-auto-adjustment`. Em 13/09/2026, o proprietário autorizou especificamente push, merge e deploy em homologação mantendo o módulo desligado. Inventário somente-leitura conferido e apresentado; confirmação pós-inventário recebida conforme DEPLOY.md, incluindo não iniciar o worker.
- Parte técnica de 4.2 aprovada com RawTherapee 5.9 em contêiner descartável, sem rede, amostras sintéticas 640×420, 0,5 CPU/768 MiB: 1,211 s subexposta, 0,791 s equilibrada, 0,735 s baixo contraste. Entrada intacta e resultado visualmente inspecionado. O smoke identificou a necessidade de `-a` para aceitar PNG, incorporada ao adaptador e ao teste de contrato.
- Repetição na imagem final, sem montar o código do adaptador: 1,340 s / 0,913 s / 0,637 s; sucesso nos três casos. Docker image ID manifest `sha256:09672b786f1fab18d8ad9170dfd672c95d4598289b22916839d90b87b20efa0e`. Sem serviço remoto modificado.
- Bloqueio humano de 4.2: avaliar antes/depois em fotografias escolhidas pelo fotógrafo. Sintéticos não comprovam qualidade estética em pele, eventos ou condições variadas; host local não mede capacidade ARM do servidor. Não recomendar ativação ampla nem marcar 4.2 concluída antes dessa avaliação.
- Revisão humana, sincronização de specs principais e arquivamento ainda não realizados. Não executar suíte geral local nem benchmark de escalabilidade; os gates obrigatórios existentes do CI permanecem inalterados.

## 5. Publicação autorizada

- [ ] 5.1 Registrar inventário e publicar commit/PR focados; acompanhar os gates obrigatórios existentes, sem desativar proteções nem incluir outros trabalhos.
- [ ] 5.2 Após confirmação do inventário, integrar em develop e publicar pelo pipeline de homologação; verificar SHA, migration 0054, serviços/healthchecks e configuração desligada sem iniciar worker ou agendar fotos reais.
