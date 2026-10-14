## Context

Veja `proposal.md` — Why. O modelo atual já obriga `PhotoFolder` a possuir `parent_gallery_id`, mas `PhotoAsset.folder_id` permanece opcional e uma rota administrativa legada registra fotos diretamente na galeria-mãe. A interface `/admin/operations` reúne criação de cliente, acervo, pasta, upload e galeria derivada numa página operacional; embora use rotas contextualizadas no backend, sua organização visual faz essas entidades parecerem independentes.

A mudança atravessa modelo, migration, contratos FastAPI e navegação Next.js. Deve preservar fotos e históricos existentes, manter o frontend backend-driven e não assumir que as capacidades futuras de venda, mensageria ou reconhecimento facial já existem.

## Goals / Non-Goals

**Goals:**

- Fazer da galeria-mãe o contexto persistente de toda criação e edição administrativa.
- Impedir no banco e na API a criação de pasta sem galeria e de foto sem pasta coerente.
- Migrar dados legados sem mudar identificadores, visibilidade autorizada ou histórico comercial.
- Reproduzir a lógica de navegação das referências em cinco etapas, usando a identidade visual própria da Markina Gallery.
- Manter galerias privadas como recortes autorizados do acervo, sem duplicar mídia.

**Non-Goals:**

- Copiar cores, tipografia, componentes ou marca do produto usado como referência.
- Implementar cálculo comercial definitivo, PIX, cartão, mensagens reais, reconhecimento facial ou entrega de originais.
- Transformar a galeria-mãe em catálogo público pesquisável.
- Reformular nesta mudança as regras individuais de múltiplos responsáveis já planejadas em `evolve-shared-derived-gallery-access`.
- Implantar em homologação ou produção durante a fase de planejamento.

## Decisions

### Galeria-mãe como agregado administrativo

As rotas visuais de criação e edição manterão um `parent_gallery_id` após a primeira gravação. O editor será composto pelas etapas `ajustes`, `vendas`, `detalhes`, `imagens` e `clientes`; cada etapa obterá do backend um contrato específico com dados persistidos, permissões e disponibilidade de ações. Avançar não criará cópias da galeria.

A criação inicial persistirá o identificador antes de abrir as etapas dependentes. A página global de operações deixará de oferecer criação de pasta e upload; poderá redirecionar para a lista de galerias ou, quando receber um identificador válido, para a etapa correspondente do editor.

Alternativa descartada: manter todos os formulários numa única página com seletores de acervo. Embora funcional, ela continua permitindo perda de contexto e não traduz a sequência de negócio validada.

### Cinco etapas com contratos backend-driven

- **Ajustes:** identidade da galeria, prazo e recursos atualmente suportados.
- **Vendas:** configurações comerciais realmente disponíveis. Campos ainda não implementados serão apresentados como indisponíveis, sem estado falso no navegador.
- **Detalhes:** capa e personalização visual suportada pelo backend.
- **Imagens:** pastas da galeria, ordem, estado, contagem, upload, prévias e liberação.
- **Clientes:** link não listado, tipo de acesso, cadastros e galerias privadas derivadas/vínculos autorizados.

Um endpoint de resumo do editor poderá informar conclusão, pendências e ações permitidas por etapa. Contratos de mutação permanecerão menores e separados, evitando um payload monolítico que sobrescreva dados de outra etapa.

Alternativa descartada: armazenar no browser um rascunho completo e enviá-lo somente ao final. Isso conflita com a diretriz backend-driven, dificulta retomada e aumenta o risco de registros duplicados.

### Integridade composta entre pasta e foto

`PhotoFolder.parent_gallery_id` permanecerá obrigatório. `PhotoAsset.folder_id` será saneado e depois alterado para obrigatório. A API de upload receberá somente a pasta e derivará dela a galeria-mãe; o cliente da API não escolherá os dois vínculos independentemente.

Como `PhotoAsset.parent_gallery_id` é usado amplamente para consultas e autorização, ele será preservado nesta etapa. Para impedir divergência também no banco, a migration adicionará uma chave candidata composta em pasta `(id, parent_gallery_id)` e uma chave estrangeira composta em foto `(folder_id, parent_gallery_id)`. A aplicação continuará validando o contexto para produzir erros compreensíveis antes da restrição do banco.

Alternativa descartada: remover imediatamente `PhotoAsset.parent_gallery_id`. Isso ampliaria desnecessariamente a migration e reescreveria consultas de autorização, sem benefício observável para esta mudança.

### Compatibilidade de fotos legadas

Antes de definir `folder_id` como não nulo, a migration agrupará as fotos sem pasta por galeria-mãe. Para cada grupo, criará uma pasta de compatibilidade com identificador determinístico derivado do identificador da galeria, nome administrativo reconhecível e estado `released`, preservando a visibilidade que as fotos legadas já possuíam quando referenciadas por uma galeria privada. A posição será calculada após as pastas existentes.

A execução verificará previamente fotos órfãs de galeria-mãe e interromperá sem descarte caso encontre inconsistência. Identificador, armazenamento, derivados, referências privadas, seleções, pedidos e compras das fotos não serão recriados. A chave determinística e a consulta por vínculo tornam o saneamento idempotente.

