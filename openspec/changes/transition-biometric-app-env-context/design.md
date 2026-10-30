# Design

## Correção operacional observada em 30/10/2026

O coordenador integrado pelo PR #345 recusou a preparação em `prepare_inventory`, antes de qualquer manutenção ou escrita financeira/biométrica. Duas consultas consecutivas provaram que somente a ordem de `Mounts` variou; ordenar por `Destination` produziu listas integralmente iguais. Normalizar a lista imediatamente após o inspect torna snapshots, fingerprints e verificações de retomada determinísticos, conservando todos os campos de cada mount. Destinos ausentes/duplicados continuam recusados; nenhum guard é removido. O pacote de fontes também exige `git -c core.autocrlf=false archive` no Windows para preservar exatamente os blobs revisados. Esta correção não modifica o plano de serviços, credenciais, pagamentos ou recuperação.

## Context

Decisão operacional de 29/10/2026 após inspeção SSH: o proprietário aceitou busca facial temporariamente indisponível para priorizar pagamentos, preservando fotos e índices. O caminho inicial SQL fica restrito a embeddings: qualquer job ativo, arquivo/localizador de referência, entrada desconhecida no diretório ou notificação com conteúdo bloqueia a escrita. A indisponibilidade facial deve ser explicitamente aplicada no corte e sua reativação exige procedimento próprio. Não fabricar registros de rollout/calibração para satisfazer o gate.

Atualização de 29/10/2026: o proprietário confirmou que os índices pertencem a fotos reais de galerias em uso. O caminho operacional deverá preservar os dados. O último recibo registra zero arquivos/localizadores e jobs; se confirmado em nova coleta, o caminho transacional PostgreSQL pode avançar independentemente da recuperação multistore. A preparação local não equivale à aprovação de migração real.

A prova de origem deverá considerar `FacialRollout` (ambiente e aprovação do conjunto) e `GalleryFacialPolicy`, além dos vínculos tenant/galeria/foto. O fluxo de indexação operacional não exige um consentimento de upload individual por embedding. Retenção pode ser comprovada pela política do ciclo de vida da galeria, sem prazo por linha; se houver prazo explícito, ele continua vinculante. Provas ausentes/divergentes continuam bloqueadas.

Ver `proposal.md` para a motivação e `specs/privacy-biometric/environment-bound-ciphertexts/spec.md` para o contrato. A change ativa `transition-app-env-bound-integrations` registra que o `APP_ENV` participa do AAD de embeddings, referências, localizadores e notificações, e mantém esses dados fora daquela migração. O inventário atual não autoriza inferir origem, finalidade, consentimento ou retenção de objetos individuais. O roadmap exige minimização, consentimento específico, retenção e exclusão controladas, e limita a autorização de homologação: ela não habilita tratamento biométrico em produção.

## Goals / Non-Goals

**Goals:**

- Definir uma elegibilidade verificável e fail-closed para mover ciphertexts biométricos entre contextos de ambiente.
- Preservar identidade, vínculos, finalidade, consentimento, retenção, auditoria e recuperação sem expor payloads.
- Manter a transição global de `APP_ENV` e a liberação do Mercado Pago como gates separados.

**Non-Goals:**

- Habilitar ou validar busca facial em produção, alterar sua flag ou coletar referências novas.
- Trocar credenciais, keyrings, valores de `APP_ENV` ou configurações externas.
- Excluir automaticamente objetos, mudar consentimentos/retenção ou tratar dados de origem desconhecida como elegíveis.
- Abrir o gate de pagamentos reais ou executar qualquer mutação em produção nesta etapa de proposta.

## Decisions

### Preparação transacional para preservação do índice existente

O comando interno de banco terá fases prepare/apply/verify/recover, com pacote preparado e recibo de pós-write cifrados sob domínios AAD separados. O recibo do estado de destino deve ser persistido e autenticado antes do commit externo. Após interrupção, a presença desse recibo não prova commit: o comando compara o banco com origem/destino antes de decidir recuperar. Ausência de pacote/recibo ou estado misto impede sobrescrita. O runner de banco não pausa Docker nem muda configuração; somente um coordenador de host revisado pode invocá-lo após verificar os consumidores e a exclusividade. Ele recusa execução com facial/live ativos no próprio processo de manutenção e revalida jobs/referências/políticas no banco.

