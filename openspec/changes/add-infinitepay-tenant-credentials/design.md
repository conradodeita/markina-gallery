# Design

## Context

Base isolada: PR #260, SHA `0959c64`, sem merge. Reutilizar endpoints `/admin/settings/infinitepay`, autenticação contextual, senha + OTP de `AdminSecurityChallenge`, rate limit, CSRF e lock de `Tenant`. Não existe cofre gerido pelo produto. `cryptography` e AEAD já são dependências do backend; evitar serviço adicional.

## Goals / Non-Goals

**Goals:** entrada de segredo no mesmo card; isolamento durável; referências por compra; gestão operacional recuperável e teste A/B real no backend isolado.

**Non-Goals:** validação financeira automática, endpoint fictício de teste, assinatura de webhook não documentada, migração de pagamentos reais, mudança do PIX, configuração de segredo real ou publicação.

## Decisions

1. Tabela dedicada `infinitepay_credential`, versionada por UUID, ciphertext/nonce/key-id/ambiente e tenant. AES-256-GCM com AAD fixando finalidade, versão, ambiente, tenant e UUID do segredo. Keyring `INTEGRATION_SECRET_KEYS` (JSON key-id→base64 de 32 bytes), `INTEGRATION_SECRET_ACTIVE_KEY_ID` e `INTEGRATION_SECRET_ENV` vêm somente da configuração segura da API. Sem default criptográfico e sem reaproveitar chave facial/OTP. Tabela cifrada especializada atende à autorização explícita do pedido, sem plaintext em tabela comercial.
2. `InfinitePaySettings` ganha origem (`server_binding` legado ou `managed`) e referência atual; `ProviderPayment` ganha referência imutável opcional. FKs compostas impedem vincular credencial de outro tenant. Compras legadas com referência nula continuam resolvendo somente o binding do PR #260. Configuração gerida nunca volta ao binding legado por ausência/falha ou desconexão.
3. Mesma ordem de locks: tenant → configuração/compra. Checkout congela credencial junto com handle/versionamento. Substituição conserva ciphertext antigo, pois callbacks usam a referência da compra; desconexão é recusada diante de qualquer estado não terminal e, quando permitida, apaga ciphertext de versões geridas. Desabilitar novos cartões não remove a chave e continua possível.
4. Entrada `SecretStr` write-only na requisição protegida. Antes do OTP, cifrar a chave com o keyring dedicado em envelope aleatório; somente esse envelope entra na proposta já cifrada do desafio. Resposta da proposta usa allowlist de campos não secretos. O código/senha e envelope expirado seguem o lifecycle existente. Confirmação aplica credencial e configuração na mesma transação e limpa o desafio. Erros de validação da rota são neutros e omitem `input`/body.
5. Campo secreto não controlado por estado React, sem storage/telemetria; apagar após envio e ao sair. Mesma UI, botões e padrão de confirmação, com proteção de abandono. Cadastro significa armazenado, validação remota indisponível; a documentação consultada do #260 não oferece endpoint seguro para validar uma API Key isolada. Nunca criar link ao salvar.
   A UI só aceita segredo com capacidade autenticada `credential_storage_available=true`. Flag ausente (API anterior) ou falsa impede entrada/substituição/envio; ações legadas sem segredo permanecem compatíveis. Publicar todas as instâncias da API antes da web e manter barreira de escritas durante troca/rollback, pois uma API antiga não conhece a sanitização do novo campo.
6. Rotação mestra mantém keyring antigo + novo durante recifragem explícita em transação. Utilitário dry-run padrão, apply explícito, sem plaintext nos argumentos/logs. Recuperação requer backup cifrado do banco e keyring de origem fora dele. Revogação pelo provedor pode invalidar versões antigas; a UI e runbook orientam reconciliar antes de revogar no provedor.
7. No CI integral `39540544153`, quatro testes delimitaram integração faltante com o catálogo de limpeza/reset: fixture operacional ainda em 0081 e cofre ausente de `TENANT_CONFIG` do reset proprietário. Classificar como R/K também nesse consumidor; preservar todas as versões do proprietário e manter exclusão dos outros tenants conforme política existente. Nenhum reset operacional é autorizado por esta alteração.
8. O mesmo CI registrou `qemu: uncaught target signal 4 (Illegal instruction)` no `npm ci` ARM64, antes do cancelamento pelo limite do job. Preservar a validação AMD64/ARM64 em matriz de runners nativos (`ubuntu-latest`, `ubuntu-24.04-arm`), sem emulação. Gate agregado continua obrigatório e `fail-fast=false` permite observar ambas as arquiteturas. GitHub confirma runners padrão gratuitos em repositório público; visibilidade PUBLIC confirmada. Não modificar dependências, Dockerfiles, limites de aprovação ou workflows de publicação/Python.

## Risks / Trade-offs

