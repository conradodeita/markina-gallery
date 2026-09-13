## 1. Conteúdo e consentimento

- [x] 1.1 Atualizar o aviso do diálogo para explicar finalidade restrita à galeria, processamento temporário, eliminação automática, expiração dos resultados, limitações e alternativa manual; verificar os textos no teste do componente. Evidência: o diálogo renderiza finalidade, ausência de cadastro permanente, 15 minutos, 24 horas, possibilidade de erro e alternativa manual; teste direcionado aprovado.
- [x] 1.2 Tornar a confirmação de pai, mãe ou responsável legal e o consentimento infantil específicos e destacados, preservando os gates atuais; verificar bloqueio sem aceite e envio válido com teste direcionado. Evidência: novo teste comprova ambos os controles inicialmente desmarcados, bloqueio sem declaração e envio com headers opacos vigentes após os dois aceites.
- [x] 1.3 Recomendar foto frontal semelhante a foto de documento e esclarecer que documento oficial não deve ser enviado; verificar a orientação renderizada no teste do componente. Evidência: orientação de enquadramento e proibição explícita de enviar documento verificadas no componente.

## 2. Experiência mobile

- [ ] 2.1 Ajustar os estilos compartilhados do diálogo facial para largura e altura dinâmicas, rolagem interna e ações alcançáveis em mobile; verificar estruturalmente os estilos e inspecionar viewport mobile.
- [ ] 2.2 Confirmar que mensagens de erro, campos e ações permanecem legíveis sem corte ou sobreposição em viewport mobile reduzida.

## 3. Validação cirúrgica

- [x] 3.1 Executar somente os testes direcionados do diálogo facial, lint e TypeScript aplicáveis, corrigindo regressões causadas pela change sem rodar a suíte completa. Evidência: 10 testes de `facial-search-panel.test.tsx`, ESLint dos dois arquivos do componente e `tsc --noEmit` aprovados; suíte completa não executada conforme orientação humana.
- [x] 3.2 Validar a change com OpenSpec estrito, executar `git diff --check` e revisar que não houve alteração de API, banco, retenção ou pipeline facial. Evidência: OpenSpec estrito e `git diff --check` aprovados; diff funcional restrito ao componente, seu teste e CSS, sem backend, migration ou configuração operacional.

## 4. Entrega em homologação

- [ ] 4.1 Preparar branch e commits focados, apresentar inventário de impacto zero, publicar a change por PR e merge autorizados e confirmar CI direcionada/obrigatória.
- [ ] 4.2 Acompanhar o deploy autorizado em homologação e verificar SHA, healthchecks, configuração facial preservada e apresentação do diálogo em viewport mobile; manter revisão jurídica de produção infantil explicitamente pendente.
