# Evidências e limites — atualização 20/09/2026

## Implementação local

Migration 0057 aditiva, sem execução em banco operacional. Fonte opt-in com reserva durável antes da escrita, hash, quotas serializadas por advisory lock PostgreSQL, EXIF, rename atômico, fila facial anterior à mídia, TTL e remoção condicionada. Reenvio verifica capacidade novamente; chave de job é digest limitado. MediaJob high-res recupera interrupções após 10 minutos e falhas após 30 segundos, com três tentativas por geração. Fragmentos `.pyp-uploading/*.part` são removidos somente após TTL e dentro da raiz de mídia. Desligar a flag impede novas admissões; não autoriza redetecção de previews aderentes.

YuNet global/multiscale/tiles seletivos, NMS, alinhamento no original orientado e SFace cifrado; orçamento inicial de 64 tiles, 2048 candidatos e 256 embeddings, com saturação registrada. Novos campos de região preservam FK foto/galeria e geometria normalizada. Consulta por UUID reaproveita consentimento, autorização, fila, snapshot e purge. Selfie continua no fluxo existente. Nenhum modelo EdgeFace foi integrado.

Preview Auto Adjustment existente preservado, com limpeza da fonte pelo worker de mídia (o worker de ajuste não monta a fonte). Worker de índice recebe volume de fonte somente para leitura. Derivados novos: maior lado 1980, thumbnail 480, JPEG adaptativo quality 90→75, alvo flexível de 250 KB. Limpeza usa SKIP LOCKED para não aguardar um índice ativo no worker compartilhado. Fragmentos têm diretório próprio para evitar varrer todo o acervo e contam conservadoramente na admissão. Upload público usa hash do conteúdo dentro da pasta para retomada sem novo ativo. Endpoint administrativo `/admin/photo-assets/{id}/facial-analysis` expõe somente lifecycle e métricas permitidas.

## Validação executada

- Baseline antes da implementação: 39 testes de provider/engine/indexing/Auto Adjustment, 164,68 s, três avisos preexistentes.
- Migration com preservação de ciphertext/versão/ID de região legada sem inventar bbox (teste reforçado: 1 aprovado, 34,54 s): upgrade completo → downgrade 0056 → upgrade completo, SQLite descartável, sem perda da tabela de fotos. A última execução conjunta com lifecycle/benchmark teve 18 testes aprovados, 27,72 s.
- Lifecycle/configuração/benchmark/regiões: 25 testes aprovados, 12,59 s; ampliação posterior lifecycle/regiões/purge: 26 aprovados, 20,84 s; recuperação do worker e limpeza de referência: 22 aprovados, 10,89 s.
- Testes novos cobrem quota/reenvio, legado sem credenciais faciais, EXIF e alinhamento original, tiles/bordas/NMS, fluxo antes da mídia, ajuste antes de descarte, fragmentos órfãos, flags, falhas limitadas, consulta sem provider/arquivo, modelo incompatível, cross-gallery, sessão ausente, consentimento, menores e revogação.
- Fluxo integrado de serviços: admissão JPEG sintético → worker facial → derivados → descarte → região autorizada → busca no índice → purge com prova limpa. Provider sintético controlado; não mede precisão.
- Frontend completo: 43 arquivos, 295 testes aprovados com `--maxWorkers=2`, 114,09 s. Primeira execução concorrente apresentou timeout em teste preexistente de correção financeira; teste isolado e suíte completa repetida passaram. Não alterado o comportamento financeiro.
- TypeScript e build de produção Next.js aprovados, 20 páginas estáticas geradas. ESLint sem erros. Ruff sem erros nos arquivos alterados. OpenSpec `validate --strict` e Compose `config --quiet` aprovados.
- Navegador real, fixture local usando os componentes reais: desktop e viewport 390×844, seis figuras sintéticas, abertura sem overlays, ativação explícita, alinhamento, zoom 150%, pan por teclado, exclusão de região fora do viewport, clique retornando o UUID correto e seleção comercial externa. Fixture/cache fora do Git, sem sessão de cliente nem fotos reais.
- Suíte ampla backend concluída em 20/09/2026: **637 aprovados, 3 ignorados, nenhuma falha**, 3824,57 s (1h03m44s), 640 coletados. JUnit `.codex-tmp/highres-backend-final.xml` e log homônimo. Os 99 avisos são depreciações FastAPI/Starlette e adaptador datetime SQLite. A falha anterior de contrato comparava candidatas sem `match_class`; expectativa corrigida, caso isolado e suíte ampla aprovados.
- Os três skips preexistentes exigem `TEST_POSTGRES_DATABASE_URL` descartável: constraints/rollback de ownership de pasta, reset operacional e ciclo de migration de carrinho. Não executados nesta suíte; não confundir com os quatro testes PostgreSQL específicos high-res, executados separadamente e aprovados. Nenhuma base operacional foi usada.

