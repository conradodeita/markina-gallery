# Design

## Context

O evento `private_photos_ready` já carrega a identificação da galeria-mãe no contexto persistido tanto para pastas derivadas de upload legado quanto para pastas restritas. O aviso e a configuração de WhatsApp são renderizados no backend; a interface administrativa recebe do contrato de notificações as variáveis e a prévia. O sistema já tem resolução e validação de hostname canônico para links transacionais.

## Goals / Non-Goals

**Goals:**

- Incluir um link HTTPS confiável da galeria-mãe no texto WhatsApp de novas fotos privadas.
- Restringir a variável ao evento e canal apropriados e torná-la configurável na central administrativa.
- Preservar mensagens personalizadas, snapshots históricos, autenticação da galeria e independência de canais.

**Non-Goals:**

- Alterar o limiar ou a busca facial, a notificação push, o OTP ou a política de acesso às galerias.
- Enviar links com tokens, sessões, credenciais ou parâmetros que contornem a autenticação.
- Reenviar eventos ou notificações históricas.

## Decisions

- Resolver `{{link_galeria}}` durante a criação do snapshot WhatsApp, usando `parent_gallery_id` já persistido no evento e a função de hostname canônico do tenant. Não usar `Host`, `Origin`, caminho de retorno nem qualquer URL recebida do navegador.
- Construir somente `https://{hostname-canônico}/public-galleries/{uuid}` e validar o resultado: host canônico correspondente ao tenant, HTTPS, sem usuário/senha, porta explícita, query ou fragmento. A galeria pública continua a exigir o OTP normal.
- Adicionar a variável às variáveis extras de WhatsApp do contrato de `private_photos_ready`. A validação e a prévia administrativa devem usar uma URL de exemplo dessa galeria e continuar rejeitando a variável em outros eventos/canais. A interface atual já renderiza as variáveis recebidas pela API; alterar frontend apenas se os testes de contrato demonstrarem necessidade.
- Se o ID da galeria-mãe não resolver para uma galeria válida do tenant, ou se o hostname canônico não puder ser resolvido e validado, cancelar apenas a entrega WhatsApp antes de iniciar transporte, com motivo sanitizado. Não bloquear nem reescrever o canal push.
- Atualizar o texto armazenado por migração de dados somente se ele for exatamente o padrão anterior; incrementar a versão da configuração conforme o modelo atual. Templates personalizados ficam intactos. A renderização persiste no snapshot de novos eventos, sem tocar em mensagens/outboxes existentes.
- Cobrir a URL e o isolamento de canal com testes de contrato/backend, incluindo ausência de origem, host inválido, host injetado e template customizado. Testar a migração com os valores padrão e personalizado.

## Risks / Trade-offs

- Tenants sem hostname canônico utilizável não poderão enviar este aviso por WhatsApp até que a configuração de domínio seja corrigida; cancelar a entrega evita expor links incorretos ou inseguros.
- Como a mensagem inclui um endereço de acesso público, o link não pode funcionar como autorização. A validação deve confirmar que o caminho é o da galeria-mãe e manter o fluxo OTP existente.
- A migração precisa fazer comparação exata do texto anterior para não sobrescrever personalizações, inclusive diferenças de pontuação ou espaços.
