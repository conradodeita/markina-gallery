## Why

O cadastro de clientes hoje só possui interface dentro da etapa 05 de uma Galeria pública, o que impede administrar contatos quando não há galerias e bloqueia a exclusão até de cadastros sintéticos que possuem apenas vínculos operacionais descartáveis. A configuração PIX também é repetida por galeria, embora pertença ao fotógrafo e deva ser administrada uma única vez com segurança.

## What Changes

- Criar um diretório administrativo global de clientes, acessível pelo menu mesmo quando não existir galeria, com busca, cadastro, edição, inventário de vínculos e exclusão segura.
- Permitir excluir uma cliente sem histórico comercial mesmo quando existirem vínculos, sessões, seleções ou galerias privadas puramente operacionais; a operação removerá o grafo descartável da cliente e preservará Galerias públicas, fotos e dados de outras clientes.
- Manter a exclusão definitiva bloqueada quando houver pedido, pagamento, entrega ou outro histórico comercial que precise ser preservado; troca de telefone continuará sendo edição da mesma identidade, com verificação do novo número.
- Manter clientes já vinculadas visíveis tanto no diretório global quanto no bloco `Cadastro existente`, identificando o vínculo em vez de ocultar o cadastro.
- **BREAKING**: substituir a configuração PIX por Galeria pública por uma configuração global única do fotógrafo, administrada em `Configurações` e confirmada pelo fluxo de segurança do WhatsApp administrativo.
- Fazer a etapa 02 somente consultar e apresentar o PIX global, com atalho para configurá-lo; preço, prazo e demais regras comerciais continuam pertencendo à galeria.
- Congelar a configuração PIX efetiva no pedido no momento do checkout, para que alterações futuras não modifiquem pagamentos já iniciados nem o histórico.
- Migrar com segurança configurações legadas: promover automaticamente somente um valor único e não divergente; divergências SHALL exigir escolha explícita do fotógrafo sem selecionar dados arbitrariamente.

## Capabilities

### New Capabilities

- `client-access/admin-client-directory`: diretório global, edição e exclusão segura do cadastro e de suas dependências exclusivamente operacionais.
- `gallery-sales/global-pix-configuration`: configuração PIX única do fotógrafo, confirmação sensível, compatibilidade legada e snapshot por pedido.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: expor Clientes no menu e fazer a etapa Vendas consumir, sem editar, o PIX global.

## Impact

- Backend FastAPI/SQLAlchemy: contratos globais de clientes, inventário e operação idempotente de exclusão, configuração PIX global, confirmação administrativa, auditoria e resolução do PIX no checkout.
- Banco/Alembic: migration aditiva para a configuração PIX global e eventual operação durável de exclusão; tabelas e snapshots comerciais legados serão preservados durante a compatibilidade.
- Frontend Next.js: nova rota `/admin/clients`, item de navegação, componentes reutilizados de cadastro/edição/exclusão e painel PIX em `Configurações`; etapa 02 passa a exibir o estado global.
- Testes: autorização, concorrência, preservação de histórico, isolamento entre clientes/galerias, migração de PIX idêntico/divergente, confirmação sensível e snapshots imutáveis.
- Operação: nenhuma limpeza de dados, migration ou deploy é autorizada por esta proposta; homologação continuará usando somente dados sintéticos.