## Benchmark preliminar

`synthetic-smoke.json`: OpenCV/YuNet/SFace reais, modelos verificados pelo manifesto, três JPEGs cinza de 0,96/24/10 MP sem rostos, Windows x64, uma thread OpenCV. Execução atual em processos distintos: legacy 2,407 s / 422 MB de pico RSS amostrado; high-res 16,425 s / 540 MB. A primeira execução no mesmo processo teve 3,751 s / 432 MB e 37,912 s / 611 MB, respectivamente; a variação reforça que este smoke não serve para dimensionar produção. Global vazio ativa aprofundamento; estes números demonstram custo do caso sem faces, não ganho de recall. Recall é `null`, não 100%. Execução concorrente com validações: inadequada para escolher recursos de produção. NumPy 8000×128 ocupa 4.096.000 bytes, p50 0,723 ms / p95 3,143 ms, sem banco/descriptografia. A medição não autoriza configurações ARM.

## Pendências externas e gates

1. Corpus real: autorização privada recebida nesta conversa. Faltam caminho, origem/finalidade específicas do evento, referências e anotações revisadas. Sugestão de localização: `C:\Users\Conrado\Pictures\Markina-benchmark`, com JPEGs pós-edição e manifesto privado. Não foi criada nem preenchida com fotos encontradas na máquina.
2. Recall real, calibração de detector/query/match e decisão de thresholds continuam não medidos. Usar splits separados; a faixa ambígua fica desabilitada por padrão.
3. EdgeFace: variante/pesos e autorização de uso precisam de decisão, além do corpus. Ver `edgeface-assessment.md`. Sem vencedor ou alegação de melhoria.
4. ARM64 e impacto em API/Postgres/Redis/Evolution/web/ajuste: exigem inventário, plano de impacto zero e autorização remota/deploy. Não executados.
5. Concorrência PostgreSQL validada localmente em container descartável PostgreSQL 16. Falha abrupta do host e operação sob carga em ARM permanecem cobertas pelo gate remoto, sem alegação de validação em produção.
6. Fluxo autenticado real desktop/mobile, produção e aceite humano pendentes. Nenhum deploy, alteração de `.env`, credencial, commit/push, sincronização de specs principais ou archive.

## Continuidade

Preservar alterações preexistentes nas changes configurable-push-and-whatsapp-notifications, fix-purchase-previews-payment-shortcuts-and-expiry e persist-branding-assets-across-deploys e o diretório `.codex-tmp`. Não incluí-las em eventual commit desta change. A regressão ampla terminou sem falhas; não há processo de teste desta execução aguardando resultado. Restam os gates externos 1.3/6.3/6.4/6.5/7.3 e a entrega 7.4–7.5 solicitada posteriormente. Relatório objetivo em report.md; novo inventário/plano em deployment-inventory.md. Não declarar a iniciativa homologada ou ganho de recall comprovado.

## Continuação em 20/09/2026

As sessões anteriores não estavam mais acessíveis após a interrupção; a suíte ampla não deixou resultado final verificável. Foi reiniciada em banco SQLite exclusivo de teste, com log e JUnit persistidos em `.codex-tmp/highres-backend-final.log` e `.xml`. Não aproveitar caches antigos como prova de sucesso.

