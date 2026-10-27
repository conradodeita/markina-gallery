# Design

## Context

Ver `proposal.md` e o contrato `specs/deployment-operations/spec.md`. A última evidência operacional versionada registra runtime `c1944189761799be96eeeb921cad9906484d8b09` em schema `20261025_0089`, com entrada `127.0.0.1:8080` e domínio `https://markina.pickyourpic.com.br`. O candidato de aplicação será `0dd015a62447e0c8d4c6af16b381140c8118f2ec`, integrado à `main` com as PRs #295, #296 e #297; o run de CI #40384426091 para o push desse SHA estava em andamento durante a revisão e SHALL estar verde antes do release. Esses valores são apenas pré-condições históricas: inventário remoto atual precisa confirmá-los.

O release API/web padrão recusa migrations e permanece inalterado. A nova operação é pontual; não habilita migrations arbitrárias nem altera o fluxo facial, Orders ou a execução genérica do serviço Compose `migrate` (`alembic upgrade head`).

## Goals / Non-Goals

**Goals:** permitir a aplicação autorizada de `20261026_0090` sobre schema `20261025_0089`, seguida da publicação do candidato exato, com inventário, backup verificável, isolamento de escritores e recuperação compatível.

**Non-Goals:** criar um framework geral de migrations; mudar o classificador comum de `protected`; publicar qualquer alteração fora da allowlist exata do candidato integrado; atualizar Compose, Nginx, banco, Redis, Evolution, workers faciais ou serviços de terceiros; alterar o conteúdo da migration `0090`.

## Decisions

**Diagnóstico da falha real #916:** a listagem inclui containers Markina parados, mas a validação aborta sem identificar a duplicidade ou nome ausente. Acrescentar ao erro somente nome de serviço reconhecido no Compose, estados Docker e contagem; não expor ambientes, IDs, comandos ou dados de clientes. Preservar a recusa e a inspeção de todos os containers, sem ignorar duplicidades. Atualizar os dois pins do inventário e reinstalar o wrapper por meio protegido antes de repetir o preflight; a alteração não autoriza deploy nem limpeza.

O mesmo inventário referencia `MIGRATION` sem definição na verificação da cadeia candidata. Definir o caminho da migration fixa 0090 e testar a busca da cadeia com respostas sintéticas, incluindo recusa de revisão divergente, sem usar rede ou alterar dados.

O run 40426457963 confirma dois `web`, um running e um exited. Emitir somente classificações normalizadas dos dois containers: nome canônico sim/não, rótulo one-off sim/não/ausente, número Compose padrão/outro/ausente, política de restart e igualdade de imagem. Não exibir nomes brutos, IDs, digests, ambiente, montagens ou outros rótulos. A consulta continua abortando sem fingerprint; a decisão sobre containers históricos depende de evidência e análise do efeito de `compose up`.

Após o run 40432429879, o proprietário pediu diagnóstico dos containers possivelmente obsoletos. Ampliar somente a saída do conflito web com prefixo hexadecimal de ID, presença e categorias fixas dos rótulos Compose, quantidade de montagens com escrita, código de saída, classificação indicativa da referência de imagem e versão numérica do Compose. Nenhum nome bruto de imagem/container, conteúdo ou caminho de montagem, variável ou credencial é impresso. O prefixo identifica o candidato para investigação, não autoriza exclusão. O resultado segue falhando fechado e não produz fingerprint. Apenas os dois containers web já envolvidos no conflito são inspecionados; outros projetos são excluídos pelo filtro de projeto existente.

Para evitar novas rodadas por conflito adicional e atender à auditoria pedida pelo proprietário, quando o conflito ocorrer coletar até 100 containers do projeto Markina antes de falhar e emitir resumo limitado de cada um: serviço reconhecido ou desconhecido, estado normalizado, prefixo de ID, status one-off, restart, classificação indicativa de imagem, exit code e quantidade de montagens graváveis. Conferir o rótulo exato de projeto de cada objeto e rejeitar prefixos inválidos ou duplicados. O resumo não avalia descartabilidade e nunca imprime caminhos ou dados de outros projetos. A regra que examinava apenas os dois web é substituída por esta consulta sanitizada mais abrangente, ainda somente leitura e sem gerar fingerprint.

1. **Operação exclusiva por SHA e revisão.** O workflow terá operações manuais separadas para instalação do wrapper read-only, `preflight` e `release`, somente em `main`. O alvo de runtime é `0dd015a62447e0c8d4c6af16b381140c8118f2ec`. A execução #899 passou para `db839cc67cd55595c8571ab66ef8fc51286bdde1`, mas não representa o alvo. O run `40384426091`/#901 para o candidato concluiu `success`; a allowlist foi conferida localmente contra esse SHA e CI. O diff desde `c194418...` corresponde às alterações revisadas das PRs #295/#297 e à migration única `20261026_0090`. Nenhuma outra mudança é admitida.

