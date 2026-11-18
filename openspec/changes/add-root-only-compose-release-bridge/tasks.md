# Tasks

## 1. Ponte root-only

- [x] 1.1 Criar fixtures sintéticas para labels, snapshots e estados Docker; verificar rejeição de path traversal/symlink/permissão/hash divergente, perfil fora da combinação fixa, saída com segredo sentinela e chamadas sem root. Evidência: 34 testes em `validation.md`.
- [x] 1.2 Implementar inventário read-only root-only que selecione somente API/web, derive fontes por serviço e valide raízes/metadados/hashes; reproduzir label existente ou exigir prova semântica autorizada quando ausente, sem expor JSON/ambiente bruto. Evidência: fixtures de descoberta e prova em `validation.md`; ativação real segue na seção 5.
- [x] 1.3 Implementar cópias root-only e comandos Compose em allowlist, exigir marcadores/lock/recibo protegido e preservar fontes. Evidência: testes de checksum adulterado e aplicação/rollback sintéticos só de API/web em `validation.md`.

## 2. Integração com release API/web

- [x] 2.1 Integrar ponte ao executor mantendo Git/lock/gates existentes. Evidência: 5 regressões de release/rollback e 6 contratos finais shell passaram; IDs vêm de labels e cada modelo é provado por serviço.
- [x] 2.2 Pinar script app no forced-command wrapper e helper no script app; preservar modos read-only da chave de preflight. Evidência: testes de blob, corpo adulterado, SHA e política passaram.
- [x] 2.3 Adicionar instalador protegido com backup verificado, metadados, troca atômica e recusa de argumentos inseguros. Evidência: sintaxe, fixture de rejeição antes de privilégio e política de workflow passaram; instalação real foi confirmada em 5.1.
- [x] 2.4 Aceitar no instalador somente as origens canônicas HTTPS e SSH comprovadas no checkout de produção; testar aceitação e recusa sem reescrever `origin`. Evidência: allowlist Bash aceita as três formas exatas HTTPS/SSH URI/SCP e rejeita nove variantes; 34 testes passaram e um teste de symlink real foi pulado no Windows, Ruff, sintaxe Bash, OpenSpec estrito e `git diff --check` passaram.
- [ ] 2.5 Aceitar snapshots preexistentes em `deploy-state` pertencentes a `root` ou ao proprietário do checkout somente quando toda a árvore for privada a esses owners; manter cópias de recuperação `root:root` root-only e recusar proprietário/modo, symlink, hard link ou hash divergente. Validação local passou; CI/Gitleaks, preflight protegido e confirmação das fontes intactas após inventário continuam pendentes.

## 3. Workflow, política e runbook

- [x] 3.1 Integrar dispatch protegido da ponte/wrapper e allowlist exata; política impede instalação por PR e mantém ambientes corretos. Evidência: 23 testes de escopo, 16 do classificador e política de workflow passaram.
- [x] 3.2 Atualizar runbook e artefatos com saída permitida, estado privado, impacto, aprovação/fingerprint e rollback; referências revisadas contra executores versionados.
- [x] 3.3 Fechar gates locais focados, OpenSpec estrito, diff e segredos. Evidências e limites em `validation.md`.

## 4. Integração e CI

- [x] 4.1 Revisar escopo/segredos e diff exato, executar os gates locais aplicáveis, criar commit Conventional e push da branch; verificar CI completo e corrigir cada falha em commits restritos à change até ficar verde. Evidência: SHA `94662062f7f2dffd9df78714c305035e7dbbbdf7`, workflow `44307098266` concluído verde; jobs de instalação/deploy ficaram pulados com `operation=none`.
- [ ] 4.2 Abrir PR, acompanhar CI/revisões, corrigir achados válidos e integrar somente quando todos os gates exigidos estiverem verdes; confirmar SHA integrado e CI de `main`. PR #379, PR #380 e PR #381 foram integrados, sendo #381 no SHA `45f4408de5d9149aaf033e18d296d17f600d84a9`; seus checks de PR passaram. O workflow `44357612611` passou nos gates de código e integrou o preflight, que falhou read-only com `snapshot_file_permissions_invalid`; não houve fingerprint nem alteração de produção. A correção de compatibilidade está implementada localmente e aguarda PR/CI e nova execução de `main`.

## 5. Ativação protegida e deploy

- [x] 5.1 Instalar helper e wrapper no host apenas pelo workflow protegido; verificar host, backup, `root:root 0755`, SHA-256/blob, recusa de comando arbitrário e invariância de containers/configuração. Evidência: workflow `44351587356` instalou ponte SHA-256 `861d42ba7d81a968807b9cacb6e9aa54afb539ac666573c2c2643931cff38ad7` e wrapper SHA-256 `1be07387d87f8e1479d68edfe06b6e90cd01858dcc86fc55ffe927c453e6f443`, ambos `root:root 0755`; backup anterior conferido e containers inalterados. Verificação SSH read-only independente confirmou hashes e metadados.
- [ ] 5.2 Executar inventário root-only read-only para o SHA integrado; confirmar fingerprint, estado minimizado, equivalência permitida, schema `20261113_0126`, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true` e preservação dos snapshots sem revelar configuração. O workflow `44357612611` chegou ao inventário, mas parou antes do fingerprint com `snapshot_file_permissions_invalid`; a comparação read-only confirmou API `root:root 0600` em diretórios `0700` e web `ubuntu:ubuntu 0600` em diretórios `0700`, com checkout/proprietário UID `1001`. A regra foi corrigida localmente para aceitar somente essa árvore privada; aguarda PR/merge e repetição do preflight. Nada foi alterado no host.
- [ ] 5.3 Após aprovação protegida vinculada ao fingerprint, publicar somente API/web sem migrations, mudança `.env`, alteração de dados, workers, backup ou serviços vizinhos; se qualquer gate falhar, não avançar para mutação e registrar causa.
- [ ] 5.4 Confirmar IDs de imagem e versão, saúde/HTTPS, schema intacto, flag facial `true`, fontes e cópias recuperáveis; registrar evidência final no OpenSpec e checklist anterior.

## Workflow follow-up

- Sincronizar a spec principal e arquivar a change somente após revisão humana final, conforme as instruções do projeto.