O downgrade removerá a obrigatoriedade e as restrições novas, mas não desassociará automaticamente fotos da pasta de compatibilidade: isso preserva dados e permite que a versão anterior continue operando. Uma reversão destrutiva da organização exigiria procedimento separado e não faz parte do rollback normal.

Alternativa descartada: excluir fotos sem pasta ou criar uma pasta por foto. A primeira viola preservação de dados; a segunda degrada a experiência e a ordem do acervo.

### Descontinuação explícita do cadastro direto

O fluxo de interface e os testes deixarão de usar o cadastro direto por galeria. Durante a transição, a rota legada responderá `410 Gone` com mensagem estável indicando que uma pasta em preparação é obrigatória; ela não criará dados. Upload, processamento e liberação passarão exclusivamente pelos contratos da pasta.

Alternativa descartada: manter a rota ativa e apenas escondê-la no frontend. Clientes antigos ou chamadas manuais continuariam produzindo fotos sem pasta e violariam a regra central.

### Galerias derivadas referenciam, não possuem, a pasta

A pasta e os arquivos permanecerão no agregado da galeria-mãe. A liberação associará referências das fotos às galerias privadas elegíveis da mesma origem. A visualização da cliente poderá agrupar essas referências pela pasta, mas não transferirá sua propriedade nem criará clone físico. Seleções, favoritos, comentários e pedidos continuarão associados ao responsável e à galeria privada conforme os contratos próprios.

Alternativa descartada: clonar pasta e arquivos por cliente. Isso multiplicaria armazenamento, permitiria divergência editorial e dificultaria reconhecer que a mesma foto foi comprada por pessoas diferentes.

### Remediação da revisão visual em homologação

A navegação administrativa removerá a entrada **Operação**, pois a rota já é somente compatibilidade e redireciona para Galerias. O redirecionamento será preservado para favoritos antigos, mas não será apresentado como área ativa.

A etapa **Detalhes** deixará de exibir indisponibilidade genérica e receberá os controles persistidos de capa, título e organização hoje misturados em Imagens. A etapa Imagens voltará a concentrar pastas, upload, processamento e liberação. Vendas continuará orientada pela capacidade real do backend e não ganhará campos simulados.

O shell administrativo usará uma gramática visual neutra, com canvas cinza claro, superfícies brancas, ações primárias pretas, bordas cinzas e espaçamento derivado dos tokens existentes. Cada assunto formará um card ou bloco com cabeçalho, explicação, controles e feedback próprios. Botões SHALL manter texto visível e contraste em estado normal, hover, foco e desabilitado.

Clientes será dividido em três superfícies: responsáveis vinculados, busca/vínculo de cadastro existente e cadastro de nova responsável. Resultados de busca usarão linhas ou cards com nome, telefone e ação textual inequívoca, empilhados no smartphone.

Alternativa descartada: manter Detalhes como placeholder e apenas melhorar seu texto. A revisão humana confirmou que uma etapa numerada sem configuração real comunica fluxo incompleto e impede operar a apresentação pela homologação.

## Risks / Trade-offs

- [Fotos legadas possuem vínculos inesperados] → executar inventário e testes de preservação antes da restrição; interromper a migration diante de órfãos.
- [Chave estrangeira composta varia entre PostgreSQL e SQLite de testes] → validar upgrade e downgrade nos dois comportamentos suportados, usando operação em lote quando necessária.
- [Etapas Vendas e Detalhes sugerirem recursos inexistentes] → renderizar somente capacidades retornadas pelo backend e estados explícitos de indisponibilidade.
- [Mudança de navegação quebrar favoritos administrativos antigos] → manter redirecionamentos contextuais para o novo editor durante a transição.
- [Conflito com mudanças ativas de acesso compartilhado] → limitar esta mudança à propriedade de mídia e consumir os contratos de vínculo vigentes, sem reimplementar titularidade.
- [Migração longa em acervo grande] → inventariar contagens e estimar duração antes de homologação; executar somente no projeto Markina com backup e plano de rollback próprios.
- [Reorganização visual esconder ações existentes] → preservar contratos e nomes de ação, testar texto/contraste e cobrir desktop e smartphone antes de nova aprovação humana.

## Migration Plan

1. Criar testes de inventário com fotos em pasta, sem pasta, referenciadas, selecionadas e compradas.
2. Adicionar contratos do editor e adaptar a interface para criar novos uploads somente dentro de pasta, mantendo temporariamente leitura dos registros existentes.
3. Publicar a migration que valida galerias-mãe, cria pastas de compatibilidade determinísticas, associa fotos legadas e adiciona as restrições de nulidade e coerência composta.
4. Desativar o contrato legado com resposta `410 Gone` e confirmar que nenhum fluxo interno ainda o utiliza.
5. Executar lint, testes backend/frontend, build e teste funcional completo das cinco etapas com dados sintéticos.
6. Antes da homologação, apresentar inventário do host compartilhado, backup exclusivo do Markina, comandos com projeto Compose explícito e plano de impacto zero para aprovação.
7. Em falha de aplicação, reverter a imagem do Markina e executar downgrade não destrutivo da migration; nunca tocar recursos Docker do ClearBudget.
