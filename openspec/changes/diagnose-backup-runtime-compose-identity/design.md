# Design

> **Registro histórico — fluxo aposentado em 25/11/2026.** A consulta de identidade do runtime global descrita nesta change foi tornada obsoleta pela retirada do código exclusivo na PR #436 (`eff4d504`). Não reativar este fluxo. A retirada remanescente está em `retire-platform-backup-runtime`; a nova prova de backup/recuperação está em `prove-open-source-backup-and-recovery`. O conteúdo abaixo permanece apenas para rastreabilidade; nenhuma spec principal compartilhada foi removida.

## Context

Ver [proposal.md](proposal.md). O diagnóstico atual usa filtros fixos de labels do Docker e informa somente contagens por estado. A consulta normal continua recusando qualquer serviço que não tenha exatamente um ID completo, e a configuração Compose de produção tem caminho e nome de projeto fixos.

## Goals / Non-Goals

**Goals:**

- Determinar, por contagens agregadas, se os registros dos labels fixos também aparecem na listagem somente de leitura da configuração Compose vigente.
- Continuar falhando fechado quando a consulta não puder validar todas as fontes e limitar o resultado ao escopo `api`, `web` e `db` de `markina-gallery`.

**Non-Goals:**

- Transformar o resultado em identidade canônica, fingerprint operacional ou aprovação para instalação, vínculo, ensaio, backup ou recuperação.
- Selecionar, renomear, parar ou remover containers; consultar outros projetos ou alterar a configuração Compose.

## Decisions

1. **Comparar conjuntos de IDs apenas em memória.** Para cada papel fixo, comparar IDs completos obtidos pela consulta Docker com labels Compose do projeto/serviço e por `docker compose ps --all --quiet --no-trunc --orphans=false`, com `--project-name markina-gallery`, `--project-directory /opt/markina-gallery/docker` e arquivo `/opt/markina-gallery/docker/docker-compose.yml` fixos. A resposta contém os totais de cada fonte, interseção e diferenças por papel. IDs nunca entram no JSON, stdout, logs ou fingerprint. A documentação oficial confirma que `ps --all` inclui containers parados, `--quiet` retorna somente IDs e `--orphans=false` exclui serviços órfãos. Alternativa descartada: comparar nomes gerados ou imprimir registros individuais, que não prova identidade e amplia exposição.

2. **Validar as duas fontes de forma completa e atômica.** Cada lista deve conter no máximo 512 IDs completos, únicos e válidos. A consulta Compose deve ser somente de leitura e a consulta Docker continua limitada pelos labels exatos existentes. Falha, saída inválida ou mudança detectada entre as leituras aborta toda a resposta com código estático; não se publica resultado parcial. Alternativa descartada: aceitar saída truncada, parcial ou IDs abreviados.

3. **Manter a guarda normal independente.** O inventário normal segue exigindo exatamente um ID completo por papel e revalidando os labels depois da inspeção. O novo agregado não pode ser consumido pela função normal nem pelo caminho `operate`; operações posteriores devem repetir o inventário estrito e passar todos os gates existentes. Alternativa descartada: escolher um registro que aparece nas duas fontes ou priorizar estado `running`.

4. **Não persistir nem instalar junto com a implementação local.** A change altera somente o módulo, schema do diagnóstico, wrapper allowlisted, parser do workflow e testes. Não altera Compose, API/web, banco, Drive ou systemd. Qualquer publicação do wrapper e nova consulta do servidor continuam sujeitas ao preflight protegido, à revisão da change e à autorização operacional aplicável.

## Risks / Trade-offs

- [O conjunto pode mudar durante a comparação] → Recoletar as listas após a inspeção e recusar a saída se os conjuntos diferirem.
- [A versão do Compose pode não aceitar uma opção fixa] → Tratar falha de execução ou saída incompatível como erro estático, sem fallback para seleção por nome ou consulta ampla.
- [Contagens idênticas não explicam por que os registros estão parados] → Declarar explicitamente que o resultado não reconcilia a causa; manter identidade ambígua bloqueada e exigir investigação operacional separada.
- [A saída do Compose pode conter avisos] → Capturar stdout/stderr internamente e emitir somente o schema agregado aprovado ou um código estático.

## Migration Plan

Não há migration de banco nem mudança de configuração. A implementação local deverá atualizar os parsers e testes do contrato do diagnóstico. A consulta no host só será considerada depois da revisão humana da change, da CI do SHA exato, do preflight protegido e da autorização operacional; o resultado não habilita serviço, timer, destino ou backup.

Referência técnica: [Docker Compose `ps`](https://docs.docker.com/reference/cli/docker/compose/ps/).
