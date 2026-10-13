## 1. Contrato e processamento por pasta

- [x] 1.1 Confirmar defaults, configuração independente e autorização por fotógrafo na base integrada `4fe9b68`, reutilizando `FolderProcessingSettings` e a API existentes, sem nova migration; cobrir tentativa de acesso a pasta de outro fotógrafo.
- [x] 1.2 Estender o reprocessamento automático após mudança de intensidade/exposição às pastas públicas, preservando o encadeamento facial privado, invalidação de geração, fonte limpa e isolamento de outros jobs/pastas/fotógrafos.
- [x] 1.3 Consolidar a visão de reconhecimento e ajuste no painel contextual compartilhado para a pasta selecionada; remover cards globais duplicados e botões de salvar/processar em lote, mantendo comparação protegida e retentativa facial.

## 2. Progresso estável do upload

- [x] 2.1 Registrar regressão do desaparecimento do contador e da piscada, reproduzida antes da correção na base atual.
- [x] 2.2 Manter o lote identificado pela pasta de destino visível durante troca de seleção e polling, preservar progresso real em bytes e evitar limpeza/remontagem da tela em consultas de atualização.
- [x] 2.3 Exibir resumos compactos por pasta sem repetir os controles completos, cobrindo lista com dez pastas restritas.

## 3. Monitor, higiene e integração

- [x] 3.1 Verificar que seleção de pasta não cria trabalho e que reprocessamento real aparece corretamente nas filas e telemetria do Monitor, preservando autorização e sem contagem duplicada da interface.
- [x] 3.2 Remover apenas componentes, estados, handlers, estilos e testes comprovadamente obsoletos deste fluxo; registrar a revisão do diff contra a base integrada.
- [x] 3.3 Executar regressões relevantes backend/frontend, lint, typecheck, build e OpenSpec estrito; registrar evidências e limites da validação local.
