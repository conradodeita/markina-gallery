# Associação segura de canais por fotógrafo

Contrato local da task 5.2. Não representa configuração remota, pareamento, envio ou autorização para provisionar outro fotógrafo.

## Configuração de servidor

`WHATSAPP_TENANT_BINDINGS` é JSON com UUID canônico da conta como chave e alias único como valor. Alias permite somente `[A-Z][A-Z0-9_]{0,31}`. Nenhuma API aceita UUID/alias de frontend para selecionar o canal. Exemplos no pacote operacional devem usar os UUIDs inventariados, sem copiar segredos para Git ou este documento.

Para cada alias, configuração externa segura fornece `WHATSAPP_BINDING_<ALIAS>_PROVIDER` (`sandbox` ou `evolution`) e `CREDENTIAL_ENV` igual ao `APP_ENV`. Evolution exige `API_URL`, `API_KEY`, `INSTANCE`, `WEBHOOK_URL`, `WEBHOOK_SECRET`; `TIMEOUT_SECONDS` é opcional, padrão 10 e limite 1–30. `PHOTOGRAPHER_PHONE_E164` é opcional para destinatário sintético do sandbox. Segredos ficam exclusivamente no servidor; o objeto de binding não os imprime e o payload administrativo contém somente provider, ambiente, estado, horários e telefones mascarados da própria conta.

O estado operacional de canal é próprio por conta/ambiente. Evolution exige telefone esperado próprio e identidade conectada compatível para estar pronto. O parâmetro técnico brasileiro de JID legado permanece. Instância no mesmo endpoint, alias ou segredo compartilhado entre contas é recusado. Um binding incompleto de B não invalida configuração independente válida de A. Sandbox também exige associação explícita em instalação multitenant e nunca abre rede.

## Preservação do canal existente

Entrega Compose preparada localmente em 8.2b: somente `api`, `worker` e `face-search-worker` leem arquivo opcional raw `docker/.env.whatsapp-bindings`, ou caminho técnico `WHATSAPP_BINDINGS_ENV_FILE`. Exige Compose >= 2.30; homologação inventariada usa 2.35.1. Arquivo ausente conserva ambiente legado. Arquivo real é ignorado pelo Git, restrito 0600 e persiste entre deploys; não será criado/modificado sem autorização. Conter somente `WHATSAPP_TENANT_BINDINGS` e chaves `WHATSAPP_BINDING_<ALIAS>_*`; não colocar credenciais globais, banco, flags ou outras configurações nele. Valores raw sem aspas adicionais de dotenv; caracteres `$`, espaços e `#` não são interpolados. A saída canonical de `docker compose config` pode escapar `$` como `$$`: não copiar essa saída para sobrescrever o arquivo nem imprimi-la com segredos reais. Testes resolvem somente fixtures sintéticas e não criam containers.

Variáveis globais legadas continuam permitidas apenas com uma única conta ativa demonstrável e igual ao alvo. Com duas contas, ausência de associação explícita impede envio; não há escolha por primeira conta nem fallback para configurações globais. Antes de provisionar B, o pacote operacional deverá mapear A para sua instância/credenciais atuais e verificar identidade/ambiente/health, preservando os valores existentes. O modo de injetar esses valores nos containers será revisado no pacote e executado somente com autorização operacional. Esta implementação não modifica `.env`, Docker de homologação ou credenciais reais, nem cria instâncias/volumes automaticamente.

## Execução e recebimento

Outbox/claim carregam owner durável. Cada consulta do canal, pareamento, envio ou reconciliação confere conta ativa e associação atual. A idempotência externa ganha prefixo da conta; chaves persistidas e envelopes/AAD OTP e faciais existentes permanecem inalterados. Origem, recurso, desafio atual, destinatário, sessão/push e geração são conferidos antes do efeito. Reenvio sem binding é recusado antes de invalidar código/entrega anterior. Conta suspensa não é consumida pelas filas; suspensão durante consulta do canal restaura trabalho anterior ao efeito. Resultado externo ambíguo não gera reenvio automático.

Webhook tem corpo limitado a 64 KiB. Instância registrada e segredo correspondente demonstram owner; UUID do payload não autoriza nada. ID externo e fingerprint são pesquisados somente nessa conta, inclusive quando repetidos em outra. Mensagem/corpo do webhook e credenciais nunca entram em log ou relatório.

SMTP permanece técnico compartilhado: origem é token/administrador demonstrável e destinatário coincide com fingerprint do envelope autenticado. Mudança de endereço ou token consumido impede entrega obsoleta. A permissão técnica não abre comércio de outra conta.

## Validação e fronteira operacional

Testes em `backend/tests/test_tenant_notification_transport.py` usam PostgreSQL descartável, telefones/nomes/envelopes sintéticos, adaptadores sem rede e configuração apenas em memória do processo. Evidências e falhas corrigidas estão em `validation.md`. Gates globais de ativação continuam até a prontidão 7.2; estes testes não são as jornadas do ensaio 7.3 nem aceite remoto.
