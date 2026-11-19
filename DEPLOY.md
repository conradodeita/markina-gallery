# DEPLOY — Pick-your-Pic em produção

> Não existe ambiente operacional de homologação. Os alvos são desenvolvimento local, GitHub Actions e produção. Nenhum workflow publica a partir de `develop`.

## Ambientes

| Alvo | Uso | Dados e segredos |
|---|---|---|
| Desenvolvimento local | Implementação e ensaios locais | `docker/.env`, não versionado; dados sintéticos quando aplicável |
| GitHub Actions | Lint, testes, builds, OpenSpec e políticas | Serviços efêmeros e dados sintéticos; sem acesso operacional à produção nos jobs de validação |
| Produção | Operação do fotógrafo proprietário | Recursos e configuração segura exclusivos da Markina Gallery |

O release web-only ainda consome o caminho histórico `docker/.env.homolog` como configuração da produção real. O nome não representa um ambiente de homologação. Esta mudança preserva esse contrato ativo; não renomeie, migre, leia nem edite esse arquivo por inferência.

## Fluxo de publicação

1. Criar pull request e aguardar todos os checks obrigatórios do SHA correspondente.
2. Revisar a compatibilidade da aplicação e das migrations, o inventário, as portas/domínio, o impacto previsto e a recuperação.
3. Iniciar somente o workflow protegido de produção previsto para a operação e obter a aprovação humana do environment `production`.
4. Confirmar o SHA aprovado e a imagem que o runbook gerar ou usar; conferir o ID imutável resultante antes de recriar serviços e não substituir a imagem durante a operação.
5. Executar smoke tests não destrutivos e conferir a saúde dos serviços após a publicação.

Os jobs e gates atuais estão em `.github/workflows/ci.yml` e nas changes OpenSpec de release. Deploy, migration, rollback e escrita de produção continuam exigindo autorização humana específica; CI verde, merge ou aprovação de PR não substituem essa autorização.

Hoje, a matriz `runtime-images` valida builds, enquanto os fluxos protegidos de API/web constroem no host de produção após a aprovação e conferem o ID local executado. Essa identidade protege a troca e o rollback, mas ainda não promove o mesmo artefato do CI; essa integração permanece pendente de arquitetura própria.

## Antes de uma operação de produção

- Fazer inventário somente leitura de versão, serviços da Markina, schema, portas, domínio, saúde e recursos de recuperação.
- Apresentar o plano de impacto zero, incluindo interrupção esperada, migration compatível, smoke tests e rollback aplicável.
- Aguardar a aprovação explícita do proprietário para a operação, o SHA e o escopo apresentados.
- Não usar dados reais em testes destrutivos. Não confundir rollback de container com recuperação do banco.

## Isolamento do servidor compartilhado

- Limitar comandos ao diretório, projeto Compose e serviços da Markina Gallery.
- Nunca alterar containers, imagens, redes, volumes, proxy, firewall, DNS, certificados ou dados de outros projetos.
- Nunca executar prunes. Não executar `docker compose down` sem `-p markina-gallery -f docker/docker-compose.yml`.

## Segredos e recuperação

- Segredos nunca entram no Git, frontend ou logs. A produção usa a configuração externa autorizada; `.env.example` serve somente para desenvolvimento local.
- Consultar `docs/CHECKLIST-DEPLOY-ROLLBACK.md`, os runbooks da operação e a change OpenSpec do candidato antes de qualquer ação.
- Ensaios de backup/restauração automatizados usam ambiente efêmero e dados sintéticos. Restauração de dados reais exige autorização operacional própria.
