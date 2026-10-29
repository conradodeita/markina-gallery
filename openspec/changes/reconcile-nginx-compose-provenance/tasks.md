# Tasks

## 1. Diagnóstico e candidato

- [x] 1.1 Isolar somente-leitura a origem ausente e as limitações do modelo remanescente; verificar metadados do projeto e HTTPS e registrar evidência sanitizada. Ver `validation.md`: fonte RAW ausente somente no Nginx; Gemma incompleto; hash divergente; `/healthz` 200.
- [x] 1.2 Inventariar configuração efetivamente carregada, imagem, montagens, redes/aliases, políticas e snapshot de todos os containers próprios; demonstrar comparação sem valores secretos, caminhos sensíveis ou dumps no Git e registrar hashes/limites no runbook. Coletor executado read-only em Python 3.8.10/Compose 2.35.1, com modelo válido por stdin; snapshot de 21 peers, três hashes de configuração e redes preservadas. Ver `validation.md` e `operations.md`.
- [ ] 1.3 Preparar candidato persistente restrito ao Nginx e recuperação independente do arquivo ausente; verificar consistência Compose normal, equivalência de todos os campos e resolução de cada diferença com fixtures direcionadas e comparação read-only do runtime. Não aprovar somente imagem/montagens iguais. Candidato e resolução read-only implementados; falta a prova Docker de recriação/equivalência no CI Linux.

## 2. Executor restrito e evidência

- [x] 2.1 Implementar preflight sanitizado, fingerprint e guarda de execução exclusiva; verificar recusa antes de writes para snapshot alterado, aprovação ausente, fonte inválida, outro projeto e artefato de recuperação indisponível. Quinze testes sintéticos aprovados em Linux descartável, incluindo trava real, backup HMAC autenticado, recusa de override e código de falha sanitizado; ver `validation.md`.
- [ ] 2.2 Implementar backup persistido/autenticado, atualização exclusiva do Nginx e recuperação por imagem/configuração anteriores, sem dependências ou serviços aposentados; verificar sucesso e falhas em ambiente descartável com fixtures próprias, comprovando preservação do restante do projeto. Executor e ensaio Docker implementados; aguardam prova real no CI Linux, sem operação mutável no Oracle.
- [x] 2.3 Atualizar o runbook e revisar somente os helpers afetados conforme a política de refatoração; executar validação focalizada, lint aplicável, OpenSpec estrito e revisão do diff antes de PR. Não criar suítes ou pushes apenas de documentação intermediária. Runbook e revisão focalizada completos; 15 testes Linux, Ruff, Bash, YAML, AST 3.8, OpenSpec estrito e diff check aprovados. Prova de publicação/recovery real continua nas tasks 1.3/2.2.

## 3. Publicação e retomada

- [ ] 3.1 Após CI/revisão, obter inventário atual e apresentar plano específico com domínio, porta, fingerprint, imagens, impacto e backup/recuperação verificados; registrar aprovação humana desse plano antes de mutação remota.
- [ ] 3.2 Executar somente o plano aprovado, revalidando snapshot e exclusividade; comprovar Nginx/configuração saudáveis, HTTPS 200 e igualdade dos demais containers. Recuperar pelo procedimento aprovado se falhar, sem writes de banco ou alteração financeira.
- [ ] 3.3 Repetir o inventário APP_ENV oficial e registrar seu recibo real; concluir apenas a reconciliação comprovada, mantendo pendências/aprovações próprias de `transition-app-env-bound-integrations` e `enable-mercadopago-production`.

## Workflow follow-up

- Manter a change ativa até revisão humana; sincronizar/arquivar somente comportamento efetivamente validado e publicado.
