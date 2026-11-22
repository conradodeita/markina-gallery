# Design

## Context

Ver proposal.md — Why. O runtime já possui inventário normal que falha fechado quando não consegue identificar univocamente os containers Compose fixos. O diagnóstico precisa explicar essa falha sem virar fonte de identidade operacional nem ampliar a superfície de comandos.

## Goals / Non-Goals

**Goals:**
- Tornar observável a quantidade agregada de registros e seus estados para `api`, `web` e `db`.
- Preservar o inventário normal, a recusa de ambiguidade e todos os gates existentes.
- Evitar que saídas Docker ou dados identificadores cheguem ao operador.

**Non-Goals:**
- Selecionar qual container deve ser usado, corrigir labels, remover duplicatas ou reconciliar containers.
- Emitir fingerprint, precondições, elegibilidade operacional ou recomendações de mutação.
- Instalar runtime, vincular Drive, executar ensaio, copiar/restaurar banco ou ativar serviço/timer.
- Expor diagnóstico na interface SaaS ou consultar serviços de outros projetos.

## Decisions

1. **Escopo fixo e agregado.** Consultar exclusivamente o projeto Compose autorizado e os papéis `api`, `web` e `db`. Retornar uma linha por papel com quantidade total e contagens de estado, limitando a 512 registros por papel; exceder o limite produz falha estática sem dados parciais. Nenhuma identidade individual acompanha a resposta. Alternativa descartada: incluir nomes, IDs ou labels para facilitar reconciliação, pois amplia exposição e pode transformar o diagnóstico em mecanismo de seleção.

2. **Mapeamento conservador de estado.** `running` conta somente `running`; `stopped` conta somente `created`, `exited` ou `dead`; `unknown` inclui estado ausente ou inválido e qualquer estado diferente dessa lista fechada, incluindo `paused`, `restarting` e `removing`. O mapeamento não interpreta texto livre nem converte estados inesperados em `stopped`. Alternativa descartada: tratar todo estado diferente de `running` como parado, o que esconderia estados transitórios ou incompletos.

3. **Canal operacional explícito e somente leitura.** A consulta será uma operação nominal do wrapper root-only existente, com argumentos fechados e sem aceitar comandos, labels, projeto ou serviços definidos pelo chamador. O wrapper vinculará a operação à revisão exata da main, conferirá o blob fixado do inventário e adquirirá o lock comum de release. O workflow acionará o diagnóstico em um job read-only sob o ambiente protegido `production-preflight`, depois de validar a CI do SHA exato e sem montar o bundle do runtime. Após aceitar o agregado, chamará o inventário normal com o mesmo SHA, manterá a resposta privada e publicará somente o código de ambiguidade esperado; não captura fingerprint nem precondições. O resultado agregado é JSON estrutural allowlisted; falhas retornam um código estático e não incluem contagens parciais. Alternativa descartada: comando SSH ad hoc ou texto de subprocesso, incompatíveis com a fronteira operacional protegida.

4. **Instalação verificável durante ambiguidade.** O instalador do forced command mantém o preflight/fingerprint da aplicação e a identidade do host como gate de autorização; após a troca atômica, ele executa o código do diagnóstico fixado no SHA exato sob o lock que já detém, valida a resposta agregada, prova o modo arbitrário recusado e confere a invariância dos containers. A execução direta do módulo evita reabrir o mesmo lock pelo wrapper aninhado. Não exige fingerprint de backup que a ambiguidade impede, não usa contagens para aprovar instalação do runtime e preserva rollback diante de falha de comando, formato ou invariância dos containers. O inventário normal continua sendo executado separadamente e falha fechado. Alternativa descartada: manter a exigência de fingerprint de backup no instalador do wrapper, pois impediria instalar o próprio caminho read-only necessário para explicar a ambiguidade.

5. **Aprovação permanece independente.** O caminho normal de inventário não consumirá contagens para escolher um container. Mesmo depois do diagnóstico, toda instalação, vínculo ou ensaio precisará de um novo inventário normal bem-sucedido, fingerprint atual e gates próprios. Alternativa descartada: aceitar um único registro ativo entre vários como substituto da identidade exata; isso relaxaria o contrato já aprovado.

6. **Sem alteração de runtime da aplicação ou dados.** A mudança fica no artefato do suporte operacional e sua CI; não requer migration, alteração de Compose, API/web, Drive ou configuração. Reversão consiste em retirar a referência operacional do diagnóstico pelo mecanismo protegido e manter a versão anterior do wrapper disponível.

7. **Binding de destino usa a saída do preflight atual.** O job `install-wrapper`, no ambiente `production`, calcula o binding de sua própria conexão SSH a partir de `PRODUCTION_SSH_HOST/PORT/USER` e compara esse hash diretamente com `needs.preflight.outputs.connection_binding`. Não tenta reler `PRODUCTION_PREFLIGHT_*` no ambiente `production`, pois variáveis escopadas ao ambiente `production-preflight` não ficam disponíveis ao job de escrita. A igualdade continua sendo obrigatória antes de qualquer SSH de escrita; fingerprint e CI exata permanecem validadas separadamente.

8. **Módulo de diagnóstico vem do commit aprovado e é validado antes da escrita.** A instalação `44972964072` passou CI, preflight, fingerprint e binding no SHA `f4faa90ee5eea3518130383d201ec68784ab6729`, mas o checkout ativo do servidor ainda estava em `492c141cd998efc87ebde1ee81ea9101effb4f7c`. O instalador leu `scripts/platform_backup_runtime_inventory.py` do working tree antigo e comparou seus bytes com o blob da main aprovada; falhou depois de trocar o forced command e antes de chamar Docker. A ponte já preparada e o forced command instalado tinham o mesmo conteúdo pinado; a cópia root-only anterior foi preservada, e o inventário read-only posterior `44973222412` confirmou API/web saudáveis e healthchecks HTTPS 200. A correção obterá os bytes do módulo por `git show "$support_sha:path"` para arquivo temporário sob `umask 077`, verificará o hash Git desse arquivo contra o blob do mesmo SHA e fará isso antes de qualquer troca do forced command. Não atualizará o checkout operacional, não instalará módulo persistente nem permitirá fallback para arquivo do working tree. Fonte ausente ou divergente aborta sem escrita; falhas posteriores continuam acionando rollback. Alternativa descartada: atualizar o checkout de produção, pois isso ampliaria a operação para publicação da aplicação.

## Risks / Trade-offs

- [Contagens podem variar enquanto o daemon muda] → O resultado é diagnóstico pontual, não aprovação; qualquer operação posterior repete o inventário e exige fingerprint atual.
- [Classificação pode ocultar um estado Docker novo] → O estado não allowlisted vai para `unknown`; adicionar estados reconhecidos exige teste e revisão.
- [Até contagens agregadas revelam informação operacional] → Limitar saída aos três papéis fixos, restringir ao canal interno e não persistir detalhes individuais.
- [Erro parcial pode induzir uma conclusão incorreta] → Descartar todas as contagens se qualquer listagem/inspeção/validação falhar e emitir somente o código estático.

## Migration Plan

Não há migração de banco nem alteração do serviço/timer. Após revisão da change e validação do SHA exato na CI, qualquer instalação do suporte e consulta do host deverão seguir o fluxo protegido com inventário prévio, autorização operacional específica e verificação posterior de que os containers permaneceram inalterados. O rollback usará a referência anterior preservada pelo instalador. O diagnóstico nunca habilita o destino nem inicia operação de backup.