O coordenador de host deve usar a trava `production-release.lock`, exigir CI push/main verde no SHA atual e conferir seu código/backend pelo tree Git oficial antes de carregar helpers. Ele mantém imagens, comandos, volumes e versões efetivamente publicados, materializa configuração explícita apenas para os cinco consumidores e verifica a matriz por serviço em vez de atribuir um SHA novo a imagens antigas. A manutenção retorna HTTP 503 pelo Nginx próprio até concluir verificação/recuperação; o arquivo montado deve ser restaurado byte a byte, sem substituir seu inode durante o reload. A configuração de ambiente e o cofre são recuperáveis por pacote separado cifrado, com alterações limitadas aos rótulos ambientais e flags já autorizados. A liberação live é fase posterior, exige sucesso da transição e mantém o par sandbox e opt-in por tenant.

O pacote de corte deve incluir snapshots dos bindings WhatsApp não secretos. Sua transição atualiza somente `environment`, preservando tenant, instância/telefones, status, auditoria e timestamps. O conjunto atual deve ser exatamente igual ao snapshot autenticado; qualquer ambiente inesperado ou linha adicional bloqueia o lote. Recovery conjunto deve verificar o fingerprint financeiro do pós-write autenticado e restaurar cofre, índices e bindings na mesma transação. Preservar a instância existente não equivale a criar/reconectar/enviar mensagem; a identidade do provedor deve ser validada por leitura antes do plano final.

A classificação de canais deve validar a configuração atual sem alterar o ambiente do processo e confirmar por operações sem envio: SMTP via TLS/auth/NOOP, WhatsApp via consultas de estado/identidade da instância já associada ao tenant. Não criar instância, parear, configurar webhook ou enviar mensagem. Identidades/configurações devem permanecer vinculadas a fingerprints privados dentro do pacote cifrado e ser comparadas após o corte; recibos públicos contêm apenas contagens e sucesso/falha. A mudança de rótulo ambiental deve ser limitada às credenciais da mesma instância/remetente comprovados e autorizados para continuidade, sem copiar segredo entre serviços ou contas.

Persistência do pacote deve exigir filesystem POSIX, diretórios previamente aprovados e separados para pacotes e chaves, ambos do executor e modo 0700. Usar descritores de diretório com `O_NOFOLLOW`, criação exclusiva de arquivos 0600 e fsync de arquivo/diretório. Não sobrescrever operação existente; falha deve deixar o lote incompleto, inacessível a outros usuários e proibido para aplicação. Reabrir os arquivos e conferir bytes/chave antes de autenticar o conteúdo. Nenhum diretório externo é criado implicitamente e Windows não deve fingir garantias POSIX. Antes da execução real, o operador ainda deve aprovar os diretórios/impacto e o coletor protegido deve verificar a persistência.

A confirmação financeira e biométrica deverá compartilhar a mesma conexão e transação PostgreSQL externa. A rotina financeira existente pode aderir por `Session(..., join_transaction_mode="create_savepoint")`; o commit da sessão libera somente o savepoint, nunca a transação externa. Um savepoint conjunto engloba os dois conjuntos de envelopes, fazendo rollback das alterações biométricas se a rotina financeira falhar. A implementação deve autenticar ambos os backups e suas associações ao plano antes da primeira escrita, rejeitar ambientes/contagens divergentes e não atualizar configurações nessa fase. Integrações externas e recuperação de configuração continuam gates separados.

O pacote de preparação SQL deverá cifrar snapshots completos de origem e destino juntos com AES-GCM, chave dedicada explícita e AAD contendo versão, ambientes e fingerprints do inventário/plano. O pacote deve ser persistido fora do repositório e reaberto antes da execução. Seu conteúdo, incluindo IDs, metadados, versões e envelopes, não aparece em relatórios. Reabertura autentica a associação ao plano e valida os tipos/campos completos; antes da substituição, ambos os envelopes devem ser autenticados em memória e seu conteúdo deve ser igual. O coordenador local deve exigir a guarda operacional, exigir confirmação do pacote persistido/reaberto, comparar contagem e snapshots atuais, e executar somente a substituição de envelopes na transação externa. Recovery segue a mesma guarda e comparação exata, invertendo snapshots. Isso prepara o mecanismo; não constitui corte de configuração nem autorização de dados reais.

