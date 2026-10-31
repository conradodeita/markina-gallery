# Evidência da preparação

Em 30/10/2026 a preparação foi autorizada, com execução Oracle dependente de nova autorização. A change foi validada com OpenSpec strict; somente proposal/design/specs/tasks foram preparados nesta fase. O executor e o rehearsal desta nova change NÃO estão implementados e suas tasks permanecem abertas.

Evidência reutilizável: candidato ARM64 ef5105e0 e relatório da change prepare-coordinated-python-security-release/preview-worker-preparation-20261030.md. Sessão anterior registrou 29 testes da preparação, pip check, comparação de 60 distribuições e renderização sintética JPEG/PNG idêntica. Esses resultados NÃO comprovam a manutenção operacional proposta.

Inspeção somente leitura do container ativo nesta fase confirmou PID1 python -m app.preview_adjustment.worker e ausência de handler cooperativo no módulo. A API e o worker geral permaneciam saudáveis, assim como o worker de prévias; nenhuma pausa foi solicitada. Dependências, checkout e imagens Oracle não foram alterados.

A revisão de código delimitou produtores adicionais em app/folder_processing.py, app/folder_processing_api.py, app/media.py e app/facial/worker.py. Isso sustenta recusar opcionais produtores ativos e isolar API/worker antes de confiar em fila momentaneamente vazia.

O bloqueio de publicação continua real: executor/recovery específico ainda não implementado/homologado e política de callbacks durante a janela pendente. A preparação técnica aprovada pelo usuário não equivale à autorização da janela.
