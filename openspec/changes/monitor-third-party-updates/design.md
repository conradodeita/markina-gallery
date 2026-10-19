# Design

## Reconciliação e proveniência

O ponto de partida é o SHA `d06dcc7460b69188833a79e39a7b05fa694410ea`, confirmado via `git ls-remote origin refs/heads/main` em 19/10/2026. Inventariar o código e registros datados presentes nesse commit. A verificação documentada em `openspec/changes/evaluate-embeddinggemma-face-search/validation.md` de 11/10/2026 provou que `face-gemma-index-worker` ficou healthy, com pesos e marcador verificados, heartbeat presente e telemetria ativa; também provou `global_engine=SFace`, zero jobs/vetores Gemma e ausência de backfill. Isso comprova uma execução experimental em homologação naquela data, não uso do modelo nem o estado atual. Não presumir que o nome de container significa inferência ou índice ativos.

Como não há sessão SSH local fornecida, nem a inspeção remota será iniciada por outra rota que exija ler segredos/configurações; runtime atual será explicitamente não confirmado. A configuração de inventário remoto atual não cobre worker/modelo Gemma.

## Atualizações ordinárias

Usar Dependabot nativo, sem Renovate concorrente: gera PRs apoiados pelos lockfiles e manifests, utiliza a automação já oferecida pelo GitHub e não requer novo serviço. Um arquivo `.github/dependabot.yml` agenda versões semanalmente, agrupa por ecossistema, limita PRs abertos, acompanha `npm`, `pip`, Dockerfiles/Compose e GitHub Actions e desabilita merge automático. Bibliotecas Python de runtime Gemma podem receber PR agrupado sob revisão; mudanças de pesos/revisão de modelo, detector/reconhecedor facial e motores de fotografia não recebem PR automático. Atualizações de segurança permanecem separadas e imediatas conforme configuração de segurança do repositório.

## Relatório semanal

Workflow `schedule` no GitHub-hosted runner lê PRs Dependabot e alertas de segurança via REST API com permissões mínimas de leitura. Publica resumo no job summary, não abre issue/PR e não envia mensagens. Um relatório vazio registra data/origem e ausência de PRs/alertas observáveis; isso não equivale a provar que todas as fontes foram consultadas ou que não há update. API 403/5xx, paginação incompleta ou fonte inacessível é estado de falha/não confirmado, separado de lista vazia. Erro de API faz workflow falhar para não parecer saudável.

## Especializados e bloqueios de qualidade

O inventário registra pesos YuNet/SFace, OpenCV/NumPy, EmbeddingGemma 2 e pilhas PyTorch/Transformers, LightCraft/RawTherapee, Evolution API, imagens e runtime. Candidatos para modelo/peso, engine facial e conversor RAW aparecem como avaliação manual no relatório/inventário; não são transformados automaticamente em PR. Permanecem ligados a eficácia/calibração/licença, compatibilidade, recursos, corpus autorizado e rollback conforme OpenSpec específico.

## Sem efeito em produção

Workflow somente de leitura; sem SSH/Oracle, Docker Compose de deploy, migrations, tokens de operador, publicação de imagem ou passos automáticos de merge. O CI normal valida código/testes/OpenSpec. A existência de `dependabot.yml` não modifica versão instalada; PRs dependem de revisão e merge humano. Alertas e update PRs de segurança do Dependabot dependem das funcionalidades do GitHub no projeto e serão verificados separadamente sem alterar configuração de conta.
