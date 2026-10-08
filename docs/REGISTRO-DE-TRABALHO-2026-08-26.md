# Registro de trabalho — 2026-08-26

## Homologação da autenticação

- A Markina Gallery foi implantada de forma isolada em `/opt/markina-gallery`, sem alteração, reinício ou remoção de recursos do ClearBudget.
- O ambiente usa PostgreSQL e Redis privados, migration Alembic aplicada, administrador inicial criado e segredos externos ao Git com permissões restritas.
- O nginx da Markina foi conectado somente à rede `npm-network`, com o alias privado `markina-homolog-nginx`; nenhum serviço foi conectado à rede do ClearBudget.
- Foi criado exclusivamente o host `markina-homolog.duckdns.org` no Nginx Proxy Manager, apontado para o alias privado, com certificado Let's Encrypt próprio e redirecionamento HTTP para HTTPS.
- Healthchecks, autenticação administrativa com senha/TOTP, fluxo de cliente com dados sintéticos e rollback restrito ao nginx da Markina foram aprovados.
- As credenciais iniciais foram guardadas pelo proprietário e o arquivo temporário correspondente foi removido do servidor.

## Planejamento das próximas funcionalidades

Foram criadas e validadas duas mudanças OpenSpec, sem implementação de código:

- `add-derived-client-galleries`: galerias privadas derivadas do acervo-mãe, seleção, favoritos, comentários privados, configurações por cliente e estatísticas de venda.
- `spike-private-facial-discovery`: avaliação isolada de segurança, privacidade, licença, precisão e desempenho ARM para busca facial privada.

A busca facial não será liberada a clientes até que o spike seja concluído e aprovado. O acervo coletivo continuará privado ao fotógrafo; galerias derivadas concedem ao cliente acesso apenas às fotos destinadas a ele.

## Implementação iniciada e limitação identificada

- A aplicação da mudança `add-derived-client-galleries` foi iniciada, com 0 de 9 tarefas concluídas. Nenhuma alteração de código dessa mudança foi finalizada nesta data.
- O login de administrador foi confirmado no ambiente de homologação, porém o frontend atual não possui a rota `/admin`. Após autenticar, o navegador recebe `404` nessa rota.
- Essa rota administrativa e a futura página de estatísticas fazem parte do trabalho pendente da mudança de galerias derivadas. O problema foi identificado para ser corrigido durante a implementação, sem mascarar o resultado da validação atual.

## Próximo passo

Retomar `add-derived-client-galleries` pela modelagem e migration aditiva, depois construir as APIs, a área administrativa e o portal do cliente. Nenhuma mudança deve seguir para produção sem revisão humana, testes e homologação próprios.
