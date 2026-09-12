## 1. Contratos de estabilidade

- [x] 1.1 Criar teste com temporizadores controlados para reproduzir duas respostas `processing` na Etapa 03 e verificar que `Abrindo a galeria` não reaparece depois da carga inicial. Evidência: teste com relógio falso percorre duas consultas de 1,5 s e confirma a permanência do editor; suíte direcionada passou com 48 testes.
- [x] 1.2 Cobrir preservação de valor digitado e foco durante polling, conclusão em `ready`, encerramento do timer, falha transitória contida e cleanup após navegação. Evidência: contratos confirmam o mesmo elemento focado com valor `74`, conclusão sem novo timer, cleanup no unmount e retentativa após erro local.

## 2. Polling localizado da capa

- [x] 2.1 Separar a consulta inicial do editor da sincronização silenciosa dos detalhes e verificar que atualizações periódicas não alternam o estado global `loading`. Evidência: polling consulta somente `/details`; carga global ocorre somente na primeira abertura do passo e o teste não encontra `Abrindo a galeria` durante atualização.
- [x] 2.2 Atualizar somente estado/URL da capa durante o acompanhamento, preservando a prévia editável e os campos não salvos; verificar os contratos de edição concorrente. Evidência: resposta periódica atualiza `details` sem reinicializar `visualPreview`; o teste mantém valor e foco até `ready`.
- [x] 2.3 Garantir um único timer, descarte de resposta obsoleta, término em estado terminal e erro recuperável junto da capa; verificar todos os ramos com temporizadores falsos. Evidência: efeito limpa timer e invalida resposta no cleanup, não agenda após `ready` e apresenta alerta com `Atualizar estado da capa` após falha transitória.

## 3. Validação e entrega

- [x] 3.1 Executar testes direcionados do editor de galeria, ESLint dos arquivos alterados, typecheck e OpenSpec estrito; revisar o diff para confirmar ausência de alteração em API, worker, banco ou mídia. Evidência: 48 testes passaram; ESLint sem erros, `tsc --noEmit`, OpenSpec estrito e `git diff --check` aprovaram; backend, banco e worker não foram alterados nesta change.
- [ ] 3.2 Preparar e apresentar inventário de impacto zero, executar o push, merge e deploy em homologação já autorizados pelo usuário e validar manualmente a Etapa 03 com capa em processamento sem piscar nem perder edição. Evidência parcial: inventário apresentado, PR `#70` mergeado em `develop` no SHA `af2b0c00fb5762a4d43f8cddb233edd0b68c618b` e deploy `34665380268` aprovado em homologação; pipeline completo aprovado. Permanece pendente a conferência humana durante um processamento real de capa na Etapa 03.
