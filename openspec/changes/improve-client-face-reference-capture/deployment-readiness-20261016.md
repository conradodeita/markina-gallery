# Inventário e plano de manutenção — 16/10/2026

## Estado observado

Inspeção SSH somente leitura após o relato do proprietário, sem ler imagens ou embeddings:

- Checkout e versão publicada: `7c7a4ad217343dc4faee57734436afd91bb1f6b1`.
- Banco: `20261016_0082 (head)`.
- Web, API, face-search-worker e Nginx Markina saudáveis. Demais serviços do projeto também saudáveis.
- API e face-search-worker com processamento facial já ativo.
- Domínio: https://markina.pickyourpic.com.br. Nginx do projeto exclusivamente em 127.0.0.1:8080; API e web sem portas publicadas no host.
- POSTs da janela relatada: Android/Chrome recebeu 202 às 18:16:49 e 18:22:45 (America/Sao_Paulo); Windows/Chrome recebeu 202 às 18:28:59. Warnings associados indicam buffering do corpo em arquivo temporário do proxy. Nenhum identificador pessoal ou conteúdo facial foi copiado.

## Plano de impacto e aprovação

O próximo release substitui somente web, API e face-search-worker. Mantém schema, modelos, índice, limiar de similaridade, autenticação, isolamento e retenção. Pode ocorrer breve interrupção ou atraso de fila durante recriação; não se promete indisponibilidade zero desses três serviços.

Antes do preflight do novo SHA, atualizar somente a cópia root-owned do wrapper de inventário Markina para o blob revisado do script. Essa manutenção do comando restrito não altera credenciais, autorização SSH, serviços, portas nem recursos de terceiros. Preservar modo root:root 0755, finais de linha LF e verificar SHA-256 local/remoto.

CI, merge automático e preflight permanecem no GitHub. O preflight remoto deverá confirmar baseline, configuração resolvida, revisão do banco, hashes, saúde e fingerprint. Somente após a aprovação humana no environment production o release revalida fingerprint e publica os três serviços. Não alterar secrets ou .env, firewall, DNS, certificados ou proxy compartilhado.

Rollback: preservar as imagens anteriores dos três serviços e SHA de origem; qualquer restauração exige inventário e aprovação operacional, sem downgrade de dados. O smoke HTTPS repete falhas transitórias dentro de orçamento limitado; indisponibilidade persistente mantém falha e não registra release saudável.

## Validação pendente

Wrapper de inventário atualizado em 16/10/2026 para o blob revisado `8b57f5593d2672bbcac811907337dfece1ed8a33`, com root:root 0755. SHA-256 local/remoto idêntico: `f9f796565535601f10cca1369c80b6acd55c35a7bb099639670f38967553e192`. Nenhum serviço da aplicação foi alterado nesta instalação.

Implementação e regressões serão validadas exclusivamente pelo CI do GitHub. Após publicação, o proprietário deverá confirmar retrato único, fundo com pessoas pequenas, ambiguidade entre dois rostos semelhantes, envio Android e captura em tela cheia. Não há corpus anotado para declarar ganho quantitativo de acurácia. A causa exata da interrupção de resposta no navegador permanece não comprovada.
