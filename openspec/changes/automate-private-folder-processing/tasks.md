## 1. Backend e filas

- [ ] 1.1 Aplicar defaults efetivos 75%/0,0 EV e processamento facial contínuo às pastas `selected`, sem herdar nem permitir pausa/desligamento locais; preservar tenant isolation e pastas públicas.
- [ ] 1.2 Aguardar o job facial mais recente bem-sucedido antes da fila de prévias; em mudança de parâmetros cancelar a geração anterior e re-enfileirar fotos reconhecidas a partir dos derivados limpos.
- [ ] 1.3 Adaptar contratos administrativos e limpeza para refletir defaults privados, progresso, retentativa e processamento sempre ativo.

## 2. Interface

- [ ] 2.1 Simplificar o painel embutido do Acervo do Cliente: remover seletores e ações manuais, manter barras de progresso e renomear a retentativa para “Refazer reconhecimento”.
- [ ] 2.2 Salvar intensidade/exposição automaticamente em cada pasta privada e empilhar os cartões em uma coluna no desktop, mantendo o recolhimento atual da pasta.

## 3. Integração e publicação

- [ ] 3.1 Atualizar specs e documentação; executar testes direcionados, lint, typecheck, build e OpenSpec estrito com evidências.
- [ ] 3.2 Revisar o diff, publicar a branch e preparar PR; aguardar gate de homologação do `DEPLOY.md` antes de merge que dispare deploy.
