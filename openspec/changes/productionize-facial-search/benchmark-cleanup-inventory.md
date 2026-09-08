# Inventário de higienização do benchmark facial

Data de corte: 2026-09-08. O lote privado foi fechado pelo workflow `34232853622` no SHA `268bc77ec620809367e64c3266700a667f2ad8ef`. A operação removeu 2.443 embeddings de uma galeria e comprovou zero embeddings, candidatas, referências e notificações pendentes. Fotos, galerias e histórico comercial permaneceram preservados.

## Remover após a migração para rollout persistente

| Item | Motivo | Proteção antes da remoção |
|---|---|---|
| `.github/workflows/facial-homolog.yml` | Orquestra exclusivamente inventário/lote/janela/benchmark privados | Substituir pelas operações persistentes de ativação, suspensão e rollout das tasks 7.1–7.3 |
| `scripts/manage-homolog-facial.sh` | Modos `activate-private`, `reconcile-private`, `resume-private`, `retry-failed-private` e `close-private` pertencem ao lote encerrado | Preservar primeiro inventário, backup, verificação de SHA, reload e rollback em operador genérico de ambiente |
| `scripts/benchmark-homolog-facial.py` | Monitor vinculado a manifesto, quantidade e janela do lote privado | Preservar métricas agregadas úteis em ensaio genérico de carga/SLO |
| `scripts/test_manage_homolog_facial.sh` | Contrato dinâmico dos tokens e modos privados | Substituir por testes do operador persistente |
| `scripts/test_manage_homolog_facial_policy.py` | Asserções estruturais de manifesto, janela e trailers temporários | Migrar somente as proteções de isolamento, segredo, portas e rollback |
| `scripts/test_benchmark_homolog_facial_policy.py` | Política estrutural do monitor de lote | Substituir por política de métricas/SLO sem PII |
| Trailers `Homolog-Facial: pause-legacy-for-private-upgrade`, `pause-private-for-upgrade`, `reconcile-private`, `resume-private` e `retry-failed-private` em `.github/workflows/ci.yml` | Fazem commit controlar ciclo temporário | Deploy deverá preservar o estado autorizado do ambiente sem trailer |

## Generalizar para produção

| Item | Estado atual | Destino |
|---|---|---|
| `scripts/deploy-homolog.sh` | Exige `flag=false/worker ausente` | Aceitar e verificar estados coerentes desligado ou persistentemente habilitado |
| `.github/workflows/ci.yml` | Pausa/retoma por trailers privados | Atualizar API, worker de mídia e workers faciais conforme estado persistente |
| `docker/docker-compose.yml` | Um `face-worker` opcional recebe ambiente facial e metadados privados | Separar classes `search`, `index` e `maintenance`, remover variáveis de lote/janela e manter zero portas |
| `backend/app/facial/config.py` | Kill switch e configuração de produto misturados a `FACIAL_HOMOLOG_*` | Manter configuração técnica; transferir autorização para rollout persistido e representação legal |
| `backend/app/facial/face_worker.py` | Interrompe quando a janela privada expira | Usar kill switch, rollout no claim e classe de worker, sem relógio de benchmark |
| `backend/tests/test_facial_config.py` | Cobre configuração técnica e janela privada | Preservar casos técnicos e substituir cenários privados por rollout/representação |
| `backend/tests/test_facial_search.py` | Fluxo infantil usa configuração privada transitória | Migrar para prova persistida de representação legal |
| `openspec/changes/integrate-private-facial-filter/{design.md,runbook.md,homologation-plan.md,specs/deployment-operations/spec.md}` | Registra o piloto e sua evidência | Preservar como histórico auditável; não usar como runbook de produção |

## Preservar como produto

- Modelos e manifesto verificados, imagem `Dockerfile.face` e licenças.
- `GalleryFacialPolicy`, embeddings cifrados, requests, snapshots, candidatas, outbox e jobs duráveis, sujeitos às migrations aditivas desta change.
- AEAD/AAD por ambiente/galeria/objeto/modelo, rotação de chave e armazenamento temporário cifrado.
- Detecção YuNet/SFace, qualidade técnica, zero rosto como sucesso de indexação e grupos `best|other`.
- Gatilho após `admin_preview` limpa e `client_preview` protegida, idempotência, leases, purge e retenção.
- Progresso/cobertura administrativa, recuperação backend da consulta, seleção pela mutation existente e notificações sem biometria.
- Isolamento Compose `markina-gallery`, Nginx como única porta publicada, limites de CPU/memória, healthchecks, inventário e rollback zero-impact.

## Verificação de escopo

A busca por `FACIAL_HOMOLOG_`, `private_homologation`, tokens `PRIVATE_FACIAL_HOMOLOG`, modos privados, `benchmark-homolog` e trailers `Homolog-Facial:` identificou somente os itens classificados acima. Nenhum arquivo de mídia, seleção, pedido, pagamento, autenticação geral, WhatsApp ou lifecycle de galeria foi classificado para remoção.
