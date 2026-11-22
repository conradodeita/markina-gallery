# Release SaaS em produção — 16/11/2026

Operação inicial restrita ao proprietário. Runtime aplicado do commit `9df3b7354c2bd9d5247248b86b25ce79d8256f9e`, schema `20261113_0126`. O proprietário autorizou continuar com merge e deploy enquanto dormia, condicionado à ausência de intervenção necessária.

- [x] PR #366 incorporada e CI 43987596966 aprovado.
- [x] Custódia TOTP na PR #369 incorporada; CI 43996786889 e CI da main 43999779751 aprovados.
- [x] Backup anterior ao corte restaurado em PostgreSQL isolado. Cadeia 0090→0126 com a chave definitiva preservou os seis conjuntos financeiros e o fator TOTP.
- [x] Expand 0092, consumidores intermediários dual-write, consumidores envelope-only, contract/head 0126 e imagens finais aplicados.
- [x] Treze serviços saudáveis. As sete aplicações conservaram as configurações anteriores, com versão e variáveis TOTP explicitamente atualizadas. API e serviços faciais mantêm `APP_ENV=production` e `FACIAL_PROCESSING_ENABLED=true`.
- [x] Fonte de app/migrations conferida nas seis imagens backend, 346 arquivos por imagem, comparando finais de linha normalizados para LF. Arquivos e conteúdos canônicos correspondem à main. O export Git no Windows conserva CRLF em parte da fonte.
- [x] Continuidade observada por 3.196 requisições à saúde da API e página inicial através do Nginx, zero erros e latência máxima 147,81 ms. A prova autenticada sintética anterior percorreu oito fases em cópia isolada, 300 requisições sem erro.
- [x] 68 pedidos, 674 itens, 3 pagamentos de provedor, 6 pagamentos Mercado Pago, 2 contas Mercado Pago e 1 configuração PIX preservados por comparação dos campos anteriores. Permanecem 1 tenant, 1 proprietário, 5.746 fotografias, 8 galerias e 20 pastas.
- [x] 18.891 registros de embeddings conservaram quantidade e conteúdo em comparação com a cópia anterior. Os workers de busca/indexação verificaram os modelos existentes e executaram detecção/embedding de imagem sintética.
- [x] Mercado Pago validou identidade da conta pelo cliente existente, com pagamentos reais habilitados e PIX ativo. WhatsApp terminou com conexão `open` e canal `ready`.
- [x] Backup pós-deploy 0126 restaurado isoladamente; fator TOTP cifrado lido com a chave preservada. SHA256 do dump `ebbd8c55fc1271711f16d99fddd828f033cf0a481e13cfe6b94101d81c0cc9d5`, 126.899.307 bytes.
- [ ] Revisão visual autenticada em produção. Browser permanece com `Trusted RPC service is not configured: browser`; revisão humana e sincronização/arquivamento OpenSpec continuam pendentes.

## Custódia e rollback

A chave dedicada está em `/etc/pyp-totp/keyring.json`, diretório de root com modo 0700 e arquivo com modo 0400. Leitura e recuperação da cópia externa foram comprovadas na operação original. Em atualização posterior, o proprietário informou que moveu a cópia TOTP para `D:\Pick-your-Pic-Recovery TOTP de todos\keyring.json` e que mantém as chaves e credenciais na unidade `D:`. A presença e as permissões do arquivo TOTP no novo caminho foram conferidas sem ler a chave. A pasta NTFS permite a conta Windows do proprietário e SYSTEM. A unidade deve ficar desconectada sob sua guarda.

O loader validado está em `/usr/local/lib/pyp-totp-custody`. Seu uso e recuperação seguem [a operação TOTP](../OPERACAO-SEGREDO-TOTP.md). Preservar as versões de chave exigidas por backups históricos.

Os containers anteriores estão parados como `pyp-saas-previous-<serviço>`. Os intermediários `pyp-saas-envelope-<serviço>` conservam código compatível com o schema atual e a chave necessária ao rollback. Voltar diretamente ao binário anterior requer primeiro restaurar plaintext por downgrade, conforme o runbook. O intermediário compatível permite retorno técnico mantendo schema e dados atuais.

Os nomes canônicos `markina-gallery-<serviço>-1` foram atribuídos aos containers finais. O arquivo Nginx original foi restaurado e seus aliases apontam aos serviços finais. O checkout `/opt/markina-gallery` conserva sua revisão anterior; a procedência do runtime é o conjunto imutável de imagens, a comparação da fonte e o manifesto do release. Uma futura recriação precisa entregar a chave pelo loader; o Compose anterior isoladamente carece dessa configuração.

## Ocorrências e limites

O worker de prévias anterior exigiu SIGINT após comprovar zero jobs pendentes/em processamento. O operador aguarda ociosidade e usa esse sinal para o serviço. Seu contexto staging original foi preservado.

WhatsApp retornou `connecting` no runtime novo e na imagem anterior. A retomada da instância existente recuperou `open`; a atualização pelo serviço da aplicação confirmou `ready`. A primeira chamada PUT foi recusada; o código oficial instalado na versão 2.3.7 define POST, usado na retomada bem-sucedida. Os serviços Evolution API/DB/Redis existentes foram preservados. A validação consultou estado/identidade das integrações; cobrança e entrega de mensagem reais não integraram o ensaio.

Recibos protegidos em `/var/lib/markina-gallery/deploy-state/saas-preflight-20261116-24f2fba2/` incluem `production-deployment-verification.json`, `production-continuity-result.json`, `production-integration-proof.json`, `production-facial-index-proof.json`, `production-source-integrity.json`, `post-deploy-backup-receipt.json` e `production-rollout-state.json`. Operadores executados foram conservados no mesmo diretório. Os recibos não contêm chaves, credenciais ou dados de clientes.

## Configuração posterior

Drive/Workspace, backup recorrente global, recuperação por tenant, arquivo de fotos, créditos/preços e retenção seguem no [checklist pós-deploy](post-deploy-configuration-checklist.md). O cadastro público continua dependente de promoção implementada do gate local e das provas pré-tenants. A abertura de outras contas segue posterior às configurações e ensaios deliberadamente adiados.