- [Perda do keyring] → credenciais irrecuperáveis; backup externo separado e ensaio sintético de restauração/rotação.
- [API comprometida] → a API precisa decifrar segredos para chamar o provedor; limitar material somente à API, nenhum endpoint de leitura, auditoria mínima e escopo autenticado.
- [Credencial antiga revogada na InfinitePay] → retenção local não restaura validade remota; reconciliar pagamentos antes de revogar externamente.
- [Rollback ao #260 após adesão à UI] → esse binário não lê o cofre; bloquear novas cobranças, manter schema/ciphertext e usar binário compatível para confirmar pendências. Não executar downgrade destrutivo.

## Migration Plan

Migration expansiva após `20261017_0084`: criar tabela e colunas nullable/default legado, sem reescrever segredos nem pagamentos existentes. Ensaiar PostgreSQL vazio/legado, FKs e recusa de downgrade com credenciais geridas. Publicação coordenada deverá integrar #260 antes deste PR, provisionar somente o keyring mestra na API, aplicar migration e subir API/web compatíveis. Workers não recebem keyring e não mudam. Workflow atual API/web proíbe migrations: registrar gate e não ampliar sua allowlist para contornar a aprovação. Um plano autorizado de migration coordenada será necessário, independente da preparação Python. Detalhes e SHAs em `release-plan.md` ao concluir.

## Integração com o checkout publicado em 21/10/2026

Main/produção `21b89c3` já contém o contrato de #260 e a reabertura manual de #263/#265; não repetir esses merges operacionais nem alterar compras recuperadas. Atualizar a branch existente por merge, sem rebase destrutivo/force push, preservando tanto os guards contra resposta tardia quanto a referência imutável de credencial. Reabertura não altera credencial da compra antiga e não cancela seu link remoto. Uma compra nova autorizada após recuperação usa a versão ativa; substituição continua possível, enquanto desconexão permanece bloqueada pelas pendências do contrato existente. Ensaiar essa interação com dados e transporte sintéticos.

A orientação do card não pode exigir desligamento global do PIX da conta InfinitePay nem afirmar que essa preferência controla links da API: o adaptador já envia `payment_methods_enabled=["credit_card"]` por link com API Key. Corrigir somente textos/declaração de preparo para esse contrato e para conferência do recebedor, mantendo senha/OTP, disponibilidade efetiva, PIX manual e ausência de chamada financeira ao salvar. Não habilitar pagamento automaticamente ou introduzir novo meio integrado nesta etapa.

Reutilizar o inventário e os recibos do release anterior como referência histórica datada do plano, com imagens/schema observados; uma nova publicação exige inventário aprovado e atual, backup/restore, mestre e migration 0085 próprios. Nenhuma nova operação Oracle é autorizada para esta retomada. O CI integrado deverá conservar os testes de recuperação PostgreSQL trazidos de main e os testes de cofre/migration e imagens nativas desta branch; nenhum gate pode ser removido para resolver conflitos.

Após o pedido de concluir o roadmap, integrar também o PR draft #266: piso local de100centavos antes de reservar e navegação no primeiro clique. Sua change e testes devem vir por merge de histórico, preservando o snapshot/legado do cofre, senha/OTP e recuperação publicada. O manifesto0084 de #266 continua descrevendo apenas o candidato API/web sem cofre: esta integração com0085 MUST continuar recusada pelo gate operacional. Não substituir pins pelos blobs do cofre nem converter uma recusa correta em aprovação de release. Repetir testes afetados no candidato único antes de enviar o mesmo PR#262 para revisão; CI técnico e autorização de publicação são evidências distintas.

### Política técnica de CI para candidato protegido

A asserção atual do teste de workflow confunde o runtime do release0084 com toda branch de desenvolvimento: exige que os arquivos do cofre sejam idênticos aos blobs do release anterior, impossibilitando validar a própria recusa correta. Corrigir somente esse teste de política, sem modificar verificador, classificador, manifests, wrappers, permissões ou workflow de publicação para admitir o cofre.

O teste SHALL comprovar positivamente, com o verificador real, o snapshot do commit ancestral que introduziu a versão exata do manifesto. O conteúdo desse manifesto SHALL ser idêntico ao utilizado pelo teste, e cada comparação de blob original SHALL permanecer sobre esse snapshot. Um manifesto novo que tente incluir cofre/migration no snapshot positivo SHALL falhar no verificador real. Separadamente, o teste SHALL executar o mesmo verificador contra HEAD: candidato API/web exato pode passar; candidato protegido SHALL ser identificado pelo classificador real e recusado pelo verificador. Falta de histórico, manifesto divergente, snapshot positivo inválido ou runtime app adulterado sem classificação protegida SHALL falhar o teste. Não usar mocks, skip ou listas de exceção para os arquivos do cofre.

Adicionar regressões Git reais de snapshot positivo, alteração documental, migration corretamente recusada, adulteração de blob, manifesto que tente aprovar migration e manifesto solto divergente. Executar essas regressões explicitamente no CI, preservando todos os checks anteriores. Sucesso técnico SHALL informar recusa de publicação do cofre e não `app_release_ready=true`.
