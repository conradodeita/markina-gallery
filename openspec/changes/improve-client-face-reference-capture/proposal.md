# Proposal

## Why

Clientes relatam que buscas por fotos enviadas do dispositivo retornam zero, embora o índice SFace e a busca por regiões indexadas funcionem. O upload já gera um recorte facial alinhado para o embedding, mas limita a resolução antes da detecção; melhorar a aquisição da referência pode preservar informação útil sem reindexar o acervo ou trocar o modelo.

## What Changes

- Preservar upload de fotos antigas e oferecer a câmera como alternativa; ao escolhê-la, a cliente SHALL concluir captura guiada obrigatória antes de iniciar a busca, sem exigir Face Liveness.
- Detectar a referência sob orçamento controlado em resolução/escala adequada e alinhar o rosto a partir dos pixels disponíveis antes de gerar o embedding SFace.
- Orientar a cliente quando a referência não contém um rosto único ou utilizável; não comparar com a galeria até que passe pelas validações técnicas vigentes.
- Manter o índice, as versões de embeddings, o escopo da galeria, o consentimento e a retenção atuais.
- Preparar publicação automatizada pelo GitHub após CI verde, sem contornar inventário, isolamento, aprovação protegida e demais gates de produção existentes.
- Executar ciclos de correção dentro do escopo sem pedir aprovação por push: acompanhar o CI, corrigir falhas verificáveis, publicar novo commit e repetir até os checks ficarem verdes; habilitar merge automático após checks e revisões exigidas.
- Fazer o preflight somente-leitura sem aprovação manual usando credencial de SSH separada e restrita; solicitar uma única aprovação no environment `production` após apresentar inventário, SHA, impacto e reversão, imediatamente antes de qualquer mutação.
- Não executar testes locais conforme preferência do proprietário; a validação automatizada existente do GitHub e a verificação pós-publicação em produção serão registradas separadamente.

## Capabilities

### New Capabilities

- `privacy-biometric/client-reference-capture`: captura, avaliação técnica, orientação e extração temporária do rosto de referência da cliente antes da busca facial.

### Modified Capabilities

- `deployment-operations`: iniciar automaticamente o job de publicação de produção pelo GitHub após CI verde, preservando os gates de inventário, aprovação e impacto zero.

## Impact

- Provider e worker de consulta facial, fluxo de referência no portal cliente e mensagens de qualidade.
- Workflow GitHub de CI/publicação e procedimento operacional de produção; a automação atual em `develop` publica homologação, enquanto o procedimento de produção existente é restrito ao serviço `web`.
- Nenhuma alteração ao índice SFace, fotos indexadas, consentimento, fronteiras de autorização ou dependências externas de reconhecimento.
- Nenhum teste local será executado. A publicação em produção só poderá ocorrer pelo fluxo aprovado após inventário atualizado e gate operacional; o primeiro teste funcional será feito pelo proprietário no ambiente publicado.
- A remoção das aprovações por push não remove a aprovação de produção. O environment protegido continuará exigindo uma revisão humana para cada release, depois que o preflight produzir o inventário revisável.
