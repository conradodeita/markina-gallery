# Validação e continuidade

## Escopo desta execução

Autorização do proprietário: engenharia local/GitHub, branch, testes, revisão, PR e merge condicionado a checks/revisões obrigatórios e ausência de efeitos em ambientes. Nenhuma escrita Oracle autorizada. A fase operacional terá solicitação conjunta própria. A change de dependências permanece com task 3.2 pendente até publicação autorizada.

Base de engenharia: main `81eb0741ab824a74a1f2b4f3df4dfb86da81b5c5`, PR #226 já integrado e [CI #39167932644](https://github.com/conradodeita/markina-gallery/actions/runs/39167932644) aprovado. Branch isolada `codex/fix-web-release-state-2026-10-18`; a branch documental anterior e as pastas locais antigas foram preservadas.

## Diagnóstico e reprodução

A auditoria anterior relacionou a imagem web `sha256:9567b1d8e6270fee9b4b8aa68fcf1e67900358e8045d954388109d014e28f573` ao release app fe1f3bc6, por log de build e mesmo container/ID no runtime. Marcador web d9c8 era anterior e não foi editado. Evidência de origem: [run #39135274157 tentativa 2](https://github.com/conradodeita/markina-gallery/actions/runs/39135274157/attempts/2), job 117710134038.

Reprodução sintética com helper do commit 81eb0741: arquivo de lock temporário passou de 21 para 0 bytes. Com helper corrigido, permaneceu em 21 bytes com conteúdo idêntico. Não foi usado o lock Oracle.

## Validações concluídas

- Política web-only e de workflows de produção aprovadas localmente; helpers pinados por blob e wrapper app com hash exato.
- Dez regressões de escopo app e doze de classificação aprovadas, incluindo os dois novos caminhos exatos e recusa de scripts/migrations/workers/Compose não permitidos. Baseline fe1f3bc6, blobs de runtime e revisão 20261017_0084 inalterados.
- Sintaxe Bash dos scripts web/app/state/wrapper aprovada.
- OpenSpec fixado no mesmo CLI do CI: `npx --yes @fission-ai/openspec@1.14.0 validate --strict --all`: 122 itens aprovados, zero falhas. Avisos informativos históricos de outras changes não são falhas nem autorização de arquivamento.
- `git diff --check` aprovado no checkpoint após correção de um espaço final.
- Auditoria npm repetida com manifests inalterados: runtime zero; completo cinco altos/zero críticos na cadeia dev ESLint/braces. Sem aplicação de downgrade ou audit fix force.
- Dois Code Reviews locais por `codex --sandbox read-only --ask-for-approval never review --uncommitted` terminaram com código 0 e sem defeitos acionáveis. O revisor não conseguiu criar temporários para testes em seu sandbox; a validação executável é feita separadamente no ambiente Linux isolado descrito abaixo. Não foi revisão pelo conector GitHub nem aprovação formal de terceiro.

## Contratos em Linux isolado

Contêiner temporário local com imagem preexistente `python:3.13-slim-bookworm`, sem rede, raiz somente leitura, tmpfs de teste, montagem de fontes somente leitura, limite de 512 MiB/2 CPUs. Todos os comandos Docker/Git/HTTPS operacionais dos scripts são stubs; apenas flock sobre arquivo temporário local é real. Nenhum teste usa Oracle, banco ou projeto local de terceiros.

Foram corrigidos defeitos encontrados durante a construção da suíte: pipeline de snapshot não propagava erro, app precisava manter versão API independente do checkout web, tags por SHA colidiam na alternância app/web e metadata de rollback precisava permanecer estável em falha intermediária. Testes confirmam recibos, IDs, configuração, falhas e recusa de drift. Execução completa final: 30 testes aprovados em 164,262 s, zero falhas ou skips no Linux, incluindo flock real. Checkpoint anterior de 26 testes também passou. Os erros iniciais de harness (newline do Windows, consumo de stdin na simulação Compose) foram isolados e corrigidos; não eram testes contra produção. Alterações finais de lint apenas organizam import e explicitam check=False nos subprocessos de teste.

## Proteções e efeitos de GitHub conferidos

Main exige backend, frontend, gemma-runtime, openspec, homolog-inventory-policy e gitleaks, com checks estritos e aplicação a administradores. Contagem obrigatória de aprovações formais = 0; sem ruleset adicional e sem hooks de repositório retornados. Nenhuma proteção foi alterada.

Workflows e gatilhos permanecem iguais à main: pull_request padrão, push main/develop e manuais; sem closed, workflow_run/call ou pull_request_target. Deploy homolog exige push develop; preflights/releases main dependem de escopo app/facial; rollbacks são manuais. O registro antigo remote-test-smoke não tem arquivo nesta linha. Classificação do commit final será executada antes de push/merge; jobs remotos devem ficar skipped.

PR #177 permanece aberto para develop, head e9ce8405c1d53b8015e72b7f1f55a098329b3926; develop b4f15abd6a71585082758062feba7fcfcc225587. Sem integração nessa linha.

## Gates ainda não concluídos neste checkpoint

CI do PR, merge e CI posterior ainda precisam de resultado definitivo antes de marcar a engenharia concluída. Publicação continua não autorizada; nenhum comando SSH foi executado nesta fase de engenharia.

A conferência final desabilitou também a criação de bytecode Python nos entrypoints de inventário, além de optional locks/lazy fetch. O pin app foi recalculado. O CI inicial do PR #227 será substituído por esse head; execução anterior cancelada não conta como aprovação do head final.
