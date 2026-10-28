# Design

## Context

Ver `proposal.md` e `specs/deployment-operations/app-env-transition/spec.md`. O código atual vincula os envelopes do `IntegrationCipher` ao `APP_ENV` por AAD e exige igualdade entre `APP_ENV` e `INTEGRATION_SECRET_ENV`. O Compose injeta `APP_ENV` em cinco serviços de aplicação. WhatsApp, e-mail e configuração facial também validam o ambiente das credenciais. `FacialScope` inclui ambiente em AAD de embeddings e referências; esse dado é biométrico e está fora da autorização desta transição. Outros usos de ambiente controlam cookies, origens e comportamento de desenvolvimento e precisam ser inventariados, mas não migrados como credenciais.

## Goals / Non-Goals

- Construir inventário seguro e um caminho repetível para transicionar envelopes de integração sem alterar sua identidade de tenant ou credencial.
- Fazer a transição falhar fechada se houver consumidor, envelope, chave, configuração externa ou serviço ativo que não possa ser classificado.
- Preparar recuperação verificável e prova de execução local com dados sintéticos.
- Não mudar o comportamento de cobrança, liberar pagamentos reais, executar chamadas de cobrança, validar credenciais por efeitos externos ou alterar dados/serviços de produção nesta change.
- Não copiar credenciais entre ambientes nem reclassificar uma credencial externa somente porque seu rótulo diverge.

## Decisions

1. **Separar inventário de mutação.** Um modo somente-leitura gera categorias, contagens agregadas, versões, revisão do banco, serviços/portas e fingerprint sanitizado. Um modo de execução separado exige o fingerprint exato e uma autorização operacional revisável. O inventário não imprime valores brutos de ambiente, segredos, envelopes, IDs de tenants/contas nem caminhos de arquivos sensíveis.

2. **Re-cifrar envelopes do banco em transação única.** O executor valida todos os envelopes no contexto de origem antes de preparar os de destino. A escrita ocorre em uma transação PostgreSQL única, com bloqueio/checagem de concorrência e atualização somente dos campos cifrados inventariados. IDs, vínculos, estado de integração, snapshots e histórico financeiro não são reconstituídos. Erro de qualquer envelope aborta a transação inteira. Texto claro existe apenas em memória do processo e não é serializado em logs, temporários ou recibos.

3. **Usar contextos criptográficos explícitos, sem alterar o ambiente global do processo.** O código de transição deve criar contextos de cifra independentes para origem e destino a partir do keyring autorizado do processo. Não deve trocar `os.environ` enquanto a API ou workers estão executando. Se a configuração atual não puder fornecer e validar os dois contextos necessários, a operação falha antes de escrever; rotação/introdução de chaves fica fora do escopo sem plano separado.

4. **Tratar configurações externas como validações independentes.** WhatsApp, SMTP e configuração facial não têm envelope Mercado Pago que possa ser re-cifrado por esta operação. Cada classe recebe estado agregado: validada para o destino, mantida desligada, ou não classificada. A mudança de rótulo `*_CREDENTIAL_ENV` só pode ocorrer depois de confirmação documentada de que a credencial já pertence ao ambiente alvo; a ferramenta não copia nem revela os valores. Um consumidor não classificado bloqueia a troca global de ambiente.

5. **Bloquear dados biométricos cifrados.** `FacialScope` inclui `APP_ENV` no AAD de embeddings, referências e notificações. Esta mudança somente conta os objetos por categoria e ambiente, sem abrir payloads. Se houver qualquer objeto vinculado ao contexto de origem, ou se não for possível provar sua ausência, não se troca globalmente o ambiente; migração ou descarte requer change e autorização próprias. Isto também protege arquivos/filas faciais cujo contexto dependa da mesma cifra.

6. **Vincular a mutação à configuração e fingerprint aprovados.** A execução reconsulta o inventário imediatamente antes da mutação e aborta se o fingerprint, schema, conjunto de serviços, classificação de credenciais ou gate diferir. A operação de produção deve ocorrer em janela revisada, com serviços escritores/consumidores identificados e paralisados de forma graciosa conforme procedimento aprovado. Não há parada forçada nem alteração de recursos fora do projeto `markina-gallery`.

7. **Preparar recuperação antes do primeiro write.** O backup autenticado e cifrado inclui o contexto ambiental anterior e somente os metadados/envelopes inventariados. A keyring e as configurações externas permanecem em cópia segura separada; não são embutidas no arquivo de envelopes. O operador verifica previamente que a keyring original continuará disponível para recuperação. Um recibo registra fingerprint, contagens, checksums, revisão e resultado, nunca valores ou payloads. Se a configuração nova, re-cifragem, commit ou healthcheck falhar, o recovery restaura os envelopes do contexto anterior e o procedimento operacional restaura a configuração correspondente. O gate de pagamentos reais permanece fechado durante e após a transição; sua liberação pertence à change de lançamento, após novo inventário e aprovação do plano específico.

