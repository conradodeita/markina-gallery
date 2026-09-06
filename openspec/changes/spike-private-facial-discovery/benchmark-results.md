# Resultados reproduzíveis do benchmark facial

## Execução

- Data: 2026-09-05.
- Corpus: 540 JPEGs sintéticos, 16 adultos ficcionais, sem dados reais ou de crianças.
- Catálogo do Evento A: 504 fotos, 544 rostos esperados.
- Sentinelas do Evento B: 4 fotos, usadas para teste de isolamento.
- Consultas: 32, duas poses por identidade.
- Modelo: OpenCV YuNet `2023mar` + SFace `2021dec`.
- Runtime: Python 3.12.9, NumPy 2.2.6, OpenCV headless 4.12.0.88, Pillow 12.0.0 e psutil 7.1.3.
- Host de desempenho: Windows 11 AMD64.
- Relatório efêmero bruto: 20.135 bytes, SHA-256 `7427809A16CED82BEFB27D9928D79704A6BB6EA5F9441EBFFEC03AF7F950D650`; removido após esta consolidação por conter somente detalhe técnico intermediário.

O corpus foi construído deterministicamente pelo `dataset.py`, verificado por hashes e processado pelo `harness.py` sem banco, API, Redis, worker ou importação do produto. O relatório confirmou `created_commercial_entities: 0`, `contains_embeddings: false` e zero violações de isolamento.

## Cobertura e operação

| Medida | Resultado AMD64 |
|---|---:|
| Cobertura de detecção | 544/544 (100%) |
| Fotos negativas com detecção indevida | 0/8 |
| Falhas de indexação | 0/504 |
| Tempo de indexação | 142,991 s |
| Throughput | 3,525 fotos/s |
| CPU / tempo de parede | 2,037 |
| RSS inicial / final | 81.059.840 / 170.647.552 bytes |
| Variação de RSS | 89.587.712 bytes |
| Tamanho dos JPEGs | 13.995.315 bytes |
| Tamanho dos modelos | 38.928.942 bytes |
| Embeddings no índice | 544 × 128 `float32` |
| Tamanho mínimo estimado dos vetores | 278.528 bytes |

O tamanho estimado cobre somente os vetores densos; um armazenamento de produto terá overhead de metadados, índice, UUID, versão e criptografia. O uso de CPU acima de 1,0 indica paralelismo interno do OpenCV. A variação de RSS é uma aproximação início/fim, não pico amostrado.

## Curva de limiar

As contagens agregam cada foto relevante por consulta. Similaridade não é porcentagem de identidade.

| Limiar | Precisão | Recall | Top-1 | FP | FN | Consulta mediana |
|---:|---:|---:|---:|---:|---:|---:|
| 0,300 | 8,07% | 100% | 100% | 12.386 | 0 | 5,12 ms |
| 0,363 | 10,18% | 100% | 100% | 9.595 | 0 | 8,36 ms |
| 0,500 | 27,80% | 100% | 100% | 2.825 | 0 | 5,39 ms |
| 0,600 | 62,85% | 100% | 100% | 643 | 0 | 2,66 ms |
| 0,650 | 88,53% | 100% | 100% | 141 | 0 | 3,76 ms |
| 0,700 | 98,37% | 99,91% | 100% | 18 | 1 | 3,68 ms |
| **0,750** | **100%** | **98,62%** | **100%** | **0** | **15** | **3,08 ms** |
| 0,800 | 100% | 89,71% | 100% | 0 | 112 | 3,23 ms |
| 0,850 | 100% | 65,17% | 100% | 0 | 379 | 3,54 ms |
| 0,900 | 100% | 39,98% | 100% | 0 | 653 | 2,71 ms |
| 0,950 | 100% | 10,85% | 93,75% | 0 | 970 | 2,50 ms |

O ponto `0,750` é o candidato conservador deste corpus porque eliminou falsos positivos e manteve recall alto. Ele não é limiar de produção: o corpus deriva de folhas sintéticas e pode superestimar similaridade intrapessoal, subestimar diversidade real e não medir equidade demográfica.

