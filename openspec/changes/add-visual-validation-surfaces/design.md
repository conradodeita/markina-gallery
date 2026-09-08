## Context

As rotas administrativas e de cliente já consultam o backend, mas ainda são telas operacionais compactas. Esta mudança torna os fluxos mais observáveis durante a validação manual, preservando as regras de autorização das especificações existentes.

## Goals / Non-Goals

**Goals:**

- Reorganizar as telas em superfícies visuais de validação para fotógrafo e cliente.
- Reutilizar respostas autenticadas do backend e adicionar somente resumos mínimos quando a interface não puder ser composta com os contratos existentes.
- Exibir ambiente e versão sem segredos para tornar relatos reproduzíveis.

**Non-Goals:**

- Criar sistema de tickets, suporte, chat, notificações ou dados simulados.
- Implementar checkout, pagamentos, entrega, busca facial, branding ou novas permissões.
- Expor originais, acervo-mãe ou qualquer foto fora de uma galeria derivada autorizada.

## Decisions

### Superfícies por papel com rotas existentes

O painel administrativo continuará em `/admin` e a experiência da cliente em `/library` e `/gallery/[galleryId]`, evitando um ambiente paralelo de demonstração. Isso mantém a validação fiel ao produto e ao controle de sessão. Uma rota separada de demo foi descartada porque duplicaria comportamento e tenderia a usar mocks.

### Composição backend-driven

As contagens, listas e estados virão de endpoints autenticados. Quando faltar um resumo para o painel, será criado um contrato pequeno e específico, sem retornar telefone, original ou dados de outras clientes. Agregação no frontend a partir de dados sensíveis foi descartada para não ampliar exposição.

### Componentes visuais reutilizáveis

Serão extraídos componentes de cartão de estado, cabeçalho de ambiente, lista/grade de validação e estado vazio/erro. Isso reduz páginas monolíticas e permite que um relato de bug cite título e estado da tela. Não será introduzida biblioteca visual externa nesta etapa.

## Risks / Trade-offs

- [Dados ainda incompletos no backend] → mostrar orientação de próximo passo e não preencher lacunas com mocks.
- [Tela mais visual aumentar carregamento] → manter prévias protegidas existentes e usar carregamento progressivo.
- [Confusão entre homologação e produção] → identificador de ambiente discreto, sem alterar autenticação ou domínio.

## Migration Plan

1. Implementar e testar os resumos e componentes no ambiente local.
2. Validar os dois papéis com dados sintéticos em homologação.
3. Publicar somente após lint, build e validação OpenSpec; rollback consiste em restaurar a imagem web anterior do projeto `markina-gallery`.