2. **Preflight fail-closed.** O preflight, por chave restrita somente-leitura, confirma SHA/runtime, schema exato `20261025_0089`, chain Alembic até `20261026_0090`, checkout limpo, serviços/saúde, Compose efetivo, overlays ativos, portas, domínio e disponibilidade/recibo de backup. Gera fingerprint sanitizado que inclui o alvo e todo estado que afeta a operação. Divergência, coleta incompleta, backup não restaurável ou wrapper sem pin aprovado interrompe antes de qualquer mutação.

3. **Aprovação e lock separados.** O release exige despacho posterior com o fingerprint integral do inventário apresentado ao proprietário. Recoleta o estado sob o mesmo lock exclusivo usado pelos releases atuais e compara o fingerprint imediatamente antes de modificar serviços. A chave mutável só existe no job protegido e não é acessível ao preflight.

4. **Ordem e escopo da janela.** Construir previamente as imagens API/web do SHA alvo. Durante a barreira de manutenção, parar graciosamente somente API e workers Markina que escrevam ou leiam as tabelas afetadas, conferindo saída/ociosidade e preservando jobs duráveis; não parar outros serviços por nome/tag presumidos. Validar o backup antes de iniciar DDL. Executar explicitamente `alembic upgrade 20261026_0090` com a imagem API alvo — nunca `upgrade head` —, confirmar schema, então iniciar API/web candidatos e retomar os mesmos workers inventariados, compatíveis com o schema expandido. Remover a barreira apenas depois de healthchecks e smoke HTTPS.

5. **Compatibilidade e recuperação.** A migração apenas amplia CHECK constraints e preserva linhas. Se falhar antes de DDL, restaurar checkout/serviços anteriores. Se falhar depois de DDL, manter o schema `0090`, preservar backup e fechar o tráfego; o runtime anterior é compatível com as constraints ampliadas e pode ser retomado após verificação, sem downgrade ou restauração de dados automáticos. Qualquer restauração de banco é outra operação explicitamente aprovada.

6. **Wrapper root-owned.** Uma operação manual dedicada no environment `production` instala somente o wrapper versionado pelo SHA/blob de suporte, preserva backup e confirma `root:root 0755`; não altera `authorized_keys`, serviços, banco nem runtime. O wrapper SSH instalado no host reconhecerá somente os comandos fixos de inventário, com blob/hash revisado e pinado, e continuará recusando shell/comandos arbitrários. Nenhum segredo ou conteúdo de Compose resolvido será registrado.

## Risks / Trade-offs

- **Base ativa mudou desde o registro:** o fingerprint e as exigências de SHA/schema abortam antes de construir ou mutar; renovar inventário e plano em vez de atualizar pins presumidamente.
- **Migration começou e falhou:** preservar DDL e tráfego fechado; não fazer downgrade nem `pg_restore` automático; exigir diagnóstico e aprovação específica de recuperação.
- **Worker ativo ou job em andamento:** aguardar parada graciosa e preservar fila; timeout, processo ainda terminando ou identidade divergente aborta antes da migration.
- **Fingerprint contém dado operacional sensível:** registrar somente campos minimizados, hashes e contagens aprovados; nunca valores de `.env`, payloads, nomes de cliente ou JSON Compose resolvido.

## Migration Plan

1. Implementar e validar os gates/scripts para o candidato integrado `0dd015a...`, abrir PR focada e obter CI verde para a change. O CI do candidato de runtime passou no run #40384426091; #899 em `db839cc...` não substituiu esse gate.
2. Mesclar o fluxo revisado; atualizar e conferir a cópia root-owned do wrapper por procedimento autorizado, sem ampliar a chave restrita.
3. Despachar preflight somente-leitura e apresentar runtime, schema, serviços, portas, domínio, backup, impacto, fingerprint e recuperação; interromper se qualquer item diferir do baseline `c194418...`/`0089`.
4. Após aprovação explícita do fingerprint, despachar release; confirmar schema `0090`, runtimes, saúde e HTTPS, registrar evidência minimizada e fechar a change somente após revisão humana.

## Open Questions

Nenhuma questão de arquitetura foi deixada em aberto. O inventário atual de produção e o fingerprint final só podem ser conhecidos no preflight; eles não alteram o desenho e qualquer divergência bloqueia a execução.
