# Design

## Context

Veja `proposal.md` — Why. A etapa 04 obtém as pastas públicas por um contrato que exclui `PhotoFolder.derived_gallery_id`; galerias privadas e seus membros são apresentados hoje na etapa Clientes. As pastas privadas têm proprietário `DerivedGallery.client_id` e podem ter membros adicionais autorizados.

## Goals / Non-Goals

**Goals:**

- Obter resumo de galerias privadas, clientes autorizados e pastas no escopo da galeria-fonte atual.
- Exibir o resumo privado separado das pastas e controles de upload públicos.
- Preservar o backend como fonte de nomes, propriedade e vínculos.

**Non-Goals:**

- Permitir upload privado ou alterar o destino de upload na etapa 04.
- Alterar permissões, vínculos, associação de pastas ou processamento/notificações.
- Expor prévias, URLs de arquivos ou dados privados em endpoints acessíveis a clientes.

## Decisions

### Contrato administrativo somente de leitura

O contrato `GET /admin/parent-galleries/{id}/private-folders` retorna apenas ID/nome da galeria privada, cliente principal, membros ativos e pastas privadas com nome, estado e contagem. A consulta exige administrador, resolve o tenant da sessão, verifica a propriedade da origem e filtra galerias, clientes, membros, pastas e fotos pelo tenant e pelo `parent_gallery_id` da origem solicitada. IDs de outro tenant respondem como não encontrados. A lista pública permanece independente, pois misturar os contratos confundiria propriedade e permissões.

Alternativa descartada: buscar todas as galerias privadas e filtrar no navegador. Isso ampliaria dados administrativos enviados ao cliente e dependeria do frontend para isolar a galeria atual.

### Seção privada independente na etapa 04

Renderizar as galerias privadas em um bloco separado após a lista pública, com o nome da cliente principal em evidência, membros ativos associados e nomes/estados das pastas. A seção será informativa; controles de upload público continuam presos às pastas públicas. A navegação/gestão de uploads privados permanece no detalhe da galeria privada.

Alternativa descartada: inserir pastas privadas na mesma grade ou no mesmo seletor de upload público. Isso poderia direcionar fotos ao lote/escopo errado e reforçar a confusão atual.

### Compartilhamento

Exibir a cliente principal definida pela galeria e todos os membros ativos, distinguindo o rótulo “Responsável principal” de “Acesso compartilhado”. Não inferir propriedade com base em telefone, sessão local ou nome da pasta.

Alternativa descartada: mostrar apenas o primeiro membro ativo, que poderia ocultar outras pessoas autorizadas numa galeria compartilhada.

## Risks / Trade-offs

- [Resumo administrativo inclui dados pessoais] → exigir sessão administrativa, limitar a consulta à origem requisitada e retornar somente nomes e metadados operacionais necessários.
- [Consultas adicionais aumentam o carregamento da etapa] → usar uma consulta agregada ou poucas consultas em lote, sem carregar prévias nem dados foto a foto.
- [Uma pasta privada pode não ter membros ativos] → ainda mostrar a responsável principal e um estado de acesso sem membros ativos, sem inventar autorização.

## Migration Plan

Não há mudança de banco nem migração de dados. A API e a interface podem ser publicadas juntas. Rollback consiste em remover a seção e o contrato de leitura; uploads, pastas, vínculos e notificações existentes não são alterados.
