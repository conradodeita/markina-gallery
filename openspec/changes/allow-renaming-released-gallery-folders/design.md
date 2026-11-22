# Design

## Context

Veja `proposal.md` e as delta specs. O editor já usa `PATCH /admin/photo-folders/{folder_id}` e preserva autorização por tenant, bloqueio da galeria e auditoria; o endpoint e a UI rejeitam pastas liberadas. Pastas restritas do `Acervo da cliente` são registros `PhotoFolder` da Galeria pública com audiência `selected`, e a seção própria não oferece renomeação. A tela legada de Galeria privada também administra pastas exclusivas existentes, mas não apresenta essa ação.

## Goals / Non-Goals

**Goals:**

- Reutilizar a rota de renomeação e sua auditoria existente para pastas comuns e restritas.
- Disponibilizar a mesma ação nos dois contextos administrativos em que o fotógrafo vê as pastas.
- Disponibilizar a ação na tela já existente de uma Galeria privada legada, limitada a renomear pastas existentes.
- Tratar o nome como metadado; preservar status, atribuições, fotos e dados comerciais.

**Non-Goals:**

- Alterar público, liberar/desliberar pastas, renomear arquivos, mover fotos ou reescrever snapshots financeiros.
- Reabrir criação ou ampliar operações das galerias privadas derivadas legadas; somente a renomeação de pastas já listadas pela tela existente entra no escopo.
- Alterar migrations ou publicar em homologação/produção.

## Decisions

1. **Manter uma única rota autenticada.** A rota continua resolvendo `PhotoFolder` no tenant da sessão e chamando `require_parent_gallery_mutable` ou `require_derived_gallery_mutable`. Remove-se somente a recusa baseada em `status == released`; pastas de galerias indisponíveis e IDs de outro tenant continuam recusados. A lógica comum cobre as pastas restritas (`audience_scope=selected`) sem endpoint paralelo.
2. **Normalizar o nome na fronteira da API.** Remover espaços externos e validar novamente limites de 1 a 200 caracteres; espaços internos são preservados. Nome vazio após normalização retorna erro de validação sem gravar.
3. **Reutilizar as interfaces existentes.** No editor de Imagens, mostrar `Renomear` para pastas comuns e restritas em qualquer estado permitido. No `Acervo da cliente`, adicionar a ação junto às operações da pasta. Na tela legada de Galeria privada, adicionar a ação nas pastas exclusivas já listadas. Sucesso atualiza ou recarrega a lista e mostra confirmação; erro mantém a lista e informa o problema.
4. **Não invalidar histórico.** Persistir apenas `PhotoFolder.name` e manter `photo_folder.renamed`. Eventos e snapshots de créditos/pedidos não são reescritos; a próxima leitura autorizada usa o novo nome.

## Risks / Trade-offs

- [Clientes podem ver nomes diferentes em telas já abertas] → as consultas seguintes retornam o nome atual; o sistema não tenta atualizar sessões já renderizadas em outros dispositivos.
- [O fotógrafo pode editar enquanto um worker prepara prévias] → a operação não altera identificadores ou arquivos e permanece protegida pelos guards da galeria; upload e processamento continuam vinculados ao UUID da pasta.

## Migration Plan

Nenhuma migration. Atualizar API e os três pontos da interface; rollback de código restaura a restrição anterior a renomeações liberadas sem alterar nomes já persistidos.