Esta nova execução terminou às 07:47 de 20/09/2026 (horário local), com 637 aprovados e 3 skips. Alterações de observabilidade e casos adicionados depois da coleta foram cobertos pelas regressões focadas abaixo; seus totais se sobrepõem à suíte ampla e não devem ser somados como testes únicos.

- Frontend atual: 296/297 testes passaram; uma expectativa de texto ainda usava “Foto de referência eliminada”. Ajustada para “Sem imagem temporária nesta busca”, válida também para consulta por região. Os 10 testes desse arquivo passaram no rerun (5,54 s). Restante da suíte já passou no mesmo estado do código de produto.
- PostgreSQL 16 local: imagem oficial já presente; container `markina-highres-test-20260920`, 1 CPU, 384 MB, dados em tmpfs, porta dinâmica só em 127.0.0.1; nenhum volume de aplicação ou rede de outro projeto. Quatro testes passaram novamente após a chave de geração (46,15 s): quota concorrente entre dois processos, replay concorrente da mesma foto com um único job, cleanup SKIP LOCKED e migrations completas upgrade/downgrade/upgrade em schemas sintéticos exclusivos. Fixture ajustada para inserir pais antes de filhos, sem desabilitar integridade referencial.
- Revogação de política oculta regiões imediatamente, mesmo antes de o purge físico executar. 11 testes de regiões passaram (7,66 s).
- Job de indexação high-res usa chave da geração da fonte (timestamp UTC normalizado). Reupload após TTL invalida jobs anteriores sem consumir a nova fonte. 21 testes de engine/lifecycle passaram (11 s), incluindo o cenário de job antigo na fila.
- Regressão de integração: 95 testes aprovados, 393,95 s, JUnit em `.codex-tmp/highres-integration-final.xml`. Detector/lifecycle com passes seletivos: 17 aprovados, 10,59 s.
- Revisão final de observabilidade: falhas de provider agora preservam contagens sanitizadas após rollback e limpam estado entre fotos. Status administrativo da galeria inclui agregados high-res, duração e fila no mesmo escopo; representam a última tentativa por fonte, não histórico nem recall. Teste verifica falha → rollback → retry → sucesso sem dupla contagem ou biometria. Provider/lifecycle/jobs/status: 39 aprovados, 15,39 s, `.codex-tmp/highres-metrics-final.xml`. Mudança posterior ao início da suíte ampla coberta por esta regressão focada.
- Handler de upload high-res: 1 teste aprovado, 4,91 s. Simula falha de escrita após reserva já visível em outra sessão, rollback, reenvio e replay; confirma fonte íntegra, uma análise, um job facial e um job de mídia. Autenticação mockada neste teste de contrato; não substitui E2E autenticado real. Log `.codex-tmp/highres-upload-handler.log`.

O container PostgreSQL de teste foi encerrado e removido automaticamente ao final. Inventário posterior confirmou os mesmos três serviços Evolution, sem alterações. Não houve implantação da aplicação. Ruff/OpenSpec/Compose e diff sem erros na revisão local final.

### Repetir validações

- Backend completo: `python -m pytest backend/tests -q --tb=short --junitxml=CAMINHO_FORA_DO_GIT/backend.xml`, com `DATABASE_URL` apontando exclusivamente para banco descartável; várias fixtures apagam/recriam tabelas. Nunca usar banco de operação.
- PostgreSQL específico: definir `HIGHRES_TEST_POSTGRES_URL` para instância descartável e executar `python -m pytest backend/tests/test_highres_postgresql.py -q`. A suíte gera/remove somente schemas com UUID próprios, usa dois processos reais e mantém constraints habilitadas. Sem a variável, esses quatro testes são explicitamente skipped.
- Frontend: `npm test -- --maxWorkers=2`, `npm run lint -- --quiet` e `npm run build` dentro de frontend.
- Artefatos sintéticos, XML/logs, bases de teste, modelos e fixtures visuais ficam fora do Git. A única evidência JSON versionável desta change é o relatório agregado synthetic-smoke.json, sem fotos ou biometria.
