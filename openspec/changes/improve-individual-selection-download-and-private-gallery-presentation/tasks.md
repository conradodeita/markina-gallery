## 1. Especificação e contrato

- [x] 1.1 Atualizar os deltas de seleção, acesso privado e apresentação visual com cenários verificáveis.
- [x] 1.2 Adicionar testes backend para HTML autônomo, auditoria, ausência de arquivo persistente, herança do modo e publicação de pasta privada. Evidência: `test_derived_galleries.py` cobre `export.html`, prévia embutida, pedido confirmado, ausência de arquivo vazio e `inherited_folder_display_mode`; a cobertura existente confirma publicação privada.
- [x] 1.3 Adicionar testes frontend para o novo rótulo/ação, herança somente leitura e liberação da pasta. Evidência: `galleries.test.tsx` cobre download direto, estado sem compra, modo herdado e liberação.

## 2. Implementação

- [x] 2.1 Implementar a resposta HTML autônoma, embutindo somente prévias administrativas disponíveis e preservando autorização por seleção/cliente.
- [x] 2.2 Renomear a ação administrativa, baixar diretamente do card da cliente e remover a tela intermediária e os botões TXT/CSV desse fluxo.
- [x] 2.3 Expor e apresentar o modo de pastas herdado na galeria privada.
- [x] 2.4 Adicionar a ação administrativa de liberar pasta privada e refletir o estado após a publicação.

## 3. Validação

- [x] 3.1 Executar testes backend e frontend direcionados e corrigir falhas causadas pela alteração. Evidência: backend `3 passed, 80 deselected`; frontend `12 passed`.
- [x] 3.2 Executar lint/typecheck aplicáveis, build, `git diff --check` e validação estrutural dos artefatos OpenSpec. Evidência: TypeScript e build de produção sem erros após limpar referência obsoleta no cache gerado do Next; ESLint sem erros (2 avisos preexistentes de `<img>`); Ruff sem erros; validação OpenSpec estrita da change passou; `git diff --check` sem falhas.
- [x] 3.3 Registrar evidências e revisar que não houve persistência de arquivos, migration, alteração de dados financeiros ou remoção indevida da galeria privada. Evidência: o HTML é montado em memória, com prioridade para prévia histórica e fallback para `admin_preview`, sem escrita de arquivo de exportação; não foram alterados schemas/migrations, preços, pagamentos, mídia persistida ou rotas de acesso da cliente.
