# Tasks

## 1. Diagnóstico e candidato

- [x] 1.1 Isolar somente-leitura a origem ausente e as limitações do modelo remanescente; verificar metadados do projeto e HTTPS e registrar evidência sanitizada. Ver `validation.md`: fonte RAW ausente somente no Nginx; Gemma incompleto; hash divergente; `/healthz` 200.
- [x] 1.2 Inventariar configuração efetivamente carregada, imagem, montagens, redes/aliases, políticas e snapshot de todos os containers próprios; demonstrar comparação sem valores secretos, caminhos sensíveis ou dumps no Git e registrar hashes/limites no runbook. Coletor executado read-only em Python 3.8.10/Compose 2.35.1, com modelo válido por stdin; snapshot de 21 peers, três hashes de configuração e redes preservadas. Ver `validation.md` e `operations.md`.
- [x] 1.3 Preparar candidato persistente restrito ao Nginx e recuperação independente do arquivo ausente; verificar consistência Compose normal, equivalência de todos os campos e resolução de cada diferença com fixtures direcionadas e comparação read-only do runtime. Não aprovar somente imagem/montagens iguais. Candidato e recuperação passaram à prova Docker isolada do CI Linux `40849402115` no SHA `f1ab3a66`; ver `validation.md`.

## 2. Executor restrito e evidência

- [x] 2.1 Implementar preflight sanitizado, fingerprint e guarda de execução exclusiva; verificar recusa antes de writes para snapshot alterado, aprovação ausente, fonte inválida, outro projeto e artefato de recuperação indisponível. Dezesseis testes sintéticos aprovados em Linux descartável, incluindo trava real, backup HMAC autenticado, recusa de override, código de falha sanitizado e montagem de recuperação; ver `validation.md`.
- [x] 2.2 Implementar backup persistido/autenticado, atualização exclusiva do Nginx e recuperação por imagem/configuração anteriores, sem dependências ou serviços aposentados; verificar sucesso e falhas em ambiente descartável com fixtures próprias, comprovando preservação do restante do projeto. Publicação, recuperação após falha injetada, backup corrompido e drift de peer passaram na prova Docker isolada do CI Linux `40849402115` no SHA `f1ab3a66`; sem operação mutável no Oracle.
- [x] 2.3 Atualizar o runbook e revisar somente os helpers afetados conforme a política de refatoração; executar validação focalizada, lint aplicável, OpenSpec estrito e revisão do diff antes de PR. Não criar suítes ou pushes apenas de documentação intermediária. Runbook e revisão focalizada completos; testes Linux, Ruff, Bash, YAML, AST 3.8, OpenSpec estrito, diff check e prova Docker de publicação/recuperação registrados em `validation.md`.
- [x] 2.4 Tornar as recusas de preflight do wrapper diagnosticáveis por códigos constantes, sem expor entradas ou saídas de comandos; validar as guardas e registrar as falhas operacionais somente-leitura que motivaram o ajuste. Dezoito testes focados passaram no Linux isolado (zero skips) e no Windows (cinco skips POSIX); inclui comparação das formas canônicas do remoto e proteção contra origem de outro repositório/host. Ruff, Bash `-n`, OpenSpec estrito e `git diff --check` passaram. Ver `validation.md`.

## 3. Publicação e retomada

- [ ] 3.1 Após CI/revisão, obter inventário atual e apresentar plano específico com domínio, porta, fingerprint, imagens, impacto e backup/recuperação verificados; registrar aprovação humana desse plano antes de mutação remota.
- [ ] 3.2 Executar somente o plano aprovado, revalidando snapshot e exclusividade; comprovar Nginx/configuração saudáveis, HTTPS 200 e igualdade dos demais containers. Recuperar pelo procedimento aprovado se falhar, sem writes de banco ou alteração financeira.
- [ ] 3.3 Repetir o inventário APP_ENV oficial e registrar seu recibo real; concluir apenas a reconciliação comprovada, mantendo pendências/aprovações próprias de `transition-app-env-bound-integrations` e `enable-mercadopago-production`.

## Workflow follow-up

- Manter a change ativa até revisão humana; sincronizar/arquivar somente comportamento efetivamente validado e publicado.
