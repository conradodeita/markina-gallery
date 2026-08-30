## Why

A área administrativa atual separa acervos, pastas, fotos e galerias em operações que não comunicam a hierarquia real do negócio e ainda preserva um contrato legado capaz de registrar fotos sem pasta. O fotógrafo precisa operar a galeria como unidade principal, seguindo o fluxo validado nas referências visuais, com garantia de que toda pasta e toda foto tenham contexto inequívoco.

## What Changes

- Reorganizar a criação e edição administrativa de uma galeria-mãe nas cinco etapas validadas pelas referências: Ajustes, Vendas, Detalhes, Imagens e Clientes.
- Tornar Galerias a entrada principal do trabalho do fotógrafo e remover da experiência a criação global ou descontextualizada de pastas.
- Exigir que toda pasta pertença a exatamente uma galeria-mãe e que toda nova foto pertença a exatamente uma pasta dessa mesma galeria.
- **BREAKING**: descontinuar o contrato administrativo que registra foto diretamente na galeria-mãe sem pasta; novos uploads serão aceitos somente por uma pasta em preparação.
- Inventariar fotos legadas sem pasta e vinculá-las, por migração auditável e reversível, a uma pasta de compatibilidade na respectiva galeria-mãe, sem apagar arquivos nem histórico.
- Manter galerias privadas derivadas como referências autorizadas às fotos da galeria-mãe, sem duplicação de arquivos e com histórico individual de seleção, compra e acesso.
- Preservar o caráter não listado da galeria-mãe: o link poderá ser compartilhado diretamente, mas não haverá catálogo público pesquisável e a visualização das fotos continuará condicionada à autenticação e às regras de liberação.
- Manter telas, disponibilidade de ações, vínculos e estados integralmente orientados pelo backend.
- Incorporar o retorno da validação humana em homologação: retirar a entrada obsoleta Operação, tornar Detalhes uma etapa configurável, corrigir a legibilidade de botões e reorganizar Clientes em blocos claros e responsivos.
- Padronizar a área administrativa em superfícies pretas, brancas e cinzas, com cards, espaçamentos, hierarquia e estados consistentes, sem alterar permissões ou inventar capacidades no navegador.

## Capabilities

### New Capabilities

- `media-storage/gallery-folder-ownership`: define propriedade obrigatória e coerente entre galeria-mãe, pasta e foto, incluindo tratamento seguro dos registros legados sem pasta.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: substitui operações administrativas desconectadas por um fluxo de galeria em cinco etapas e restringe criação de pastas e upload ao contexto da galeria selecionada.

## Impact

- Frontend Next.js da área administrativa: navegação de galerias, resumo, criação e edição guiada, componentes de etapas, fotos, pastas e clientes.
- Design system administrativo e testes de contraste, texto visível, agrupamento e responsividade dos componentes revisados.
- APIs FastAPI administrativas de galerias-mãe, pastas, fotos, vendas, aparência e vínculos de clientes.
- Modelo SQLAlchemy e migration Alembic para tornar obrigatório o vínculo de foto com pasta após o saneamento dos dados legados.
- Testes de API, migration, autorização, componentes e fluxo funcional, incluindo recusa de pasta ou foto sem galeria e preservação de históricos.
- Documentação OpenSpec e roteiro posterior de validação visual; sem ativar pagamento real, WhatsApp real, reconhecimento facial ou exposição pública do acervo.
