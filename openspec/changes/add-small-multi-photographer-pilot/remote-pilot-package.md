# Preparação operacional do piloto — ainda sem autorização de execução

## Estado e destino

PR #134 publicado, schema 0071 e operador atual concedido/verificados. Novo patch local reúne correção de legibilidade e entrega Compose dos bindings já implementados. Exige PR/checks e aprovação específica antes de integração que dispara deploy. Não há migration nova ou alteração de recursos vizinhos.

Destino: `/opt/markina-gallery`, Oracle `132.145.193.169`, projeto `markina-gallery`; subdomínio `https://markina-homolog.duckdns.org`, entrada própria `127.0.0.1:8080`. Inventário após publicação: 13 serviços próprios saudáveis; DB/Redis/três serviços Evolution e Firefly/NPM/Portainer preservados. Atualizar inventário imediatamente antes de qualquer operação. Portas vizinhas 3000, 80/81/443 e 8000/9443 permanecem protegidas; sem novas portas, redes, volumes, certificados ou containers para os bindings.

Conta A existente: `1531dbaa-215c-4583-b1f0-77d185ad7f07`. Admin/operador existente: `f4606e36-a74c-4b31-b123-9ee2059412e5`, preservado. Inventário 23:14:05Z: uma conta ativa e nenhuma associação explícita. O proprietário disponibilizou identidade, e-mail ainda não cadastrado e segundo telefone corrigido para B. Esses dados ficam fora do Git. Ainda faltam aprovação operacional e fornecimento seguro das credenciais da nova conta; não pedir senha/TOTP neste chat.

Referência local dos contatos fornecidos: `C:/codex-data/test-runs/pilot-b-contact-20261001.json`, sem senha/TOTP e fora do repositório. Não copiar conteúdo para PR/docs/logs. Arquivo identifica intenção de preparação, não autorização de execução.

## Ordem obrigatória e impacto

1. Aprovar/publicar head exato do patch com CI verde e backup novo conferido. Preservar schema, legado, flags e serviços protegidos; conferir monitor usando sessão humana válida. Não criar B neste deploy.
2. Com aprovação específica de configuração, criar arquivo restrito `docker/.env.whatsapp-bindings` somente no servidor. Associar A ao alias `LEGACY_A`, mantendo provider/ambiente/endpoint/instância/credenciais e estado atuais. Conservar valores legados existentes. Não copiar segredos para logs, Git ou documento; não imprimir Compose resolvido real. Recriar somente os consumidores próprios autorizados `api`, `worker`, `face-search-worker`, com interrupção breve desses serviços; conferir saúde, associação/identidade de A e preservação dos vizinhos antes de seguir. Nenhuma mensagem de teste sem aceite próprio.
3. Definir e aprovar UUID novo explícito para B, alias `PILOT_B` e instância lógica própria no Evolution já existente, verificando ausência de conflito. Nome proposto `pyp-pilot-b-20261001`; não reutilizar A, webhook secret ou estado de pareamento. Isso cria recurso lógico somente após aceite; não aumenta infraestrutura. O binding de A permanece completo antes de a instalação passar a duas contas.
4. Fornecer e-mail/senha/TOTP de B pelo processo seguro autorizado, sem argumentos de shell, Git, logs ou envio automático. Executar CLI offline com UUID aprovado em dry-run; revisar flags, aplicar com confirmação exata e repetir para comprovar idempotência. Não copiar PIX, branding, templates ou permissão de operador.
5. Adicionar binding completo independente de B e configurar telefone esperado fornecido pelo proprietário. Pareamento exige participação humana no WhatsApp de B e autorização do recurso lógico/segredos; conferir identidade/ambiente prontos sem alterar A. Falha/incompletude de B não autoriza fallback nem reinicialização do canal A.
6. Somente depois dessas conferências, selecionar três destinatários autorizados por fotógrafo, repetindo um entre contas, e aprovar os envios OTP por execução. Até 12 JPEGs sintéticos sem pessoas; sem biometria ou pagamento real. Seguir roteiro `pilot-plan.md`, no máximo seis jornadas concorrentes e diagnóstico antes/durante/depois; registrar relatórios sanitizados e confirmar cópia integral. Não apresentar evidência local como prova remota.

## Limites e reversão

Se A não estiver preservado/pronto, não criar B. Antes da criação de B, é possível retirar somente a nova configuração autorizada e retomar o canal legado com uma conta, mediante conferência. Depois de B ativo, não remover o binding de A nem retornar automaticamente ao fallback de conta única. Falha exige correção controlada; não apagar conta/dados, fazer downgrade, restaurar banco ou limpar recursos sem aprovação própria. Ausência de credencial, pareamento ou destinatário bloqueia a operação correspondente, sem justificar bypass.

Nenhuma etapa de criação/configuração/env/pareamento/envio desta preparação foi executada. Informar dados de B não concede essas autorizações. Revisão humana da change, sync e arquivo continuam posteriores ao ensaio validado.
