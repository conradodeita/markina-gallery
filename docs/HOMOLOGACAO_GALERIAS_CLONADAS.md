# Homologação — galerias privadas clonadas

## Escopo

Validar somente dados sintéticos: duas responsáveis, um acervo-fonte, duas galerias privadas clonadas e JPEGs de demonstração sem pessoas reais.

## Inventário e impacto zero

- Projeto autorizado: `markina-gallery` em `/opt/markina-gallery`.
- Comando permitido: `docker compose -p markina-gallery -f docker/docker-compose.yml`.
- Não alterar containers, redes, volumes, proxy, firewall, DNS, certificados ou arquivos de qualquer outro projeto.
- Antes do deploy, registrar versões dos containers Markina, portas publicadas e healthchecks; interromper caso algum recurso externo ao projeto apareça no inventário.

## Pré-requisitos técnicos

- Aplicar as migrations pelo container/API do próprio projeto antes de iniciar a validação. A migration `20260826_0004` é aditiva e inclui `auth_challenge.parent_gallery_id`, necessário também para a autenticação administrativa.
- Confirmar a revisão atual e fazer backup lógico do banco Markina antes da atualização. Não usar banco, volume ou backup de outro projeto.

## Roteiro manual

1. Criar uma cliente sintética, acervo-fonte sintético e galeria privada inicial.
2. Clonar a galeria para uma segunda cliente sintética e confirmar que as fotos são referências do mesmo acervo.
3. Em sessões separadas, selecionar fotos diferentes e bloquear somente a segunda galeria.
4. Confirmar que o link do acervo-fonte com OTP registra a cliente, mas não expõe grade coletiva.
5. Conferir a ficha administrativa, prévia sem marca d'água administrativa e exportações TXT/CSV.
6. Trocar o telefone de uma cliente com OTP e confirmar histórico; confirmar que o número antigo não autentica.
7. Confirmar estados `nova`, `visualizada mas não comprada` e `já comprada` no portal da cliente.

## Critérios de aprovação

- Nenhuma sessão de cliente acessa galeria de outra responsável.
- Nenhum acervo-fonte é listado ou entregue ao cliente.
- Nenhuma operação toca serviços fora de `markina-gallery`.
- Healthchecks da API e web permanecem verdes.

## Rollback

Se houver falha, interromper a atualização somente do projeto Markina e restaurar a imagem/tag anterior registrada no inventário. A migration é aditiva; não executar exclusão manual de dados nem `docker compose down` sem o prefixo e arquivo acima.

## Registro de execução

- Preparação local: concluída em 2026-08-26, com banco SQLite local migrado e autenticação administrativa validada.
- Homologação remota: pendente de aprovação explícita e de inventário de impacto zero no servidor.