O diagnóstico SSH confirmou que os 394 índices fora da comparação de versão têm apenas `model_version` diferente da política atual; não faltam política, aviso, base ou retenção, nem há suspensão. O adapter SQL SHALL usar as versões de modelo/qualidade de cada linha no AAD original e preservar todas as colunas além de ciphertext, nonce e key_id. Não promover modelo histórico a vigente, não reindexar nem usar a manutenção criptográfica como aprovação facial. O plano específico de execução deverá identificar o conjunto autorizado, backup autenticado reaberto e snapshots exatos de origem e destino; somente contagens ou aprovação booleana não bastam. O adapter deve participar de uma transação PostgreSQL exclusiva e devolver o controle ao coordenador para confirmação, sem commit autônomo. Para recovery, o estado atual deve coincidir integralmente com o snapshot de destino antes de restaurar os envelopes originais; qualquer mudança concorrente aborta o lote. A execução real e integração com APP_ENV permanecem pendentes.

1. **Classificar por metadados antes de qualquer operação.** O inventário identifica categorias e vínculos de ambiente sem abrir payloads. Origem, finalidade, consentimento, retenção ou autorização de destino desconhecidos deixam o conjunto inelegível e mantêm bloqueada a transição global. O sistema não tenta resolver bloqueios apagando registros.

2. **Usar contextos criptográficos explícitos.** A operação futura receberá contextos validados de origem e destino sem alterar `os.environ` ou o `APP_ENV` ativo. A elegibilidade e a autenticação de cada objeto serão verificadas antes de preparar ciphertexts de destino; chave ausente, divergência de contexto ou objeto incompatível aborta sem fallback.

3. **Não presumir atomicidade entre armazenamentos.** A inspeção de código deverá classificar os objetos em banco, arquivos e filas antes da implementação. Registros transacionais serão atualizados atomicamente; qualquer armazenamento sem transação deverá usar preparação invisível, manifesto de migração e confirmação/recuperação verificáveis. Se não for possível ocultar estados parciais ou provar rollback, aquela classe permanece bloqueada.

4. **Preservar metadados e evitar correlação por conteúdo.** IDs, relações de tenant/galeria/cliente, consentimento, finalidade, retenção e auditoria permanecem. Texto claro existirá somente em memória. Relatórios, logs, temporários e recibos não registrarão payloads, IDs, caminhos, valores ou hashes derivados do conteúdo biométrico; validações externas usarão somente contagens e categorias agregadas.

5. **Manter o contexto anterior recuperável.** Antes de qualquer escrita real, um backup cifrado e autenticado deverá ser persistido fora do repositório, reaberto e verificado; keyring e configuração anterior serão preservados separadamente no armazenamento aprovado. A recuperação restaura o conjunto e contexto anteriores sem recriar IDs. Falha em verificar backup ou recovery bloqueia a operação.

6. **Separar a operação de produção das mudanças funcionais.** Qualquer migração real exigirá inventário atual, fingerprint, serviços/portas, impacto, janela, backup, recovery e aprovação humana específica. Consumidores próprios serão pausados graciosamente conforme esse plano. A busca facial mantém sua flag atual; o gate `MERCADOPAGO_ALLOW_LIVE_PAYMENTS` permanece fechado; a change APP_ENV só pode prosseguir depois de uma nova coleta provar ausência de dados ligados à origem e passar seus demais gates.

7. **Tratar dados inelegíveis fora desta operação.** Registros expirados, revogados, sem autorização ou de origem desconhecida não serão migrados nem excluídos aqui. Permanecem bloqueadores até decisão e fluxo próprios, usando a política de retenção vigente; não serão convertidos em autorização implícita para produção.

## Bloqueio de integração com o gate APP_ENV

A change `transition-app-env-bound-integrations` atualmente bloqueia a transição quando qualquer contador biométrico é maior que zero. O coletor conta os objetos existentes por categoria, mas não classifica cada linha/arquivo como vinculado à origem, ao destino ou a um contexto desconhecido. Esta change preserva os registros ao re-cifrá-los; portanto, a contagem total continua positiva e o gate atual não consegue provar que os ciphertexts da origem foram eliminados. Não se deve interpretar a aprovação deste procedimento biométrico como autorização para ignorar esse gate.