### Cenários no limiar 0,750

| Cenário | Precisão | Recall | FP | FN |
|---|---:|---:|---:|---:|
| Limpeza | 100% | 100% | 0 | 0 |
| Iluminação | 100% | 100% | 0 | 0 |
| Desfoque | 100% | 98,96% | 0 | 2 |
| Baixa resolução | 100% | 94,79% | 0 | 10 |
| Oclusão | 100% | 98,44% | 0 | 3 |
| Grupo | 100% | 100% | 0 | 0 |

## ARM64

Um primeiro smoke em container `python:3.12-slim` sob emulação local informou `aarch64`, instalou as dependências fixadas, carregou os dois pesos, detectou um rosto sintético e produziu um vetor de 128 dimensões.

Após autorização humana, o benchmark completo foi repetido no Oracle físico usado pela Markina. O host possui quatro CPUs ARM Neoverse-N1; o container efêmero ficou limitado a 2 CPUs, 1 GiB de memória e 256 processos, sem portas, Compose, banco ou volume da aplicação. Resultado:

| Medida | Oracle ARM64 físico |
|---|---:|
| Plataforma | Linux `aarch64`, Python 3.12.14 |
| Cobertura / falhas | 544/544 (100%) / 0 |
| Tempo de indexação | 35,093 s |
| Throughput | 14,362 fotos/s |
| CPU / tempo de parede | 1,921 |
| RSS inicial / final | 99.614.720 / 232.304.640 bytes |
| Variação de RSS | 132.689.920 bytes |
| Consulta mediana em 0,750 | 0,943 ms |
| Precisão / recall / top-1 em 0,750 | 100% / 98,62% / 100% |
| Falsos positivos / negativos em 0,750 | 0 / 15 |
| Violações de isolamento | 0 |

O relatório agregado ARM possuía 19.453 bytes e SHA-256 `92a9d5b97d37dbccd91204374ceae3101dbe259668f5a0cf7fadc16116c9f065`. Ele foi removido junto do corpus após a consolidação. Os containers Markina e os demais projetos não foram reiniciados ou alterados.

## Estados e testes negativos

Testes automatizados verificaram referência sem rosto, múltiplos rostos, baixa qualidade, falha técnica, referência pronta, filtragem estrita pelo evento e ausência dos campos de galeria privada, seleção, vínculo e autorização. O benchmark real também registrou estado `ready` separado para os dois índices; falhas seriam reportadas como `partial` ou `failed` sem bloquear a disponibilidade da foto.

## Limitações

- Adultos sintéticos não permitem concluir desempenho com crianças, vieses demográficos ou qualidade de evento real.
- Transformações derivadas de duas folhas não substituem poses e câmeras independentes.
- O benchmark executa busca linear em memória; índice vetorial, concorrência, fila e criptografia acrescentarão custo.
- O pico real de memória não foi amostrado continuamente.
- O candidato AdaFace não foi medido porque a cadeia comercial dos pesos não foi comprovada.
- O limite de 2 CPUs/1 GiB torna a medição ARM conservadora; concorrência com uploads reais ainda deve ser validada antes de habilitar a fila em homologação.

Essas limitações impedem habilitação em clientes, mas não invalidam a decisão de manter YuNet + SFace como único baseline elegível para um próximo piloto controlado.

## Validação e limpeza final

Em 2026-09-05:

- `ruff` aprovou todos os scripts do spike;
- `pytest scripts/face_spike -q` aprovou 7 testes;
- `openspec validate spike-private-facial-discovery --strict` aprovou a change;
- `git diff --check` não encontrou erro de whitespace;
- corpus, relatório bruto, modelos e ambiente virtual efêmeros foram removidos;
- a busca por diretórios temporários retornou `TEMP_REMAINING=0`;
- nenhum container de smoke permaneceu em execução;
- a busca no repositório por JPEG, PNG, ONNX, NPY, NPZ, SQLite ou DB retornou `REPO_BIOMETRIC_ARTIFACTS=0`;
- nenhuma migration, rota, API, worker, interface ou feature flag do produto foi criada ou habilitada.
