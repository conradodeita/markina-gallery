# Proposal

## Why

O proprietário solicitou impedir o salvamento de uma galeria sem capa e delegou a escolha da etapa para preservar o cadastro inicial. A etapa 3, Detalhes, já oferece upload e personalização da capa, mas atualmente permite salvar e avançar sem imagem e o fluxo termina por simples navegação.

## What Changes

- Exigir capa explicitamente configurada, pertencente à galeria/conta e com prévia pronta para salvar Detalhes e concluir o fluxo guiado.
- Manter Criar e continuar, Ajustes e Vendas disponíveis sem capa, permitindo gerar o contexto necessário ao upload; esses passos não significam conclusão da galeria.
- Mostrar orientação acionável na etapa Detalhes para capa ausente, preparando ou com falha; estado concluído somente após prontidão confirmada pelo backend.
- Conforme revisão do proprietário em 08/10/2026, retirar o parágrafo explicativo sobre JPEG horizontal, marca-d’água, grade e carregamento das pastas; preservar a orientação de obrigatoriedade e prontidão da capa.
- Revalidar no backend ao salvar configurações visuais e consultar a prontidão atual antes de Concluir; não confiar em identificador/estado informado pelo browser.
- Aplicar a exigência também ao editar/concluir galerias existentes sem capa, sem preencher automaticamente nem revogar acesso já autorizado de clientes.

## Capabilities

### New Capabilities

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: adicionar obrigatoriedade de capa na etapa Detalhes e na conclusão guiada, conservando criação/preparação e autorização existentes.

## Impact

Editor administrativo, contrato de estado/prontidão da galeria e salvamento de configurações visuais; testes backend/frontend e documentação operacional. Sem migration destrutiva, novos canais, alteração de segredos ou bloqueio automático das galerias publicadas.

O botão Concluir hoje apenas abre o resumo; a proposta acrescenta verificação atual da prontidão sem inventar estado persistente de publicação/conclusão. A validação refere-se à conclusão guiada, sem tornar a capa uma autorização de mídia nem impedir leitura/manutenção dos acervos existentes.

A falha de miniaturas em Compras é tratada em `fix-finalized-selection-purchase-previews`. A orientação neutra aprovada para OTP também é independente. Publicação de qualquer correção depende de CI e inventário/autorização específicos; o piloto A+B e a limpeza final permanecem pendentes.
