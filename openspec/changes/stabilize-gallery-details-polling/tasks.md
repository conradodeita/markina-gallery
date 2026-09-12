## 1. Contratos de estabilidade

- [ ] 1.1 Criar teste com temporizadores controlados para reproduzir duas respostas `processing` na Etapa 03 e verificar que `Abrindo a galeria` não reaparece depois da carga inicial.
- [ ] 1.2 Cobrir preservação de valor digitado e foco durante polling, conclusão em `ready`, encerramento do timer, falha transitória contida e cleanup após navegação.

## 2. Polling localizado da capa

- [ ] 2.1 Separar a consulta inicial do editor da sincronização silenciosa dos detalhes e verificar que atualizações periódicas não alternam o estado global `loading`.
- [ ] 2.2 Atualizar somente estado/URL da capa durante o acompanhamento, preservando a prévia editável e os campos não salvos; verificar os contratos de edição concorrente.
- [ ] 2.3 Garantir um único timer, descarte de resposta obsoleta, término em estado terminal e erro recuperável junto da capa; verificar todos os ramos com temporizadores falsos.

## 3. Validação e entrega

- [ ] 3.1 Executar testes direcionados do editor de galeria, ESLint dos arquivos alterados, typecheck e OpenSpec estrito; revisar o diff para confirmar ausência de alteração em API, worker, banco ou mídia.
- [ ] 3.2 Validar manualmente a Etapa 03 com capa em processamento sem piscar nem perder edição; preparar inventário de impacto zero e solicitar autorização humana específica antes de push, merge ou deploy em homologação.
