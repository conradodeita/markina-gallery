## Why

O proprietário solicitou avaliar `google/embeddinggemma-2` para identidade facial e pesquisa multimodal, sem substituir o motor atual por antecipação. O projeto já usa YuNet + SFace, possui benchmark sintético anterior e ainda não tem evidência de identificação em corpus real anotado. A avaliação precisa separar identidade facial de recuperação semântica e preservar o runtime vigente.

## What Changes

- Criar protocolo reprodutível para comparar o motor atual YuNet + SFace, EmbeddingGemma 2 e, se licença de código e pesos for comprovada, um reconhecedor facial adicional.
- Implementar um único seletor global “Usar SFace/Usar Gemma”, restrito a PlatformOwner + InstallationOperator e preservando namespaces independentes por modelo.
- Ao selecionar Gemma, indexar somente galerias criadas após a ativação; galerias antigas ficam em SFace. Galerias novas sem cobertura Gemma completa também usam SFace integralmente.
- Fixar o engine selecionado em cada consulta por referência enviada ou rosto clicado, sem misturar dimensões nem namespaces. O seletor é reversível e não dispara backfill.
- Comparar imagem inteira, recorte facial alinhado e recorte com contexto, usando as mesmas fotos, detecções, partições e identidades.
- Medir qualidade de identificação e rejeição, desempenho, memória, dimensões e limiares em corpus real autorizado, com resultados separados por dificuldade quando os rótulos permitirem.
- Priorizar identidade facial e operação do produto: indexação antecipada após upload, busca por foto de referência e filtro acionado ao tocar em rosto, com vários fotógrafos/clientes concorrentes.
- Não usar busca de cenas por texto (por exemplo, “casal se beijando”) como critério de escolha do motor de identidade; registrar esse possível uso multimodal como fora do objetivo desta avaliação.
- Entregar integração local reversível para teste privado; nenhum deploy, ativação remota ou processamento de fotos acontece nesta implementação sem autorização operacional específica por execução.

## Capabilities

### New Capabilities

- `privacy-biometric/embedding-engine-evaluation`: protocolo isolado para avaliar embeddings de identidade facial sem alterar o motor em execução.

### Modified Capabilities

- `privacy-biometric/embedding-engine-evaluation`: acrescenta pipeline paralelo, persistência versionada separada e controle global pelo proprietário técnico.

## Impact

- Backend facial, migration aditiva, worker isolado, dependência/modelos locais fora do Git, interface administrativa e harness de benchmark; relatório agregado sem fotos, embeddings ou identificadores pessoais.
- Execução real depende de corpus fornecido pelo fotógrafo/administrador, ground truth e registro da origem, finalidade, autorização e controles de acesso, criptografia, retenção e exclusão para aquela execução.
- A autorização posterior do proprietário em 11/10/2026 para continuar, fazer push, merge e deploy acrescenta a publicação em homologação e o provisionamento isolado do runtime no servidor inventariado. Não autoriza produção, alteração de segredos, backfill ou benchmark com fotografias reais sem o lote e a autorização próprios.
