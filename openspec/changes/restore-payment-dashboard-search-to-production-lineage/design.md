# Design

## Contexto

O recurso aprovado está consolidado no commit `92366f56eed0840443476a977e71664703c98a97` de `develop`. A produção usa `main`, que avançou por uma integração independente da galeria progressiva baseada no commit `aa7119c`. As duas linhas divergiram; o release web de #179 atualizou a interface a partir de `main`, onde o filtro não existia. O endpoint atualmente ativo ainda contém a versão de busca publicada anteriormente, portanto a regressão visível é inicialmente de frontend; a árvore fonte de `main` também precisa recuperar o contrato backend antes de futuros releases.

## Decisões

1. Portar somente as mudanças de produto e testes de `92366f5` nos arquivos de pagamentos. Não fazer merge geral de `develop`, que introduziria mudanças fora do escopo e conflitos com a galeria publicada.
2. Adaptar o port ao código atual de `main` preservando `deferGridImages` e outras alterações do PR #179; não substituir arquivos completos pela versão antiga.
3. Criar esta change antes do port de código e executar testes de busca backend, sugestões/layout frontend, lint, typecheck, build e validação OpenSpec conforme viabilidade local.
4. Enviar o resultado para revisão por PR em `main`. A aprovação já dada cobre preparar a correção, mas não cobre merge ou publicação. Qualquer deploy dependerá de inventário atualizado, plano de impacto e autorização específica.
5. Manter #177 independente: ele altera manifest/lockfile e OpenSpec de dependências, está aberto para `develop` e não é necessário para restaurar esta função.

## Segurança e dados

O filtro permanece restrito ao painel administrativo autenticado. A resposta da API não deve expor telefones. A alteração não acessa nem modifica dados reais, segredos, containers ou configurações do servidor.