Antes de implementar a task 3.2 ou declarar a transição APP_ENV pronta, as duas changes precisam de um contrato compatível. A opção recomendada para revisão é inventariar contagens por contexto ambiental usando metadados de envelope/registro versionados cuja associação ao ciphertext seja verificável, mantendo ausentes, inconsistentes ou desconhecidos como bloqueadores. A revisão deverá definir como a prova é autenticada sem abrir plaintexts, cobrir linhas PostgreSQL e arquivos `.reference`, validar adulteração/ausência em testes e atualizar o coletor/contrato da change APP_ENV em uma alteração própria e revisável. Um marcador de texto não autenticado, fixture sintética ou recibo não vinculado ao conjunto atual não é prova suficiente.

A ordem de corte também precisa ser aprovada: após preparar ciphertexts de destino, nenhum consumidor pode voltar a ler/escrever enquanto configuração, código e workers ainda esperarem o contexto de origem. O roteiro deve manter os consumidores faciais pausados até a configuração/versão de destino estar ativa e a verificação de consistência passar, mantendo a busca facial desativada. Não foi feita alteração na change APP_ENV nem no seu gate; este ponto é uma dependência para revisão, não uma decisão de arquitetura já aprovada.

## Protocolo candidato de recuperação multistore — para revisão

Este protocolo torna explícitos os pontos que precisam de revisão para a task 3.2. Ele **não está aprovado nem implementado**; em particular, a localização do journal e a prova de contexto exigem decisão antes do writer.

1. **Fechar a janela de mutação.** Revalidar inventário/fingerprint e elegibilidade; impedir novas escritas faciais e pausar, de forma graciosa, todos os leitores, workers, limpeza e retenção que possam tocar nos objetos. Confirmar zero jobs em execução. Qualquer divergência cancela antes de preparar destino.
2. **Tornar a recuperação durável antes de escrever.** Persistir e reabrir um journal cifrado e autenticado, separado do repositório, contendo o plano e snapshots de origem protegidos; manter também o backup autenticado verificado. IDs, vínculos e envelopes não podem aparecer em claro no journal, logs ou recibos. A durabilidade e o local aprovado do journal ainda são uma decisão aberta.
3. **Preparar sem substituir origem.** Gerar envelopes de destino para o conjunto aprovado, validar leitura com o contexto de destino e preparar arquivos `.reference` cifrados em staging no mesmo filesystem do destino final. Fazer flush/fsync de arquivos e diretório. Até esta fase ser verificada integralmente, banco e arquivos de origem permanecem intactos.
4. **Aplicar o banco em uma transação.** Revalidar fingerprints/concorrência; atualizar todas as linhas PostgreSQL elegíveis na mesma transação e registrar a fase no journal durável. Se a transação falhar, manter origem e descartar apenas staging comprovadamente pertencente ao lote.
5. **Promover arquivos com recuperação por objeto.** Com consumidores ainda pausados, substituir arquivos finais por `os.replace`, sincronizar o diretório e registrar cada avanço no journal. Como journal, banco e filesystem não compartilham uma transação, a recuperação após crash deverá comparar cada estado com snapshots autenticados de origem/destino: continuar somente quando o estado observado for exatamente conhecido; estado divergente ou ambíguo mantém a pausa e exige intervenção.
6. **Verificar antes do corte.** Conferir que toda linha e arquivo do lote está validamente legível no destino, que não restam objetos vinculados à origem e que contagens/fingerprints correspondem ao plano. Só então coordenar a ativação de código/configuração que usa o destino; retomar consumidores depois da nova verificação de saúde, mantendo a busca facial desligada. O gate APP_ENV precisa aceitar a prova de contexto aprovada no parágrafo anterior.
7. **Preservar recuperação e auditar.** Manter backup e journal até expirar a retenção aprovada e concluir revisão; não apagar origem, backup ou journal como parte implícita do commit. Registrar somente resultado agregado/allowlisted.

