# Tasks

## 1. Extração robusta da referência

- [ ] 1.1 Atualizar o caminho de consulta para normalizar a orientação e detectar/alinha o rosto em resolução adequada sob limites de bytes, pixels, passes e latência, preservando YuNet + SFace, versão, dimensão e contrato do índice; verificar provider/worker no CI do GitHub, sem executar testes localmente.
- [ ] 1.2 Retornar estados sanitizados distintos para ausência de rosto, múltiplos rostos e qualidade insuficiente, mantendo a comparação e a retenção atuais; verificar contratos e ausência de biometria/PII nos diagnósticos pelo CI do GitHub.
- [ ] 1.3 Atualizar documentação OpenSpec e notas operacionais com limites da consulta, custos de CPU, rollback sem migration e ausência de melhora alegada sem ground truth; verificar coerência com os artefatos da change.

## 2. Orientação de captura para a cliente

- [ ] 2.1 Preservar upload de fotos antigas e exigir captura guiada explícita quando a cliente escolher a câmera, exibindo enquadramento e instruções de pose, luz e estabilidade; a validação técnica do servidor deve ocorrer antes da comparação, com orientação de nova tentativa; verificar lint, testes e build executados pelo GitHub CI.
- [ ] 2.2 Apresentar orientação específica para referência inadequada sem afirmar que a pessoa não existe na galeria; verificar fluxos de upload e câmera no CI e aceite visual do proprietário após publicação, sem teste local.

## 3. Publicação automática protegida pelo GitHub

- [ ] 3.1 Ajustar a automação para iniciar o job de produção após merge em `main` e CI verde, exigir o environment protegido `production` antes de mutações e falhar fechado em validação ou aprovação ausente; verificar políticas do workflow pelo GitHub CI.
- [ ] 3.2 Preparar preflight somente leitura que confira SHA, inventário de produção, portas/subdomínio, serviços e isolamento de terceiros; executar somente serviços Pick-your-Pic necessários conforme plano aprovado e documentar rollback; verificar automação e runbook no GitHub CI sem ler ou alterar secrets.
- [ ] 3.3 Confirmar no GitHub que branch, environment/revisores e segredos de deploy já configurados atendem ao workflow, sem imprimir ou modificar valores; registrar bloqueio se configuração da conta exigir ação do proprietário.

## 4. CI e validação de produção

- [ ] 4.1 Abrir PR com somente arquivos desta change, aguardar lint, suítes, build, OpenSpec e varredura de segredos do GitHub; não executar testes localmente nem contornar job vermelho.
- [ ] 4.2 Após merge e disparo automático, apresentar inventário atualizado e plano de impacto zero, aguardar a aprovação do environment `production`, e registrar SHA, serviços, healthchecks e resultado do deploy; nenhuma mutação remota antes desses gates.
- [ ] 4.3 Após o deploy aprovado, o proprietário validar rapidamente com sessão autenticada upload e captura guiada, incluindo uma referência de qualidade difícil e uma imagem de busca negativa; registrar estados, sucesso/zero resultados e orientação exibida, sem colocar imagens, embeddings ou scores no Git.
- [ ] 4.4 Revisar os resultados operacionais, corrigir regressões com nova execução do CI GitHub e só considerar a change concluída após aceite humano e evidência verificável; manter pendentes os critérios de acurácia que dependam de corpus anotado.

## Bloqueios de configuração externos

- A leitura da configuração GitHub em 2026-10-15 encontrou o repositório `conradodeita/markina-gallery` com branch padrão `main`, sem environment `production` e sem secrets de repositório para deploy. Os environments existentes são `homolog` e `homolog-tests`; apenas `homolog` possui credenciais SSH configuradas. A API não reportou regra de proteção para `main`, coerente com a convenção de revisão por PR registrada no `openspec/config.yaml`. Nenhum valor de segredo foi lido.
- As tasks 3.1–3.3 e 4.1–4.4 permanecem pendentes. Antes de qualquer release automático, o proprietário precisa provisionar o environment `production` com revisores obrigatórios e credenciais SSH de produção nesse environment. A infraestrutura observada pela change separada `add-production-web-release-workflow` permite publicar somente `web`; ela não autoriza API ou workers faciais, portanto o plano de publicação dos múltiplos serviços ainda precisa de preflight e runbook específicos.
- Não executar deploy nem publicar workflow que possa transformar automaticamente a ausência do environment protegido em autorização de mutação. Após configuração da conta e revisão do plano de serviços, rever o inventário de produção e o plano de impacto zero antes de habilitar a etapa remota.
