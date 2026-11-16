# Gate posterior de publicação do endereço

## O que esta change entrega

Escolha e reserva autenticadas, exclusividade no banco e visualização do estado. A reserva ocupa canonical_host no namespace único e marca canonical_host_status=reserved. Isso não publica DNS, não cria certificado e não habilita acesso de clientes nesse host. O fotógrafo mantém a conta ativa e os gates anteriores de dados/termos/créditos/PIX/WhatsApp.

## Antes de promover para ready

1. Especificar a operação de provisionamento/ativação em change própria: autorização de operador, idempotência, estado verificável por host, auditoria e compensação. Não há endpoint self-service de promoção/renomeação nesta entrega. Não promover por SQL manual para contornar o gate.
2. Confirmar Cloudflare ativa, DNSSEC reconciliado, estratégia curinga versus registros individuais e armazenamento seguro de eventual token com escopo mínimo por zona. Manter markina/raiz e seus registros, sem misturar proxy/cache no corte.
3. Apresentar inventário de serviços/portas/hosts, SHA/schema/imagens saudáveis anteriores, backup/restore comprovado e plano sem interrupção para autorização específica. Nenhuma porta nova, parada ou mudança de recurso vizinho é inferida da aprovação do desenvolvimento local.
4. Validar emissão/renovação TLS do hostname, roteamento pelo proxy com Host validado e autoridade no banco. Hosts desconhecidos/reserved/inativos devem falhar fechados, sem fallback para o proprietário. Não confiar em X-Forwarded-Host recebido do cliente.
5. Garantir API e todos os workers consumidores de tenant_hosts atualizados para a mesma política antes de aceitar reservas no ambiente publicado. Código antigo ignora o estado novo; não autorizar rollout misto enquanto houver esse risco. Migration aditiva não prova compatibilidade funcional de runtime antigo.
6. Demonstrar login/OTP e sessões host-only, autorização A/B, links de galeria/compra e notificações, incluindo replay de cookie/challenge no host errado. Não compartilhar cookie no domínio pai nem transportar tokens/sessão por URL para facilitar o redirecionamento.
7. Somente a operação autorizada e validada poderá promover reserved para ready; a UI então oferece abertura manual. Não declarar pronto apenas porque DNS resolve, um certificado existe ou uma conta está ativa.

## Recuperação e preservação

Não liberar/reciclar nome de tenant suspenso nem reatribuir a outro fotógrafo. Não há edição de endereço neste escopo. Reversão da migration 0105 recusa estados persistidos para impedir remoção silenciosa da proteção reserved; usar versão/schema compatíveis e plano específico. Preservar dados, créditos, pagamentos em reconciliação, fotos, filas e o funcionamento do proprietário.

## Limites da prova local

PostgreSQL, concorrência HTTP/DB, build e Chrome desktop/mobile comprovam a reserva e sua interface. Caixa de e-mail, contas, crédito e WhatsApp da demonstração são sintéticos. Não houve prova de curinga/HTTPS por tenant, transporte real, envio de e-mail com remetente do fotógrafo nem publicação de backend SaaS no Oracle. Termos de teste permanecem sem validade de contratação.
