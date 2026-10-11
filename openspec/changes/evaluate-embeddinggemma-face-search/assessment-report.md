# Avaliação técnica inicial — EmbeddingGemma 2

## Estado

Avaliação estática concluída em 08/10/2026. Benchmark de identidade com fotos reais não executado: esta change ainda não contém corpus fornecido, ground truth nem manifesto da execução. Nenhuma troca ou alteração do runtime foi feita.

## Arquitetura facial existente

- `backend/app/facial/provider.py`: `OpenCvSFaceProvider`, com detector YuNet e recognizer SFace, modelo versionado como `yunet-2023mar+sface-2021dec`, embedding de 128 dimensões normalizado em L2.
- `backend/app/facial/engine.py`: indexação de rostos observados em fotos, criptografia dos vetores por escopo e comparação por produto escalar entre vetores normalizados, equivalente a cosseno.
- O índice persiste `model_id`, `model_version` e dimensão junto dos envelopes cifrados. A consulta atual filtra modelo `opencv-yunet-sface`, versão/configuração e dimensão 128; não mistura variantes.
- A detecção/alinhamento, medição de qualidade, indexação/consulta em workers separados, autorização por galeria, retenção e purge fazem parte do lifecycle facial atual.
- A abstração `FaceEmbeddingProvider` existe, mas não equivale ainda à interface pedida `FaceEmbeddingEngine` ponta a ponta. `replace_photo_index` exige observações do provider; workers verificam classe concreta; a busca fixa SFace e 128 dimensões. Portanto, a configuração `FACE_EMBEDDING_ENGINE=...` exigiria desenho e implementação posterior, com adaptação de armazenamento/busca versionados, namespaces separados e reindexação explícita. Não implementar isso nesta avaliação.

## Evidência existente e limites

- `openspec/changes/spike-private-facial-discovery/benchmark-results.md`: 540 JPEGs sintéticos e 16 identidades fictícias. No limiar sintético 0,750, SFace registrou precisão 100%, recall 98,62%, top-1 100%, 0 falsos positivos e 15 falsos negativos; não é calibração de produção nem resultado em evento real.
- `openspec/changes/evolve-highres-facial-pipeline/report.md` e tasks associadas: o fluxo high-res foi desenvolvido mantendo SFace; a comparação real SFace/EdgeFace segue pendente por corpus e licença dos pesos.
- `docs/benchmarks/BENCH-20260928-2116-relatorio.md`: o teste de capacidade registrou 2.122 fotos reais, 2,5325 s/foto de inferência facial média e vazão operacional sob carga. O documento expressamente não possui ground truth de identidade para derivar recall, FAR ou precisão. É evidência operacional, não benchmark de reconhecimento.
- Nenhum benchmark do projeto encontrado nesta avaliação mede EmbeddingGemma 2.

## Avaliação do Gemma 2

