# Proposal

## Why

O aceite da fundação de propriedade em homologação revelou dois defeitos na jornada existente: o painel entrega um convite `http://` com capacidade de acesso apesar da origem pública HTTPS, e o carrinho mostra “Prévia indisponível” para uma foto cuja prévia protegida abre na galeria. O primeiro pode expor o token na primeira requisição; o segundo impede a conferência visual antes do PIX.

## What Changes

- Gerar links de capacidade da galeria pela origem pública confiável já configurada no servidor, com HTTPS obrigatório fora de desenvolvimento/teste; recusar origem ausente ou insegura antes de devolver um link sensível. Preservar a entrada local HTTP apenas nos ambientes de teste/desenvolvimento.
- Fazer a prévia de compra reconhecer a rota protegida de foto da galeria canônica no carrinho e em superfícies que reutilizam o componente, sem aceitar URLs externas, originais ou rotas administrativas.
- Cobrir as respostas de convite e o carregamento/negação da prévia com testes focados. Revalidar em homologação somente após revisão, CI e autorização operacional específica; o ensaio não exige pagamento real.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `client-access/cloned-private-galleries`: o link não listado entregue ao fotógrafo SHALL usar a origem pública segura configurada, sem confiar no esquema/host de cabeçalhos da requisição para compor a capacidade.
- `media-storage/protected-previews`: o carrinho SHALL mostrar a prévia protegida já autorizada de uma foto selecionada na galeria canônica e continuar negando mídia de outra cliente ou pasta.

## Impact

Backend: composição dos links de galeria/convite e validação da origem pública existente (`PUBLIC_APP_ORIGIN`); frontend: lista estrita de rotas aceitas pelo componente compartilhado de prévias de compras; testes de API, frontend e configuração. Não há migration, nova variável de ambiente, edição de `.env`, alteração do Proxy Manager ou do nginx compartilhado, mudança de PIX/OTP, envio de mensagem nem acesso público anônimo às imagens. A change `fix-purchase-previews-payment-shortcuts-and-expiry` cobre imagens históricas/operacionais antigas; este ajuste acrescenta o caminho de galeria canônica sem substituir suas regras. O relatório da fundação permanece no PR #118 até revisão humana.
