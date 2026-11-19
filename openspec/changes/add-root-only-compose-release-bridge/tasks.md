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
- [x] 2.5 Aceitar snapshots preexistentes em `deploy-state` pertencentes a `root` ou ao proprietário do checkout somente quando toda a árvore for privada a esses owners. Cópias de recuperação permanecem `root:root` root-only, com recusa de proprietário/modo, symlink, hard link ou hash divergente. Evidência: testes locais, CI/Gitleaks e resolução real das fontes privadas no segundo preflight de `44374037053`; diagnóstico somente leitura confirmou fontes intactas. A equivalência dos containers ativos permanece bloqueada na task 5.2.

## 3. Workflow, política e runbook

- [x] 3.1 Integrar dispatch protegido da ponte/wrapper e allowlist exata; política impede instalação por PR e mantém ambientes corretos. Evidência: 23 testes de escopo, 16 do classificador e política de workflow passaram.
- [x] 3.2 Atualizar runbook e artefatos com saída permitida, estado privado, impacto, aprovação/fingerprint e rollback; referências revisadas contra executores versionados.
- [x] 3.3 Fechar gates locais focados, OpenSpec estrito, diff e segredos. Evidências e limites em `validation.md`.

## 4. Integração e CI

- [x] 4.1 Revisar escopo/segredos e diff exato, executar os gates locais aplicáveis, criar commit Conventional e push da branch; verificar CI completo e corrigir cada falha em commits restritos à change até ficar verde. Evidência: SHA `94662062f7f2dffd9df78714c305035e7dbbbdf7`, workflow `44307098266` concluído verde; jobs de instalação/deploy ficaram pulados com `operation=none`.
- [ ] 4.2 Abrir PR, acompanhar CI/revisões, corrigir achados válidos e integrar somente quando todos os gates exigidos estiverem verdes; confirmar SHA integrado e CI de `main`. PRs #379–#381 foram integrados. A correção de compatibilidade de snapshots foi integrada em #382 (`d1a4f8930aad681b962452111a0e10a66d1e5103`) e a reutilização de CI para o instalador em #383 (`8e702c36bed16f834ca70cd28bc65ce78bf5bff1`). No workflow de `main` `44392683081`, os gates de código passaram, mas o inventário remoto somente leitura falhou; os jobs de release foram pulados. Não há fingerprint nem mudança de produção. Esta change Engine ainda precisa de prova isolada, PR/CI verdes, integração e novo CI de `main`.

## 5. Ativação protegida e deploy

