# Design

## Decisão

Adicionar ao monitor de terceiros um extrator/validador estreito para a declaração de imagem do serviço `nginx` no bloco `services` do Compose. O validador não interpreta o manifesto inteiro; a validação estrutural completa continua sendo responsabilidade de `docker compose config` nos testes de validação do candidato.

A referência deve apontar exatamente para `nginx`, declarar uma tag numérica (`X.Y` ou `X.Y.Z`) terminada em `-alpine`, e pode incluir digest somente se este passar pelo validador existente `parse_image_reference`. Tags móveis como `latest`, imagens não oficiais, variantes fora de Alpine e versões malformadas são rejeitadas. O teste de integração também confirma a linha Nginx no inventário e o monitoramento `docker-compose` configurado para `/docker`.

## Testes

- Aceitar tags `1.27-alpine` e `1.31-alpine` para demonstrar independência da versão.
- Rejeitar ausência do serviço/imagem, referência sem tag explícita, repositório diferente, tag não numérica, variante que não seja Alpine, e digest inválido.
- Rodar o teste do relatório semanal e conferir o Compose candidato de #248 com o CLI Docker Compose.
- Quando Docker estiver disponível, executar a imagem `nginx:1.31-alpine` isolada com a configuração versionada e `nginx -t`, e testes locais de roteamento com upstream sintético.

## Risco e isolamento

A mudança afeta apenas código de validação e testes. A validação de contêiner usa configuração local read-only, sem volumes, rede, dados ou serviços da aplicação/produção. Se o daemon Docker não estiver disponível, registrar esse bloqueio e executar as validações estáticas e de CI que forem possíveis.