**Regra de recovery proposta:** antes do commit SQL, abortar preparação e conservar origem; depois do commit, rolar para frente apenas com todos os destinos e snapshots autenticados disponíveis, ou restaurar o lote inteiro a partir do journal/backup. Se não for possível provar exatamente uma dessas opções, manter consumidores pausados e parar sem sobrescrever dados. A política de escolha, o ponto de coordenação com a mudança de APP_ENV e a durabilidade do journal precisam de aprovação humana e testes de interrupção em PostgreSQL + filesystem antes de converter esta proposta em implementação.

### Alternatives considered

- **Mudar apenas o `APP_ENV` ou ignorar a contagem biométrica:** rejeitado porque os ciphertexts podem ficar ilegíveis e a change de transição exige bloqueio até uma prova específica.
- **Re-cifrar todos os objetos sem avaliar consentimento e origem:** rejeitado porque a presença de ciphertext não comprova finalidade, autorização para destino ou retenção vigente.
- **Excluir todo o conjunto para zerar o bloqueio:** rejeitado porque esta mudança não define autorização nem critérios para exclusão de cada objeto.
- **Migrar com commits independentes ou exportação em texto claro:** rejeitado porque poderia expor payloads ou deixar tenants/armazenamentos em contextos mistos.

## Risks / Trade-offs

- [Metadados não comprovam origem, consentimento ou finalidade] → manter os objetos inelegíveis e bloquear o corte até revisão específica.
- [Classes de dados distribuídas entre banco, arquivos e filas tornam rollback incompleto] → mapear todos os consumidores/armazenamentos antes do código e manter qualquer classe não recuperável fora da migração.
- [Ciphertext válido na origem falha no destino por chave ou AAD divergente] → validar contextos explicitamente com fixtures sintéticas e abortar antes do primeiro write real.
- [Exceções ou métricas expõem informação biométrica] → emitir somente códigos allowlisted, contagens agregadas e estados sanitizados; não incluir hashes de payload.
- [Pausa de consumidor facial afeta jobs] → derivar a lista de serviços/consumidores do inventário atual, pausar graciosamente e manter jobs sem perda durante a operação.
- [Uma migração aprovada é confundida com ativação facial ou de pagamentos] → preservar flags e gates e exigir suas próprias aprovações posteriores.

## Migration Plan

1. Mapear no código e no inventário autorizado todas as classes de objetos, armazenamentos, consumidores e metadados de consentimento/finalidade/retenção. Não abrir payloads nem inferir origem a partir de fixtures ou configurações versionadas.
2. Revisar critérios de elegibilidade e obter uma decisão humana sobre o conjunto e o destino. Se houver qualquer classe sem comprovação, deixar essa classe e a transição global bloqueadas.
3. Implementar e validar localmente somente com dados sintéticos: contextos explícitos, preservação de vínculos, isolamento por tenant, concorrência, falhas e recuperação.
4. Preparar, para eventual operação real, inventário sanitizado atual, fingerprint, backup cifrado verificável, serviços/portas, impacto, janela e rollback; submeter o plano específico para aprovação antes de mutação.
5. Apenas após essa aprovação, revalidar fingerprint/backup, pausar os consumidores próprios listados, migrar o conjunto elegível e verificar consistência, saúde e contagens agregadas. Retomar serviços somente após comprovar estado íntegro.
6. Reexecutar o inventário APP_ENV. A migração biométrica não executa a troca global de ambiente nem habilita pagamentos reais; ambas exigem seus próprios gates e procedimentos.

## Open Questions

- A coleta atual informa categorias agregadas, não a procedência, os metadados de consentimento/retenção nem todos os armazenamentos de cada categoria. Esses fatos deverão ser obtidos por inspeção e inventário sanitizados na aplicação desta change; até lá nenhum objeto é considerado elegível.
- Como provar, sem expor plaintext, a classificação ambiental de cada ciphertext preservado e fazer o gate APP_ENV distinguir objetos ainda vinculados à origem dos já vinculados ao destino? A decisão deverá abranger metadados autenticáveis para PostgreSQL e `.reference`, compatibilidade/versão do contrato do coletor e tratamento fail-closed de dados legados ou divergentes.
- Qual sequência de corte coordenada entre a re-cifragem, a versão/configuração que usa o contexto de destino e a retomada dos consumidores faciais impede leituras ou escritas com contexto misto? A resposta requer revisão das duas changes; até então não retomar consumidores após qualquer migração real.