- [x] 5.1 Instalar helper e wrapper no host apenas pelo workflow protegido; verificar host, backup, `root:root 0755`, SHA-256/blob, recusa de comando arbitrário e invariância de containers/configuração. Evidência: workflow `44351587356` instalou ponte SHA-256 `861d42ba7d81a968807b9cacb6e9aa54afb539ac666573c2c2643931cff38ad7` e wrapper SHA-256 `1be07387d87f8e1479d68edfe06b6e90cd01858dcc86fc55ffe927c453e6f443`, ambos `root:root 0755`; backup anterior conferido e containers inalterados. Verificação SSH read-only independente confirmou hashes e metadados.
- [ ] 5.2 Executar inventário root-only read-only para o SHA integrado; confirmar fingerprint, estado minimizado, equivalência permitida, schema `20261113_0126`, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true` e preservação dos snapshots sem revelar configuração. O workflow `44357612611` falhou inicialmente em permissões; a comparação read-only posterior confirmou a árvore privada de snapshots e a versão integrada em #382 foi instalada por workflow protegido. O CI `44392683081` chegou ao passo de inventário somente leitura e falhou antes de emitir fingerprint; o job de release foi pulado. A causa técnica específica desse passo permanece pendente de diagnóstico seguro. As tarefas 6.1–6.3 formalizam a prova Engine exigida para o par promovido em 17/11. Nada foi alterado no host por esses preflights.
- [ ] 5.3 Após aprovação protegida vinculada ao fingerprint, publicar somente API/web sem migrations, mudança `.env`, alteração de dados, workers, backup ou serviços vizinhos; se qualquer gate falhar, não avançar para mutação e registrar causa.
- [ ] 5.4 Confirmar IDs de imagem e versão, saúde/HTTPS, schema intacto, flag facial `true`, fontes e cópias recuperáveis; registrar evidência final no OpenSpec e checklist anterior.

## Workflow follow-up

- Sincronizar a spec principal e arquivar a change somente após revisão humana final, conforme as instruções do projeto.

## 6. Prova do par promovido em 17/11

- [ ] 6.1 Verificar recibo root-only, pin SHA-256, SHA/IDs/imagens/schema e projeção efetiva pela mesma fronteira. Testar recusas e preservar caminhos Compose genéricos.
- [ ] 6.2 Preparar e comprovar ambos os candidatos Engine sem tráfego e registrar journal de promoção/recuperação. Exercitar a execução e a recuperação, inclusive falha parcial, com Docker isolado antes de efeito real.
- [ ] 6.3 Validar escopo, testes de contrato, pins, OpenSpec e CI. Reexecutar o fluxo protegido sem duplicar CI para o mesmo SHA sempre que houver evidência elegível.

### Tentativa CI do PR #384

- A tentativa `44411391749` executou a prova Engine, mas ela terminou com `protected_command_failed`. O traceback minimizado percorreu `_engine_discover → _inspect_api_web → _list_service_ids → _docker → _run` e caiu no tratamento de `OSError`/timeout após 19 s; os comandos do harness via `PATH` já haviam criado recursos sintéticos. Isso sustenta a hipótese de diferença no caminho `/usr/bin/docker` do runner. A prova corrigida foi implementada localmente com adaptador limitado e testes unitários; manter 6.2 pendente até a nova prova Engine real completar no CI.
- A tentativa `44418238541`, no SHA `9380992bb86828e85dd480f77e4297e6fc4203fb`, repetiu a falha no mesmo passo em 16 s, apesar do adaptador de caminho do CLI. Gitleaks, OpenSpec, escopo, frontend, imagens AMD64/ARM64 e os três shards de backend passaram. O traceback sanitizado ainda termina no `except (OSError, subprocess.TimeoutExpired)` de `_run`. Inspeção do código mostra que o default `cwd=PROJECT_ROOT` foi capturado como `/opt/markina-gallery` no import, distinto do diretório do checkout. É a hipótese dominante, não confirmada porque o detalhe exato de `OSError` é minimizado. O harness foi corrigido para encaminhar somente o `cwd` implícito ao checkout após `require_ci_runner()`, preservando cwd explícito e sem alterar a ponte de produção. A suíte local ficou verde; a prova Docker real segue reservada ao runner CI.
- A tentativa `44424649626`, no SHA `25fc7f7ef829e66034af7077c97667144bbc7dee`, passou os três shards do backend e falhou em `backend-quality` no passo da prova Engine, agora com `api_web_container_count_invalid` após chegar a `select_api_web`. A causa foi confirmada no código: o argumento padrão `project=PROJECT` do seletor foi capturado como `markina-gallery`, enquanto o cenário sintético altera `bridge.PROJECT` para um nome exclusivo. Os jobs de política agregada/Gemma também ficaram vermelhos por gates dependentes; deploy e jobs mutáveis foram pulados. O harness foi corrigido para usar `bridge.PROJECT` atual somente quando o seletor omite `project`, preservando argumento explícito e helper de produção. Suíte local: 59 testes, 58 passaram e 1 skip de symlink no Windows; Ruff, `py_compile`, OpenSpec estrito e `git diff --check` também passaram.
- A tentativa `44428285088`, SHA `b36c38087cacd087d768527938a6d44d87b18235`, passou os três shards do backend e os demais checks de código, mas falhou em `backend-quality` na prova Engine com `engine_original_pair_mismatch`; jobs agregados/dependentes falharam em consequência e os jobs mutáveis foram pulados. A adaptação de projeto resolveu a falha anterior. O helper compara `_engine_revision(item)` a `ENGINE_BOOTSTRAP_SHA`; o harness declarava `OLD_REVISION = "1" * 40`, incompatível com o SHA de bootstrap fixo. A revisão dos fixtures foi alinhada ao valor pinado, com contrato unitário local; 60 testes, 59 passaram e 1 skip de symlink no Windows, Ruff, `py_compile`, OpenSpec estrito e `git diff --check` passaram.