A documentação oficial descreve `google/embeddinggemma-2` como embedding multimodal compartilhado de 768 dimensões para texto, imagem, vídeo e áudio, 740M parâmetros, Apache 2.0, com truncamento Matryoshka e renormalização após truncamento. O cartão recomenda dimensões 768/512/256/128, mas alerta que 128d é mais apropriado para workloads somente textuais. Esses benchmarks públicos avaliam tarefas gerais multimodais/de recuperação; não provam identidade facial, nem velocidade/custo em acervos de eventos. Fontes: [model card oficial](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2), [guia multimodal oficial](https://ai.google.dev/gemma/docs/embeddinggemma/multimodal-embeddinggemma-with-sentence-transformers) e [guia oficial de inferência](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers).

**Inferência técnica alinhada ao produto:** é viável testar Gemma como gerador de vetores de face crop; não há base para assumir que seu espaço compartilhado agrupa a mesma identidade sob pose, iluminação ou escala facial melhor que SFace. Como o embedding do catálogo é gerado uma vez e reutilizado, o custo dominante será inferência de indexação e peso/residência do modelo; a consulta por foto também precisa ser medida. Ao tocar num rosto indexado, o sistema pode reaproveitar aquele vetor como consulta em vez de regenerá-lo, desde que a interface produto preserve consentimento, autorização e isolamento. O caminho para identidade exige calibração independente, threshold conservador e validação de desconhecidos.

## Candidatos e elegibilidade

| Papel | Candidato | Estado |
|---|---|---|
| A — atual | YuNet + SFace | Baseline implementado; evidência sintética e de capacidade disponível; falta recall/precisão real anotada |
| B — novo | EmbeddingGemma 2 | Apache 2.0 conforme fonte oficial; não integrado nem medido no corpus/carga do projeto |
| C — especialista | SFace é o baseline especializado atual | ArcFace/InsightFace adicional só entra se licença comercial do peso exato e runtime forem comprovados; a avaliação existente excluiu pesos públicos InsightFace/Buffalo por restrição não comercial e EdgeFace Base por CC-BY-NC-SA-4.0 |

Como A já usa um reconhecedor especializado, duplicar SFace como terceiro candidato não seria comparação independente. A comparação mínima tecnicamente honesta é atual SFace contra Gemma; um C adicional depende de checkpoint ArcFace elegível. Não baixar/integrar pesos de licença não aprovada.

## Desenho recomendado

Comparar as mesmas fotografias sob: (A) imagem inteira, (B) face detectada/alinhada e (C) face com contexto. Usar o mesmo detector/bounding box sempre que aplicável, particionar por evento/sessão/câmera para evitar vazamento, e calibrar limiar somente em validação. Medir top-1/top-5, precision/recall, FAR/FPR, FRR/FNR, rejeição correta de desconhecidos, margem top-1/top-2 e métricas por dificuldade com contagem amostral explícita. Comparar Gemma 768/512/256/128 com renormalização; relatar pesos e overhead do índice. Medir ingestão, tempo de fila por lote, latência de busca p50/p95/p99 e throughput sob concorrência representativa de fotógrafos e clientes, além de CPU/RAM/VRAM e custo do modelo residente. O relatório de capacidade existente não comprova fairness entre tenants; isso precisa ser distinguido e medido. A inferência Gemma em CPU/ARM e memória ainda não foi medida; bfloat16 depende de hardware compatível e não deve ser presumido no Oracle ARM CPU.

## Recomendação provisória para este produto

**Manter YuNet + SFace no caminho de identidade até benchmark real autorizado.** Não recomendar `REPLACE WITH EMBEDDINGGEMMA2` com evidência atual. Busca textual de cenas não é o objetivo desta change. Gemma permanece candidato ao caminho de identidade apenas se demonstrar qualidade e eficiência total melhores na indexação antecipada e nas buscas por foto/click sob uso multi-fotógrafo. Isso é status provisório, não a decisão final exigida pela change.

## Forma de experimentação com chave global

É tecnicamente viável oferecer ao proprietário uma chave global para habilitar Gemma sem remover SFace. A arquitetura segura para o primeiro teste é **modo shadow**: os engines geram índices isolados; SFace continua atendendo todos os fotógrafos/clientes; Gemma calcula apenas resultados experimentais agregados para comparação. Desativar shadow interrompe novas tarefas Gemma sem apagar o índice nem alterar SFace. O seletor do engine servido globalmente deve ser separado e bloqueado até a evidência e os gates de privacidade/capacidade estarem completos.

Isso atende o objetivo de experimentar sem uma substituição imediata. A integração shadow está sendo implementada nesta change com provider, fila, imagem/worker separados e painel global. A validação do runtime com os pesos reais e a ativação operacional permanecem pendentes. O controlador não ignora elegibilidade/consentimento/política por galeria. A chave registra seu instante de ativação e não inicia backfill do legado.

## Itens pendentes para completar o relatório solicitado

- Receber diretório/lote exato enviado pelo fotógrafo/administrador e manifesto com origem e finalidade desta execução.
- Receber ground truth pseudonimizado de identidade por foto/rosto, eventos e separação de referência/consulta; indicar quais cenários/categorias estão representados.
- Registrar autorização explícita por esta execução e controles efetivos de acesso, criptografia, retenção/exclusão e presença/ausência de menores.
- Identificar hardware de benchmark pretendido; não usar homologação/produção nem consultar fotografias arbitrárias sem inventário e autorização próprios.
- Resolver proveniência/licença do checkpoint do candidato ArcFace, se for além do SFace atual.

## Atualização de escopo — 11/10/2026

O proprietário escolheu substituir a chave shadow por um seletor global único entre SFace e Gemma. A decisão operacional é não reindexar galerias existentes: somente galerias criadas após a primeira ativação podem usar Gemma. Cada busca usa Gemma somente quando a cobertura da galeria está completa; enquanto indexação estiver pendente, falhar ou divergir, a galeria segue integralmente em SFace. Trocar para SFace pausa novos jobs Gemma sem apagar o índice. O engine fica fixado por consulta e também rege a seleção por rosto clicado. A mudança é local e não habilita deploy ou processamento de mídia; homologação ainda exige autorização explícita por execução e as proteções já documentadas.

## Implementação local e estado de validação — 11/10/2026

O código agora contém provider, namespace 768d, migrations aditivas, worker/profile próprios, seletor único do proprietário, roteamento por galeria e consultas do cliente por referência/região. Isso substitui a descrição estática anterior de busca exclusivamente SFace, sem afirmar alteração no sistema publicado. SFace permanece padrão; acervo antigo não é reindexado.

Monitor e comparador offline foram concluídos localmente. Evidências e comandos estão em validation.md; tarefas operacionais/corpus permanecem abertas em tasks.md. Gemma executará no servidor sem API paga de inferência; há custos de infraestrutura. Licença Apache-2.0 não comprova adequação para identidade facial. Sem inferência com pesos reais/corpus anotado, a conclusão comparativa permanece **INCONCLUSIVA**. Nenhuma recomendação de substituição ou ativação em produção é apresentada.

## Runtime real e publicação autorizada — 11/10/2026

O proprietário autorizou push, merge e deploy restritos à homologação privada. O plano/inventário está em deployment-plan.md; não há autorização de produção, reindexação antiga ou benchmark de fotografias reais. PostgreSQL 0073/0074 foi validado e a inferência ARM64 passou offline com pesos reais na revisão fixada: 768 dimensões normalizadas, 48,656 s na primeira chamada, 34,402 s na segunda e RSS máximo de 4.840,4 MiB sob 1 CPU/6 GiB. A entrada foi sintética; estes valores não demonstram qualidade facial nem eficiência superior ao SFace. O runtime mostrou custo significativo de CPU/RAM. SFace permanece escolha inicial; nenhuma recomendação de substituição é emitida. CI AMD64 e entrega ainda são gates pendentes nesta atualização.

A leitura Gemma da fonte foi separada do lock de PhotoAnalysis após reproduzir bloqueio PostgreSQL do fluxo SFace. Testes concorrentes demonstram conclusão SFace e prévias enquanto Gemma calcula, e rejeição do resultado caso a fonte mude ou seja excluída. O lease exclusivo Gemma está limitado a 900 segundos; SFace mantém 120 segundos. Ver validation.md.
