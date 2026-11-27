# Design

## Context

Ver `proposal.md` para a motivação. Hoje `replacement_document` copia o modelo Compose ativo, e `handoff_recover_service` pode iniciar diretamente o container original retido. A especificação da ponte exige que testemunhas históricas permaneçam paradas e intactas. O inventário de aposentadoria inclui containers parados; portanto, remover a origem do bind sem uma receita de recuperação diferente deixaria o rollback dependente de um arquivo apagado.

O proprietário escolheu manter rollback de API/web sem restaurar o Picker em 26/11/2026. A autorização deste checkpoint cobre o desenho local; qualquer release, escrita ou remoção no host mantém seus próprios gates.

## Goals / Non-Goals

**Goals:**

- Manter recuperação de API/web por imagem e modelo Compose comprovados, sem recuperar o mount ou a chave do Picker.
- Preservar as testemunhas antigas como histórico imutável e permitir que o inventário as diferencie de containers em execução ou ainda elegíveis para rollback.
- Liberar a retirada posterior do arquivo exato do Picker sem alterar OAuth, banco, mídias, containers testemunha ou projetos vizinhos.

**Non-Goals:**

- Reativar Picker, recriar sua chave, alterar OAuth, remover testemunhas antigas ou limpar imagens, redes, volumes e recursos Docker.
- Alterar schema, registros, filas, dados de clientes, Drive ou qualquer armazenamento de arquivo frio.
- Executar release, recovery ou remoção em produção nesta change documental.

## Decisions

1. **Receita de recuperação, em vez de iniciar o container antigo.** Durante a preparação protegida, salvar sob a árvore root-only o image ID, o modelo efetivo, ambiente, redes, mounts, fase e hashes do serviço ativo e saudável observado no inventário. Derivar uma cópia de recuperação removendo somente o bind de arquivo cujo source seja `/etc/pyp-google-drive/picker-config.json` e cujo target seja `/run/secrets/google-drive-picker-config.json`. A imagem e todos os campos restantes permanecem pinados. `handoff-recovery-apply` cria um container novo por geração Compose isolada; não chama `docker start` no witness antigo.

   - Se source/target cobrir diretório ancestral, se o bind não for exato, ou se houver ambiguidade entre Picker e OAuth, não há sanitização automática: o plano bloqueia e mantém o estado atual. Isso evita remover o mount de `/etc/pyp-google-drive/oauth-client.json` junto com o Picker.
   - O código antigo pode ainda conter a interface/rota aposentada. A recuperação não restaura credencial nem funcionalidade do Picker; o teste sintético SHALL comprovar que a aplicação ativa inicializa e mantém saúde sem esse arquivo. Se não inicializar, o cleanup permanece bloqueado e este design precisa ser revisto.

2. **Testemunha preservada, não elegível para iniciar.** O container original permanece parado, sem start/stop/rename/remove e com identidade/configuração integral registrada. A receita nova é a única fonte de rollback. O inventário só deixa de tratar o bind dessa testemunha como ativo se o estado for exatamente parado, a identidade/mounts corresponderem ao registro privado, e o recibo/receita vigente provar que ela não é candidata. Todos os metadados dos mounts continuam no digest da fingerprint. Container ativo, desconhecido, alterado ou sem prova continua bloqueando. O helper local verifica que a ponte root-only instalada tem exatamente o blob da revisão aprovada; a ponte compara a observação atual com o registro privado e emite somente fingerprint e atestações de identidade/configuração/lifecycle. Qualquer divergência ou inventário incompleto falha sem fingerprint.

3. **Recriação transacional limitada a API/web.** O recovery usa Compose em geração nova, imagens imutáveis existentes, redes/volumes externos já comprovados e modelo root-only. O journal registra intenção/fase e IDs novos. API precisa ficar saudável antes da troca de web; healthchecks e endpoints são verificados antes de publicar o receipt. Nenhum `down`, prune, alteração de witness, remoção de volume, SQL ou migration é permitido.

4. **Sem fallback automático.** Divergência ou falha depois de iniciar a recuperação não tenta iniciar o witness Picker nem troca de imagem/modelo. O journal e todos os artefatos conhecidos são preservados. Uma nova recuperação exige inventário do estado atual, fingerprint novo, revisão e aprovação protegida própria.

