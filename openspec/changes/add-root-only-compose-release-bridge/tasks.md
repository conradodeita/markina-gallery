# Tasks

## 1. Ponte root-only

- [x] 1.1 Criar fixtures sintéticas para labels, snapshots e estados Docker; verificar rejeição de path traversal/symlink/permissão/hash divergente, perfil fora da combinação fixa, saída com segredo sentinela e chamadas sem root. Evidência: 34 testes em `validation.md`.
- [x] 1.2 Implementar inventário read-only root-only que selecione somente API/web, derive fontes por serviço e valide raízes/metadados/hashes; reproduzir label existente ou exigir prova semântica autorizada quando ausente, sem expor JSON/ambiente bruto. Evidência: fixtures de descoberta e prova em `validation.md`; ativação real segue na seção 5.
- [x] 1.3 Implementar cópias root-only e comandos Compose em allowlist, exigir marcadores/lock/recibo protegido e preservar fontes. Evidência: testes de checksum adulterado e aplicação/rollback sintéticos só de API/web em `validation.md`.

## 2. Integração com release API/web

- [x] 2.1 Integrar ponte ao executor mantendo Git/lock/gates existentes. Evidência: 5 regressões de release/rollback e 6 contratos finais shell passaram; IDs vêm de labels e cada modelo é provado por serviço.
- [x] 2.2 Pinar script app no forced-command wrapper e helper no script app; preservar modos read-only da chave de preflight. Evidência: testes de blob, corpo adulterado, SHA e política passaram.
- [x] 2.3 Adicionar instalador protegido com backup verificado, metadados, troca atômica e recusa de argumentos inseguros. Evidência: sintaxe, fixture de rejeição antes de privilégio e política de workflow passaram; instalação real segue em 5.1.

## 3. Workflow, política e runbook

- [x] 3.1 Integrar dispatch protegido da ponte/wrapper e allowlist exata; política impede instalação por PR e mantém ambientes corretos. Evidência: 23 testes de escopo, 16 do classificador e política de workflow passaram.
- [x] 3.2 Atualizar runbook e artefatos com saída permitida, estado privado, impacto, aprovação/fingerprint e rollback; referências revisadas contra executores versionados.
- [x] 3.3 Fechar gates locais focados, OpenSpec estrito, diff e segredos. Evidências e limites em `validation.md`.

## 4. Integração e CI

- [x] 4.1 Revisar escopo/segredos e diff exato, executar os gates locais aplicáveis, criar commit Conventional e push da branch; verificar CI completo e corrigir cada falha em commits restritos à change até ficar verde. Evidência: SHA `94662062f7f2dffd9df78714c305035e7dbbbdf7`, workflow `44307098266` concluído verde; jobs de instalação/deploy ficaram pulados com `operation=none`.
- [ ] 4.2 Abrir PR, acompanhar CI/revisões, corrigir achados válidos e integrar somente quando todos os gates exigidos estiverem verdes; confirmar SHA integrado e CI de `main`.

## 5. Ativação protegida e deploy

- [ ] 5.1 Instalar helper e wrapper no host apenas pelo workflow protegido; verificar host, backup, `root:root 0755`, SHA-256/blob, recusa de comando arbitrário e invariância de containers/configuração.
- [ ] 5.2 Executar inventário root-only read-only para o SHA integrado; confirmar fingerprint, estado minimizado, equivalência permitida, schema `20261113_0126`, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true` e preservação dos snapshots sem revelar configuração.
- [ ] 5.3 Após aprovação protegida vinculada ao fingerprint, publicar somente API/web sem migrations, mudança `.env`, alteração de dados, workers, backup ou serviços vizinhos; se qualquer gate falhar, não avançar para mutação e registrar causa.
- [ ] 5.4 Confirmar IDs de imagem e versão, saúde/HTTPS, schema intacto, flag facial `true`, fontes e cópias recuperáveis; registrar evidência final no OpenSpec e checklist anterior.

## Workflow follow-up

- Sincronizar a spec principal e arquivar a change somente após revisão humana final, conforme as instruções do projeto.
