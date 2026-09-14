## 1. Inventário e identidade

- [x] 1.1 Reconciliar conclusão da change dark-mode-and-landscape-covers e inventariar ocorrências da marca por categoria (produto, personalização, histórico, infraestrutura); entregar lista revisável de substituições e exceções. Evidência: inventory.md e commit 7aab730; varreduras de runtime/documentação.
- [x] 1.2 Centralizar nome Pick-your-Pic e atualizar cabeçalhos, entrada, textos acessíveis, metadata/manifesto, offline e exportações; verificar com testes de renderização/contrato e varredura de marca antiga nas superfícies de runtime. Evidência: product-brand.test.tsx (2 aprovados), constantes por camada e varredura frontend sem marca antiga de apresentação.

## 2. Arte e comunicação

- [x] 2.1 Integrar a logo configurada nas superfícies compartilhadas sem duplicar o nome nem alterar a arte; verificar fallback, proporção e contraste em ambos os temas e mobile/desktop. Evidência: 3 testes BrandLogo e QA 48 combinações (entrada/admin/biblioteca × quatro larguras × dois temas × com/sem arte), sem overflow/erro JS; contain e ausência de filtro verificados. Arte sintética somente no mock de teste; uploads reais preservados.
- [x] 2.2 Atualizar comunicações/defaults novos no backend sem alterar dados persistidos; executar testes focados de OTP, recuperação/verificação de e-mail, mensagens e preferências personalizadas preservadas, sem envio real. Evidência: 5 testes direcionados aprovados (21,77 s), sandbox/provedores falsos, banco temporário; marca personalizada não sobrescrita e worker mantém payloads renderizados existentes.

## 3. Documentação e validação

- [x] 3.1 Atualizar documentação vigente e contexto de execução distinguindo produto novo de infraestrutura legada; verificar comandos/URLs intactos e registrar exceções históricas com varredura final. Evidência: README, mandato, roadmap, diretrizes, runbooks e config OpenSpec atualizados; decisão datada anterior preservada e explicitamente supersedida; IDENTIDADE-PICK-YOUR-PIC.md lista exceções.
- [x] 3.2 Executar testes direcionados, lint/typecheck/build e OpenSpec estrito; registrar evidências, inspeção responsiva em dois temas, necessidade de upload individual quando aplicável e limite de atualização de aplicativos instalados. Não executar suíte completa local ou deploy sem solicitação própria. Evidências em validation.md; revisão humana e publicação permanecem etapas próprias.