5. **A remoção do arquivo é uma etapa separada e ligada ao recibo atual.** Só após CI/merge da capability, release API/web saudável sem o mount e recibo da receita picker-free, o inventário de aposentadoria pode produzir fingerprint atual. O recibo deve ligar o journal root-only ativo e suas duas fases saudáveis ao schema verificado, à receita e aos modelos/imagens pinados, ao manifesto/base ativa e aos IDs observados de API/web; a ponte revalida mounts Docker e HostConfig para provar ausência do caminho do Picker. O helper de inventário confere o blob da ponte root-only na revisão aprovada e valida a saída exata. A operação `retire-backup-runtime` exige esse recibo no snapshot aprovado e o coleta novamente sob o mesmo lock/fingerprint antes de qualquer remoção; se recibo, receita, runtime, mounts ou fingerprint divergirem, aborta sem remover. O pós-check exige que o recibo e o digest agregado dos containers permaneçam iguais. A retirada continua limitada aos caminhos fixos e ao arquivo Picker; ela não altera Docker. Os containers witness parados são permitidos somente pela prova da decisão 2. OAuth, banco, dados de clientes e diretório pai compartilhado permanecem fora dos alvos.

## Risks / Trade-offs

- [A imagem ativa depende do segredo para iniciar] → Exercitar as imagens ativas com Compose e dependências sintéticas antes de concluir o gate; qualquer falha mantém a retirada bloqueada.
- [O modelo sanitizado diverge do container antigo] → Preservar no journal o modelo de origem, aplicar somente a remoção exata do bind e comparar todos os demais campos, imagens e mounts antes/depois.
- [Testemunha é confundida com container inativo descartável] → Exigir registro privado de ID/configuração, estado parado e digest exato; não aceitar somente nome, label ou status genérico.
- [Falha parcial deixa API/web em fases diferentes] → Persistir journal antes de cada efeito, exigir inventário/fingerprint de recovery e nunca executar rollback automático.
- [OAuth compartilha diretório com o Picker] → Não apagar o diretório pai; recusar binds ancestrais e manter o mount OAuth e seus metadados na fingerprint.

## Migration Plan

1. Implementar localmente a receita picker-free, o inventário de witnesses, o recovery API/web e testes sintéticos com falhas injetadas.
2. Integrar por PR revisada, CI verde na `main` exata e atualizar OpenSpec. Esta etapa não altera o servidor.
3. Executar inventário protegido somente-leitura atual, revisar fingerprint, ports/domínio, API/web/schema/saúde, witnesses e plano de impacto zero.
4. Com autorização operacional própria e aprovação do ambiente protegido, publicar API/web pelo handoff e verificar saúde e o receipt da recuperação picker-free.
5. Fazer novo inventário e obter aprovação própria da fingerprint para a retirada exata. Remover apenas o arquivo do Picker por workflow protegido; confirmar endpoints e preservação de OAuth/schema/dados.
6. Se qualquer etapa divergir ou não comprovar que a receita do par ativo inicia sem Picker, manter a configuração no host e bloquear a remoção; nunca usar SSH manual como alternativa.

Decisão do proprietário: o ensaio e a recuperação usam a mesma referência saudável em produção. Capturar API e web na mesma observação; conferir identidade, imagens, modelos e saúde ao preparar. Se a referência mudar, repetir o diagnóstico antes da troca. O histórico permanece para auditoria.

A operação `export-images` no workflow de recovery executa diagnóstico atualizado e exporta somente as imagens ativas API/web pelo ForcedCommand restrito. O exportador confere serviço, projeto comprovado pela ponte, image ID e plataforma linux/arm64. O runner valida o arquivo gzip e a imagem importada, publica SHA-256 e artifacts separados por serviço, com retenção de um dia. Esses arquivos contêm somente camadas/configuração da imagem, sem exportar ambiente de container, volumes ou dados de clientes. A exportação não recria containers nem libera recovery ou retirada. Divergência de identidade aborta o ensaio. O comando API já usado no release continua aceito.

A observação read-only de 27/11/2026 identificou tmpfs /run:rw,nosuid,nodev,noexec,size=16m na API ativa, com binds de arquivo separados para OAuth e Picker. O bloqueio do run #46011319633 ocorreu na preparação, antes da troca. A receita admite exclusivamente esse ponto canônico /run quando há um único bind exato Picker e OAuth exato somente leitura. As opções do tmpfs são validadas pela função existente e copiadas sem alteração. Sobreposição em /run/secrets ou caminhos não canônicos continuam recusados. O ensaio deve incluir esse tmpfs e comprovar que o arquivo Picker não existe após inicialização.
