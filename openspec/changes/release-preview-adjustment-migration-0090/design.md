# Design

## Context

Ver `proposal.md` e o contrato `specs/deployment-operations/spec.md`. A última evidência operacional versionada registra runtime `c1944189761799be96eeeb921cad9906484d8b09` em schema `20261025_0089`, com entrada `127.0.0.1:8080` e domínio `https://markina.pickyourpic.com.br`. O candidato de aplicação será `0dd015a62447e0c8d4c6af16b381140c8118f2ec`, integrado à `main` com as PRs #295, #296 e #297; o run de CI #40384426091 para o push desse SHA estava em andamento durante a revisão e SHALL estar verde antes do release. Esses valores são apenas pré-condições históricas: inventário remoto atual precisa confirmá-los.

O release API/web padrão recusa migrations e permanece inalterado. A nova operação é pontual; não habilita migrations arbitrárias nem altera o fluxo facial, Orders ou a execução genérica do serviço Compose `migrate` (`alembic upgrade head`).

## Goals / Non-Goals

**Goals:** permitir a aplicação autorizada de `20261026_0090` sobre schema `20261025_0089`, seguida da publicação do candidato exato, com inventário, backup verificável, isolamento de escritores e recuperação compatível.

**Non-Goals:** criar um framework geral de migrations; mudar o classificador comum de `protected`; publicar qualquer alteração fora da allowlist exata do candidato integrado; atualizar Compose, Nginx, banco, Redis, Evolution, workers faciais ou serviços de terceiros; alterar o conteúdo da migration `0090`.

## Decisions

1. **Operação exclusiva por SHA e revisão.** O workflow terá operações manuais separadas de `preflight` e `release`, somente em `main`. O alvo de runtime é `0dd015a62447e0c8d4c6af16b381140c8118f2ec`. A execução #899 passou para `db839cc67cd55595c8571ab66ef8fc51286bdde1`, mas não representa o alvo; o run #40384426091/#901 para o SHA candidato ainda estava em andamento na última consulta. O diff candidato desde `c194418...` deve coincidir com os runtimes aprovados do ajuste de prévias, com as alterações de checkout revisadas das PRs #295/#297 e com a migration única `20261026_0090`. Nenhuma outra mudança posterior é admitida.

2. **Preflight fail-closed.** O preflight, por chave restrita somente-leitura, confirma SHA/runtime, schema exato `20261025_0089`, chain Alembic até `20261026_0090`, checkout limpo, serviços/saúde, Compose efetivo, overlays ativos, portas, domínio e disponibilidade/recibo de backup. Gera fingerprint sanitizado que inclui o alvo e todo estado que afeta a operação. Divergência, coleta incompleta, backup não restaurável ou wrapper sem pin aprovado interrompe antes de qualquer mutação.

3. **Aprovação e lock separados.** O release exige despacho posterior com o fingerprint integral do inventário apresentado ao proprietário. Recoleta o estado sob o mesmo lock exclusivo usado pelos releases atuais e compara o fingerprint imediatamente antes de modificar serviços. A chave mutável só existe no job protegido e não é acessível ao preflight.

4. **Ordem e escopo da janela.** Construir previamente as imagens API/web do SHA alvo. Durante a barreira de manutenção, parar graciosamente somente API e workers Markina que escrevam ou leiam as tabelas afetadas, conferindo saída/ociosidade e preservando jobs duráveis; não parar outros serviços por nome/tag presumidos. Validar o backup antes de iniciar DDL. Executar explicitamente `alembic upgrade 20261026_0090` com a imagem API alvo — nunca `upgrade head` —, confirmar schema, então iniciar API/web candidatos e retomar os mesmos workers inventariados, compatíveis com o schema expandido. Remover a barreira apenas depois de healthchecks e smoke HTTPS.

5. **Compatibilidade e recuperação.** A migração apenas amplia CHECK constraints e preserva linhas. Se falhar antes de DDL, restaurar checkout/serviços anteriores. Se falhar depois de DDL, manter o schema `0090`, preservar backup e fechar o tráfego; o runtime anterior é compatível com as constraints ampliadas e pode ser retomado após verificação, sem downgrade ou restauração de dados automáticos. Qualquer restauração de banco é outra operação explicitamente aprovada.

6. **Wrapper root-owned.** O wrapper SSH instalado no host reconhecerá apenas os comandos fixos deste preflight, com blob/hash revisado e pinado; a instalação será um passo operacional separado, verificando `root:root`, modo `0755`, preservando backup anterior e recusando shell/comandos arbitrários. Nenhum segredo ou conteúdo de Compose resolvido será registrado.

## Risks / Trade-offs

- **Base ativa mudou desde o registro:** o fingerprint e as exigências de SHA/schema abortam antes de construir ou mutar; renovar inventário e plano em vez de atualizar pins presumidamente.
- **Migration começou e falhou:** preservar DDL e tráfego fechado; não fazer downgrade nem `pg_restore` automático; exigir diagnóstico e aprovação específica de recuperação.
- **Worker ativo ou job em andamento:** aguardar parada graciosa e preservar fila; timeout, processo ainda terminando ou identidade divergente aborta antes da migration.
- **Fingerprint contém dado operacional sensível:** registrar somente campos minimizados, hashes e contagens aprovados; nunca valores de `.env`, payloads, nomes de cliente ou JSON Compose resolvido.

## Migration Plan

1. Implementar e validar os gates/scripts para o candidato integrado `0dd015a...`, abrir PR focada e obter CI verde para a change. A execução #40384426091 do candidato de runtime também deve estar verde; #899 em `db839cc...` não satisfaz esse requisito.
2. Mesclar o fluxo revisado; atualizar e conferir a cópia root-owned do wrapper por procedimento autorizado, sem ampliar a chave restrita.
3. Despachar preflight somente-leitura e apresentar runtime, schema, serviços, portas, domínio, backup, impacto, fingerprint e recuperação; interromper se qualquer item diferir do baseline `c194418...`/`0089`.
4. Após aprovação explícita do fingerprint, despachar release; confirmar schema `0090`, runtimes, saúde e HTTPS, registrar evidência minimizada e fechar a change somente após revisão humana.

## Open Questions

Nenhuma questão de arquitetura foi deixada em aberto. O inventário atual de produção e o fingerprint final só podem ser conhecidos no preflight; eles não alteram o desenho e qualquer divergência bloqueia a execução.
