## Why

As telas atuais permitem validar integrações pontuais, mas ainda não oferecem uma visão clara e contínua do que o fotógrafo e a cliente conseguem fazer. São necessárias superfícies visuais mais completas para acelerar a validação manual e tornar relatos de bugs e necessidades de produto objetivos.

## What Changes

- Criar um painel visual de validação para o fotógrafo, com atalhos para operação, estado de importações, galerias recentes e orientações de teste baseadas em dados autorizados do backend.
- Evoluir a biblioteca e a galeria da cliente para uma experiência de validação mais visual, com grade de fotos, indicadores explícitos de seleção, favoritos, comentários, prazo, mensagens e histórico.
- Incluir estados de carregamento, vazio, erro e sucesso consistentes, além de identificadores visuais de versão/ambiente para facilitar o relato de problemas nesta conversa.
- Manter toda informação, permissão e ação relevante orientada pelo backend; não introduzir dados simulados, acesso público ao acervo ou armazenamento interno de chamados.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: ampliar as telas administrativas para validação visual e operação rápida orientada pelo backend.
- `client-access/derived-galleries`: ampliar biblioteca e galeria derivada da cliente para validação visual das interações privadas.

## Impact

- Frontend Next.js nas rotas administrativas, biblioteca e galeria privada; estilos e componentes reutilizáveis.
- APIs existentes poderão receber campos de resumo ou estado quando indispensáveis para uma interface backend-driven.
- Testes de frontend/backend e documentação de homologação serão atualizados; não há integração externa, pagamento, biometria ou mudança de infraestrutura neste escopo.
