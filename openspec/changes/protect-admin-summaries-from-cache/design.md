# Design

## Context

As rotas `GET /admin/security/summary` e `GET /admin/validation-summary` já exigem sessão administrativa. A segunda inclui nomes e horários de atividade de clientes; a primeira informa estado dos fatores de segurança. As respostas atuais não definem política explícita de cache. Ver requisitos em `specs/auth/spec.md` e `specs/gallery-sales/operational-gallery-interface/spec.md`.

## Goals / Non-Goals

**Goals:**

- Restringir as duas respostas ao cliente autenticado e impedir armazenamento por caches HTTP.
- Manter autenticação, payload, consultas, isolamento por tenant e comportamento visual sem alterações.

**Non-Goals:**

- Alterar outros endpoints administrativos, criar política global de cache ou mudar o cache interno do React.
- Remover dados da tela após visualização, logout ou encerramento da sessão por mecanismos além dos já existentes.

## Decisions

- Definir `Cache-Control: private, no-store` diretamente na resposta de cada endpoint. A decisão torna o contrato explícito no servidor e cobre navegador e intermediários sem depender de como o frontend faz `fetch`.
- Verificar o cabeçalho em testes de contrato autenticados junto aos campos existentes. Não incluir um cenário de autorização duplicado, pois os testes atuais já cobrem a sessão e o escopo dessas rotas.
- Não usar middleware global: outras rotas têm contratos e necessidades de cache diferentes. Não confiar somente em `fetch(..., { cache: "no-store" })`, pois isso controla a requisição do frontend, mas não substitui a política de resposta HTTP.

## Risks / Trade-offs

- [Consultas repetidas deixam de usar cache do navegador] → Os resumos são pequenos e já são carregados no acesso ao painel; a leitura atualizada e a minimização de dados têm prioridade.
- [Um endpoint futuro pode adicionar informação pessoal e esquecer o cabeçalho] → Manter a exigência próxima aos contratos das duas superfícies e os testes de regressão junto às rotas.
