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
6. Rotação mestra mantém keyring antigo + novo durante recifragem explícita em transação. Utilitário dry-run padrão, apply explícito, sem plaintext nos argumentos/logs. Recuperação requer backup cifrado do banco e keyring de origem fora dele. Revogação pelo provedor pode invalidar versões antigas; a UI e runbook orientam reconciliar antes de revogar no provedor.

## Risks / Trade-offs

- [Perda do keyring] → credenciais irrecuperáveis; backup externo separado e ensaio sintético de restauração/rotação.
- [API comprometida] → a API precisa decifrar segredos para chamar o provedor; limitar material somente à API, nenhum endpoint de leitura, auditoria mínima e escopo autenticado.
- [Credencial antiga revogada na InfinitePay] → retenção local não restaura validade remota; reconciliar pagamentos antes de revogar externamente.
- [Rollback ao #260 após adesão à UI] → esse binário não lê o cofre; bloquear novas cobranças, manter schema/ciphertext e usar binário compatível para confirmar pendências. Não executar downgrade destrutivo.

## Migration Plan

Migration expansiva após `20261017_0084`: criar tabela e colunas nullable/default legado, sem reescrever segredos nem pagamentos existentes. Ensaiar PostgreSQL vazio/legado, FKs e recusa de downgrade com credenciais geridas. Publicação coordenada deverá integrar #260 antes deste PR, provisionar somente o keyring mestra na API, aplicar migration e subir API/web compatíveis. Workers não recebem keyring e não mudam. Workflow atual API/web proíbe migrations: registrar gate e não ampliar sua allowlist para contornar a aprovação. Um plano autorizado de migration coordenada será necessário, independente da preparação Python. Detalhes e SHAs em `release-plan.md` ao concluir.
