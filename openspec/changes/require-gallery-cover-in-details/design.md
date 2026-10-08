# Design

## Context

Ver `proposal.md`. A criação em `new/page.tsx` envia apenas os dados iniciais, persiste uma galeria e abre Ajustes. O registro/upload de capa exige esse UUID. Detalhes já contém upload, estados de processamento e personalização visual. Seu formulário usa PATCH de settings com os campos de título da capa e avança incondicionalmente após sucesso. O editor considera Detalhes completo apenas pela existência de cover_photo_id, mesmo que ainda não haja derivado. Concluir é um link ao resumo, sem estado persistente de conclusão.

## Goals / Non-Goals

**Goals:** cobrar a capa no ponto em que o fotógrafo consegue defini-la, com regra verificável na API e feedback claro para processamento/falha; evitar falso estado concluído.

**Non-Goals:** exigir upload antes de criar a galeria, selecionar foto automaticamente, criar novo estado persistente de publicação, revogar clientes, impedir navegação/leitura/manutenção das galerias existentes ou converter a capa em requisito de autorização de mídia.

## Decisions

1. Exigência na etapa 3 — Detalhes. Foi delegada pelo proprietário para evitar travar o cadastro. Exigir no cadastro inicial precisaria antecipar o upload ou introduzir staging, e exigir em Ajustes antecederia a configuração atual da capa. Detalhes resolve a sequência no fluxo existente.
2. Derivar prontidão no servidor a partir da capa efetivamente configurada, ownership, galeria, asset e derivado pronto utilizados pelas rotas existentes de capa. Expor estados ausente/preparando/falha/pronta; identificador isolado e fallback automático de outra foto não satisfazem a obrigação. Usar a mesma decisão em Detalhes, editor e salvamento visual para evitar divergências.
3. Manter o PATCH de settings e exigir prontidão quando qualquer campo de título/capa salvo pelo formulário Detalhes estiver presente. Validar antes de alterar campos, auditar ou commitar. Patches de nome, descrição, organização e regras anteriores não devem exigir capa. Upload e sua associação continuam disponíveis justamente para sanar a pendência.
4. Substituir a ação Concluir por uma ação que consulta o editor autenticado atual e verifica a prontidão devolvida antes de navegar ao resumo. Falha de consulta ou estado não pronto mantém o fluxo aberto e orienta Detalhes. A regra é de conclusão guiada: abrir diretamente o resumo continua sendo leitura, não persistência de uma conclusão inexistente.
5. Galerias existentes sem capa permanecem acessíveis conforme suas permissões atuais, mas não podem salvar Detalhes nem concluir novamente o fluxo até configurar capa pronta. Remover ou substituir uma capa pode devolver a etapa ao estado pendente; não revogar vínculos nem escolher outra foto implicitamente.
6. Regressões de criação permitida, salvamento rejeitado/atômico, processamento/falha, capa de outra conta/galeria, estado completo apenas quando pronto, retomada de legadas e Concluir após atualização concorrente. Mockar somente fronteiras externas; a decisão de prontidão e os efeitos de persistência não devem ser ocultados pelos testes.

## Risks / Trade-offs

- Processamento assíncrono deixa o fotógrafo temporariamente sem avanço → mostrar preparar/falha e atualização real, mantendo upload e retomada disponíveis.
- Exigência indiscriminada no PATCH bloquearia até a correção do cadastro → aplicar somente aos campos visuais da etapa Detalhes e preservar as etapas anteriores.
- Concluir com estado antigo de browser → consultar o backend imediatamente antes da navegação; recusar avanço em falha de consulta.
- A capa ser interpretada como gate de publicação ou acesso → documentar que esta change não cria novo estado de publicação nem revoga acesso legado; a autorização das fotos permanece independente.

## Migration Plan

Sem migration. Implementar/testar localmente, revisar a compatibilidade das fixtures atuais e preparar PR focado. Homologação/deploy exigem inventário e autorização próprios. Aceite visual após publicação: cadastro inicial sem capa funciona, Detalhes não avança sem capa e passa após processamento, Concluir identifica capa pendente. Nenhum dado real será preenchido/excluído automaticamente.
