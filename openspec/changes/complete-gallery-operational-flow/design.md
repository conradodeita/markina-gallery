## Context

O editor atual preserva o contexto de uma galeria-mãe e já exige a hierarquia galeria-mãe → pasta → foto. Contudo, a etapa Imagens ainda não entrega revisão visual suficiente, a escolha de capa não é persistida e o resumo não reúne responsáveis e estado operacional para o fotógrafo. Consulte `proposal.md` para a motivação e as delta specs para o comportamento observável.

## Goals / Non-Goals

**Goals:**

- Completar a experiência administrativa que antecede vendas: criação, pastas, upload, revisão de prévias, capa, clientes e resumo.
- Manter toda mutação no backend, usando identificadores contextuais e respostas que permitam à interface exibir permissões e bloqueios.
- Preservar pedido, item vendido, seleção e auditoria ao impedir exclusão de fotos com compra confirmada.
- Entregar a mesma versão funcional em DEV e homologação após a suíte verde.

**Non-Goals:**

- Não implementar WhatsApp, reconhecimento facial, catálogo público, pagamentos, carrinho, PIX ou confirmação de venda.
- Não desfazer liberação de pasta nem permitir apagar foto com compra confirmada.
- Não expor original, chave de armazenamento ou URL de origem em nenhum estado visual.

## Decisions

### Exclusão condicionada ao histórico comercial

O backend será a autoridade da exclusão: ele buscará a foto no contexto da pasta e rejeitará quando existir item de pedido com pagamento confirmado. Fotos sem compra poderão ter suas referências derivadas elegíveis e seus arquivos de mídia removidos de forma atômica do ponto de vista de banco; a remoção física será registrada e tolerará reexecução. A interface nunca decide o bloqueio apenas por estado local.

Alternativa considerada: bloquear qualquer foto já liberada a uma galeria privada. Ela reduziria acidentes, mas impediria a correção normal de uma seleção antes da compra e não corresponde ao fluxo solicitado.

### Prévia administrativa única e ampliável

A grade e o modal de ampliação consumirão a mesma rota autenticada de derivado protegido com marca d’água. A imagem será ampliada por modal responsivo, sem fornecer download nem substituir a rota por uma origem de maior privilégio.

Alternativa considerada: servir uma miniatura para a grade e outra imagem não marcada para ampliação. Ela eleva o risco de exposição e não é necessária para a validação atual.

### Capa referencial e fallback determinístico

A galeria-mãe armazenará somente a referência de uma foto própria como capa. Se ela estiver ausente, o resumo buscará a primeira foto processada por ordem de pasta e foto, sem gravar essa escolha implícita. A exclusão da capa limpa a referência no mesmo fluxo.

Alternativa considerada: copiar a imagem de capa para outro armazenamento. Ela duplicaria mídia e violaria a propriedade centralizada da foto.

### Resumo orientado por contrato único

O backend fornecerá um resumo autenticado da galeria-mãe contendo metadados, capa protegida, contagens de pasta/foto, link não listado e responsáveis. A busca de clientes permanecerá paginada e ordenada no backend por nome normalizado, com filtro por nome ou WhatsApp.

Alternativa considerada: montar o resumo por diversas chamadas no navegador. Ela aumenta estados inconsistentes e contraria a diretriz backend-driven.

### Navegação sem efeitos colaterais

Avançar e voltar no editor trocará apenas a rota da etapa; persistência ocorrerá somente em ações explícitas de salvar, criar, enviar, vincular, escolher capa ou excluir. Os testes devem confirmar que recarregar ou navegar não duplica dados.

## Risks / Trade-offs

- [Exclusão física falhar após a transação] → registrar trabalho de limpeza idempotente e nunca apagar registro com compra confirmada.
- [Foto ainda sendo processada escolhida como capa] → aceitar somente derivado concluído e informar estado pendente.
- [Vínculo duplicado de cliente] → reutilizar a galeria derivada existente da mesma cliente e origem, com restrição e teste de idempotência.
- [Prévia ampliada em tela pequena] → modal com foco gerenciado, fechamento por teclado e imagem limitada ao viewport.
- [Divergência DEV/homologação] → exigir testes, build e deploy automático restrito ao projeto Markina após cada conjunto verde.

## Migration Plan

1. Adicionar metadado opcional de capa referenciando foto da mesma galeria-mãe, com constraint e migration reversível.
2. Implementar contratos e testes de exclusão, capa, resumo e busca contextual antes do frontend.
3. Implementar interface administrativa e testes de componente/fluxo sintético.
4. Executar suíte local, build e revisão visual com dados sintéticos.
5. Criar backup exclusivo do Markina, aplicar somente o Compose `markina-gallery` em homologação e verificar saúde, migration e fluxo de teste.

Rollback: reverter o código e, se necessário, a migration de metadado de capa; não restaurar backup para corrigir erro de interface. Caso a migration ou a integridade falhe, interromper o deploy antes de iniciar API/worker e preservar o backup exclusivo.

## Open Questions

Nenhuma. A reversão desta mudança significa somente navegação entre etapas e exclusão de foto sem compra; ela não inclui desfazer liberação de pasta.
