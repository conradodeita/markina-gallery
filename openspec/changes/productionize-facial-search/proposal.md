## Why

O benchmark privado já comprovou no ARM a capacidade de indexar o acervo real, e insistir em corrigir duas fotos terminais não altera essa conclusão. O próximo risco relevante é operacionalizar o reconhecimento facial como recurso de produto: retirar o acoplamento aos scripts temporários do benchmark, concluir a experiência autenticada da cliente e preparar uma ativação de produção gradual, observável e reversível.

## What Changes

- Encerrar o ciclo de benchmark privado com evidência agregada e prova de limpeza, removendo do caminho normal de deploy e runtime os modos, trailers e estados criados exclusivamente para a medição.
- Manter `FACIAL_PROCESSING_ENABLED` como kill switch técnico por ambiente, com homologação apta a permanecer ativa para validação funcional e produção inicialmente desligada até todos os gates desta change serem aprovados.
- Tornar deploy, upgrade e rollback do `face-worker` compatíveis com o estado facial persistente do ambiente, sem janela de benchmark, porta adicional ou intervenção em recursos de terceiros.
- Consolidar o contrato operacional de produção para indexação automática, progresso/cobertura administrativa, busca autenticada da cliente, retomada após sair da página e resultados ordenados no topo.
- Permitir que a cliente escolha explicitamente uma foto JPEG já existente no celular ou abra a câmera, usando um diálogo mobile-first coeso em vez do controle nativo de arquivo exposto.
- Aceitar referências JPEG de até 30 MB com o mesmo limite efetivo no navegador e na API, margem de transporte no proxy e mensagem específica antes do envio quando o arquivo exceder esse limite.
- Validar admissão durável e backpressure para pelo menos 100 consultas simultâneas, com limites, SLOs, métricas agregadas e alertas que não exponham imagem, vetor, score ou PII.
- Formalizar os gates de produção para segurança, calibração, equidade, base legal, consentimento, representação de menores, retenção, revogação, atendimento a direitos e resposta a incidente.
- Executar rollout progressivo e reversível, começando por contas/galerias explicitamente permitidas e expandindo somente após evidência técnica, jurídica e humana registrada.

## Capabilities

### New Capabilities

- `privacy-biometric/facial-production-runtime`: ciclo de vida do reconhecimento facial em produção, incluindo gates de ativação, indexação e busca, privacidade, observabilidade, capacidade, rollout e rollback.

### Modified Capabilities

- `deployment-operations`: permitir deploy e upgrade zero-impact do subsistema facial conforme o estado autorizado de cada ambiente, eliminando o acoplamento operacional ao benchmark privado encerrado.
- `client-access/derived-galleries`: incorporar a busca facial autenticada como entrada opcional para a seleção individual, sem criar galeria privada, pedido ou vínculo adicional antes da escolha explícita da cliente.

## Impact

- Backend facial, configuração, filas, retenção, auditoria, autorização e endpoints administrativos/da cliente.
- Frontend administrativo e público autenticado, com progresso, retomada e grupos de resultados.
- Docker Compose, workflows de CI/CD, scripts de deploy/rollback e documentação operacional.
- PostgreSQL, Redis e `face-worker`, preservando isolamento de rede, recursos e dados dos demais projetos.
- Processo humano de aprovação jurídica, segurança, calibração e rollout antes de `FACIAL_PROCESSING_ENABLED=true` em produção.
