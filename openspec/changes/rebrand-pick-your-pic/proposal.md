## Why

O proprietário definiu o novo nome do produto como Pick-your-Pic e forneceu referência visual da logotipo. A identidade antiga ainda aparece na interface, no aplicativo e em mensagens padrão, tornando necessária uma mudança consistente de marca.

## What Changes

- Substituir a marca exibida Markina Gallery e suas variantes visuais por `Pick-your-Pic`, incluindo entrada, navegação admin/cliente, metadata, aplicativo instalado, offline, nomes de exportação e mensagens padrão de autenticação/e-mail/WhatsApp.
- Preservar a arte oficial configurada por upload, a tipografia incorporada à logotipo e a paleta preto/amarelo, com cinza e bege de apoio. A prancha enviada é referência, não um arquivo de ícone para substituir automaticamente os uploads.
- Centralizar o nome do produto por camada para evitar novas divergências; atualizar testes, documentação vigente e contexto de execução.
- Atualizar defaults de marca-d'água para novos dados sem sobrescrever preferências personalizadas, históricos, mensagens enviadas ou reprocessar fotografias existentes.
- Preservar identificadores técnicos `markina-gallery`, cookies, caminhos, filas, containers, volumes, nomes internos de componentes, repositório, domínio e links existentes. Rebranding do produto não renomeia infraestrutura ou apaga trilha histórica.

## Capabilities

### New Capabilities

- `product-branding`: identidade Pick-your-Pic consistente em superfícies e comunicações do produto com continuidade técnica.

### Modified Capabilities

Nenhuma regra consolidada de autenticação, venda ou autorização é alterada; textos de marca passam a seguir a nova capacidade.

## Impact

Frontend, metadata/manifesto, backend de comunicações e defaults, testes e documentação ativa. Sem dependências externas, redesenho de imagens, troca de domínio, migration destrutiva ou publicação remota durante o planejamento.

Sequência: concluir `dark-mode-and-landscape-covers`, depois aplicar esta change sem misturar tarefas parciais. A base de UI/PWA do PR #82 já foi mergeada e seu deploy continua pendente de confirmação operacional; autorização de rebrand não libera aquele gate. Usar o mesmo nome novo nos dois temas sem alterar as escolhas visuais aprovadas.
