# Benchmark e limites de interpretação

## Corpus

Autorização privada concedida pelo proprietário em 19/09/2026. Ainda faltam localização, origem do evento e anotações. Pasta sugerida: `Pictures/Markina-benchmark`, fora do repositório. Começar com 30–50 JPEGs pós-edição e ampliar para amostra representativa. Não usar imagens arbitrárias encontradas em caches. Separar calibração/validação; não escolher limiar e anunciar precisão no mesmo conjunto.

Manifesto privado para `scripts/face_benchmark.py`: `synthetic`, autorização com `origin`, `purpose`, `expires_at` UTC e `photos[]` com caminho relativo, `scenario`, `split` (`calibration` ou `validation`) e `faces[]` com `box` normalizada e `subject` pseudônimo local. Nenhum nome, imagem ou vetor entra no Git. Cenários: retrato, poucas pessoas, grupo médio/grande, rosto pequeno, perfil, oclusão, pouca luz, blur e falhas reais. Anotar todas as faces; posição e identidade para retrieval exigem revisão humana.

## Comparação reproduzível

Instalar dependências do ambiente isolado `scripts/face_spike/requirements.txt`. Preparar modelos pelo comando `backend/app/facial/model_assets.py prepare`, usando `backend/facial-assets/model-manifest.json`. Não usar o provider próprio do spike histórico.

Executar `python scripts/face_benchmark.py --manifest CAMINHO/manifest.json --model-root CACHE_VERIFICADO --threads 1 --output RELATORIO_PRIVADO.json`. Para RSS comparável entre pipelines, executar `--pipeline legacy` e `--pipeline highres` em processos novos. O hash do corpus inclui bytes dos JPEGs e manifesto. Repetir com 2/4 threads no host autorizado. `--config` recebe JSON dos parâmetros do detector. Sem manifesto, o comando mede somente matriz NumPy 8000×128; não inclui descriptografia/banco.

- OLD: mesma geração JPEG de admin_preview e mesmo provider limitado do runtime atual.
- NEW: mesmo SFace, mas fonte orientada high-res, global/multiscale/tiles/NMS.
- Detecção: matching bipartido um-a-um com IoU de avaliação 0,5; recall por split/cenário, falsos positivos e duplicatas. Avaliar sensibilidade a IoU e revisar caixas de borda.
- Retrieval: somente detecções associadas ao ground truth, pares positivos/negativos entre fotos, top-1/5/10, distribuição e varredura de thresholds. Não incorporar falha de detecção ao denominador de reconhecimento. Separação atual best/other continua como qualidade secundária.
- Recursos: tempos, CPU do processo, RSS amostrado a cada 10 ms, fotos/min, MP/s e passes por amostra. Incluir aquecimento e repetir em processos novos para comparação decisiva. Pico amostrado pode perder alocações breves.
- Query: registrar estados no mesmo provider. Calibrar tamanho, blur/confiança em referências anotadas; os defaults 72 px/18/0,80 continuam hipóteses legadas, não resultados novos.

## ARM64 e serviços compartilhados

Nenhuma execução remota nesta etapa. Antes: inventário CPU/RAM/disco, limites atuais, portas/subdomínio, SHA, processos Markina e serviços terceiros; autorização explícita. Comparar 1×1, 1×2 e 2×1 processos×threads em lote fixo. Coletar p50/p95 de API, PostgreSQL/Redis, Evolution, nginx/web e Preview Adjustment, idade/profundidade de fila, disco temporário e load average. Manter reservas e reduzir admissão ao exceder SLO definido; não remover limites de container. Resultados Windows não validam ARM.

## Parâmetros iniciais e gates

Global 1600/2 MP; multiscale 2400; tiles 1024, overlap 25%, NMS 0,4, no máximo 64 tiles, 2048 candidatos e 256 embeddings. Saturação é reportada; não implica cobertura completa. Triggers versionados: grupo ≥4, face proporcional <0,06, confiança <0,85, borda ou >8 MP sem retrato grande. São hipóteses configuráveis, não parâmetros escolhidos por benchmark real. Quota inicial 64 fontes/2 GB, reserva 25% do disco e TTL 24h, calibráveis. Flag high-res desligada por padrão. A faixa ambígua é opcional e deve ser ≤ match; nenhum threshold EdgeFace é herdado. Não habilitar produção com estes números sem calibração e aprovação.
