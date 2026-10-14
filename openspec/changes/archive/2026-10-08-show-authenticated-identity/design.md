## Contexto

O endpoint `/auth/destination` já valida a sessão, mas serve ao roteamento e tem consumidores que esperam somente o destino. A identificação visual deve ter contrato próprio para não acoplar a navegação à apresentação.

## Decisão

Adicionar `GET /auth/identity`, que deriva o papel e o sujeito do cookie validado por `current_session`. Para fotógrafo, retornar o e-mail da conta administrativa da própria sessão. Para cliente, retornar o telefone E.164 ativo e verificado associado à própria identidade, com fallback ao telefone canônico do cadastro quando não houver registro em `client_phone`.

Um componente client-side comum consulta o endpoint com `cache: no-store` e mostra `Logado como: [identidade]` nos cabeçalhos `/admin`, `/library` e `/gallery`. Respostas ausentes ou falhas não exibem identidade inventada nem impedem o uso da área.

## Segurança e privacidade

O endpoint não aceita identificador de usuário como parâmetro e não é público. Cada resposta contém somente a identidade correspondente ao cookie autenticado, sem dados de perfil adicionais. A tela não persiste esses dados no navegador.

## Riscos

- O identificador pode não aparecer momentaneamente enquanto a consulta carrega ou se a API estiver indisponível.
- O telefone é apresentado em E.164 para identificar sem ambiguidade o número verificado.
