# Matriz local de consumidores de ambiente

Escopo estático revisado em 28/10/2026 no candidato `2d42a7b5`. Esta matriz não substitui inventário do host. Não contém valores de variáveis, credenciais, payloads, identificadores de tenant, conta ou caminhos operacionais.

## Serviços Compose com `APP_ENV`

| Serviço | Uso observado |
|---|---|
| `api` | API, origens, autenticação, WhatsApp, e-mail, Mercado Pago, configuração facial |
| `worker` | filas e entrega, incluindo OTP/WhatsApp |
| `face-search-worker` | workers faciais e scopes criptográficos |
| `face-index-worker` | indexação facial e scopes criptográficos |
| `face-maintenance-worker` | manutenção e retenção facial |

Os nomes acima vêm de `docker/docker-compose.yml`. A lista real de containers, imagens, saúde e portas continua sujeita ao preflight de produção aprovado.

## Dados cifrados que dependem do ambiente

| Classe | Escopo criptográfico | Tratamento nesta change |
|---|---|---|
| Credenciais Mercado Pago | `IntegrationCipher` usa `APP_ENV` no AAD; cada envelope também é associado ao tenant e ao ID da conta. `MercadoPagoAccount` armazena os envelopes do token e do segredo de webhook. | Elegível para re-cifragem transacional depois de inventário, backup e aprovação do plano. |
| Dados faciais | `FacialScope` usa ambiente, galeria/objeto, finalidade e versões no AAD. Inclui embeddings, referências/localizadores e notificações; referências temporárias também usam o scope. | Fora do escopo autorizado. Contagem agregada; qualquer objeto de origem ou ausência de prova de zero bloqueia a troca. Não abrir, re-cifrar ou apagar payloads. |

## Integrações e efeitos ambientais

| Consumidor | Vinculação observada | Risco se `APP_ENV` mudar | Regra |
|---|---|---|---|
| WhatsApp | Credencial de ambiente em configuração de servidor/binding; `WhatsAppChannelSettings` é selecionado pelo ambiente. | Binding e preferências podem deixar de ser selecionados; a configuração também pode causar envio externo. | Não copiar valores; validar classe/provedor e manter bloqueado se não classificado. |
| SMTP | Credencial ambiental comparada com `APP_ENV`. | Entregas falham ou selecionam configuração incompatível. | Não copiar valores; exigir confirmação do provedor e bloquear enquanto pendente. |
| Facial | `FACIAL_CREDENTIAL_ENV`, keyring próprio e ambiente no AAD biométrico. | Configuração falha fechada e ciphertext existente pode ficar ilegível. | Não alterar; qualquer dependência da origem bloqueia esta transição. |
| Mercado Pago | Gate de teste/live, conta associada e `IntegrationCipher`. | Credenciais deixam de descriptografar sem re-cifragem; habilitar gate teria efeito financeiro. | Re-cifrar apenas envelopes elegíveis; manter gate live fechado. |
| Cookies, origens e proteções de desenvolvimento | `APP_ENV` define `Secure`, fallback local, política de origem e ausência/presença de configurações obrigatórias. | A mudança ativa comportamento de produção e exige valores de produção já provisionados. | Validar todas as categorias e consumidores, não tratar como simples rótulo. |
| OTP WhatsApp e push | Chaves próprias; contexto OTP usa chave de idempotência e push usa Fernet. `APP_ENV` controla somente atributo de cookie push, não o AAD desses payloads. | Não exige re-cifragem por ambiente; as chaves existentes continuam necessárias. | Preservar chaves e dados; confirmar disponibilidade e política de cookie. |

## Cobertura de código

Os caminhos atualmente detectados e as contagens de linhas com marcadores ambientais/criptográficos estão protegidos pelo teste `backend/tests/test_app_env_transition_inventory.py`. Uma referência em novo arquivo, alteração de cobertura ou mudança do conjunto Compose exige revisar esta matriz e atualizar o teste.

`backend/app/environment_transition_inventory.py` contém o contrato sanitizado e os classificadores; ele não lê o ambiente do processo nem material secreto. `classify_external_integrations()` deriva os estados de WhatsApp, SMTP e facial apenas de flags agregadas sobre habilitação, compatibilidade ambiental e validação do provedor. As três flags precisam ser verdadeiras para classificar uma integração habilitada como `validado_destino`; ausência ou divergência gera `nao_classificado`, que impede fingerprint. Integrações desabilitadas são classificadas `desativado`. Suas ocorrências de marcadores são nomes usados em documentação do contrato, e o teste as acompanha explicitamente.

O coletor operacional apresenta os vínculos `WhatsAppChannelSettings` somente como contagens agregadas de categoria ambiental e estado; o fingerprint abrange esses vínculos e os hashes das variáveis de runtime de cada serviço. Antes de emitir um inventário, compara a keyring de integração com o que API e worker carregam, confirma o binding `INTEGRATION_SECRET_ENV` com o `APP_ENV`, compara configurações externas compartilhadas entre API/worker e confirma o gate live fechado em ambos. Valores e caminhos usados nessas comparações permanecem em memória e não entram no recibo.

## Evidência operacional disponível

O run read-only `40715456515` passou a validação de conjunto de serviços, saúde e portas; depois parou fechado na categoria sanitizada `ambiente_divergente:outro_ambiente_conhecido`. Não emitiu fingerprint completo nem verificou matriz de tenants, schema ou HTTPS neste fluxo. Portanto esta matriz não declara o conjunto de produção atual nem a contagem real de credenciais/dados faciais.