8. **Não emitir tráfego financeiro nem mensagens de teste.** Validação local usa keyrings, tenants e credenciais sintéticos. A verificação pós-transição em produção limita-se a configuração, descriptografia, isolamento, schema e saúde dos serviços. Não cria pedido, pagamento, estorno, mensagem, e-mail ou chamada externa com efeito financeiro/operacional.
9. **Coletar o inventário real por comando remoto explicitamente somente-leitura.** O `ForcedCommand` terá um comando de inventário APP_ENV próprio, permitido somente para o SHA atual de `main` e para o blob revisado do coletor. O workflow manual usa o ambiente protegido de preflight, captura somente o objeto sanitizado do contrato e apresenta os bloqueios mesmo quando não há fingerprint aprovável. A coleta lê apenas metadados whitelisted de containers/configuração, contagens de banco e arquivos biométricos; não imprime valores de ambiente, credenciais, envelopes, IDs ou caminhos, não chama provedores externos, não pausa serviços e não modifica banco, arquivos, containers ou configurações. Fonte ausente ou erro de leitura gera somente um envelope de coleta incompleta com bloqueio genérico e fingerprint nulo; divergência do SHA/blob rejeita o comando.

### Alternatives considered

- **Alterar somente `APP_ENV`:** rejeitado porque muda o AAD e pode tornar os envelopes atuais ilegíveis, além de divergir das configurações dos outros consumidores.
- **Rotular todos os provedores como produção automaticamente:** rejeitado porque o nome do ambiente não prova a origem ou validade das credenciais externas.
- **Descriptografar e re-cifrar linha a linha com commits independentes:** rejeitado porque falha parcial deixaria tenants em contextos incompatíveis.
- **Migrar segredos via exportação temporária ou arquivo claro:** rejeitado por ampliar exposição e contrariar o modelo de segredos do repositório.

## Risks / Trade-offs

- [Uma categoria de segredo ou ciphertext não previsto ficar fora do inventário] → enumerar usos de `APP_ENV` e chaves de credenciais no código, Compose e runtime; consumidor/dado não classificado bloqueia fingerprint aprovável.
- [O helper de contrato não existir na versão de aplicação ativa] → o coletor obtém o módulo puro da revisão imutável de `main`, confere o blob Git esperado e executa a validação em memória; qualquer divergência aborta sem fallback ou saída parcial.
- [Dados biométricos cifrados ficarem ilegíveis após a troca] → contabilizar sem abrir payload e bloquear a troca se qualquer registro/arquivo/linha de fila estiver ligado ao ambiente de origem; exigir procedimento aprovado separado.
- [Falha após atualização do banco e antes de reiniciar os serviços] → manter backup e configuração anterior disponíveis, registrar estado da operação e exigir recuperação verificada antes de reabrir tráfego.
- [Chave necessária ausente ou incompatível] → validar todas as chaves e envelopes em modo somente-leitura; abortar sem escrita, sem fallback de chave ou contexto.
- [Credencial externa de homologação ser confundida com produção] → exigir confirmação específica por classe/provedor e manter integração desativada enquanto não validada.
- [Interrupção operacional durante a troca] → inventariar consumidores reais, apresentar impacto/portas/janela e limitar qualquer parada aos serviços próprios aprovados.

## Migration Plan

1. Mapear usos de ambiente, credenciais e ciphertexts no código, configuração Compose e serviços ativos; criar inventário sanitizado em modo somente-leitura, incluindo bloqueio explícito para qualquer dado biométrico vinculado ao ambiente de origem.
2. Implementar e validar localmente o plano de re-cifragem somente dos envelopes Mercado Pago usando dados sintéticos; demonstrar atomicidade, idempotência operacional por fingerprint e recuperação.
3. Classificar integrações externas e todos os efeitos comportamentais de `APP_ENV`; nenhum binding ou segredo externo é copiado. Classificação desconhecida ou incompatível bloqueia a troca.
4. Preparar backup cifrado e executar ensaio de restauração local sem dados reais.
5. Gerar plano operacional de produção com estado observado atual, origem/destino em categorias sanitizadas, conjunto exato de serviços, portas, contagens, hashes/fingerprint, janela, gate fechado e recuperação. Submeter o plano para revisão humana antes de qualquer alteração remota.
6. Após aprovação específica do plano, repetir inventário e fingerprint; abortar se houver divergência ou dado biométrico, classificar as integrações externas, pausar os consumidores identificados graciosamente, aplicar a transição e verificar saúde/consistência.
7. Se qualquer verificação falhar, restaurar configuração e envelopes pelo mesmo backup e manter bloqueados os pagamentos reais até a consistência anterior ser comprovada.
8. Não abrir o gate nesta change. A change `enable-mercadopago-production` deverá executar seu preflight atualizado e obter sua aprovação operacional própria antes de qualquer habilitação geral.

## Open Questions

Não há decisão de arquitetura pendente para o mecanismo local. A origem efetiva, contagem de envelopes, serviços ativos e situação de cada provedor externo são fatos operacionais que devem ser obtidos pelo inventário sanitizado; qualquer categoria não suportada bloqueia a execução e exige revisão do plano, sem pressuposição.
