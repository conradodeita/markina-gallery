# Checklist de deploy e rollback — Pick-your-Pic

Limitado à Pick-your-Pic. Nunca afeta containers, imagens, redes, volumes, proxy, firewall, DNS ou certificados de outros projetos.

## 0. Gate obrigatório antes de qualquer ação em produção

- [ ] Consultar o workflow protegido e o runbook OpenSpec vigentes para o tipo de release; não usar comandos de snapshots históricos.
- [ ] Confirmar PR aprovado e todos os checks obrigatórios verdes no SHA exato da operação.
- [ ] Concluir o inventário somente leitura de serviços, schema, portas, domínio, saúde, artefato ativo e recuperação.
- [ ] Apresentar ao proprietário o alvo, SHA/digest, impacto, smoke tests, janela e rollback aplicável.
- [ ] Receber aprovação humana explícita para operação e escopo apresentados, incluindo o gate `production` quando aplicável.

## 1. Preparação do release

- [ ] Confirmar compatibilidade da aplicação e das migrations sem executar mudanças em produção.
- [ ] Confirmar a proveniência do SHA e o ID da imagem de rollback. Os fluxos atuais constroem no host de produção após aprovação e fixam o ID local antes da recriação; isso não equivale à promoção do artefato validado pelo CI.
- [ ] Confirmar backup e procedimento de recuperação aplicáveis, sem expor conteúdo ou credenciais.
- [ ] Usar somente a configuração externa prevista no contrato atual de produção. O caminho histórico `docker/.env.homolog` é usado pelo release web-only como configuração da produção; seu nome não cria um alvo de homologação e não deve ser renomeado nesta mudança.
- [ ] Manter indisponível o acesso de tenants externos até a autorização expressa de lançamento.

## 2. Publicação protegida direta em produção

- [ ] Disparar somente o workflow de produção correspondente e autorizado; `develop` não publica automaticamente.
- [ ] Revalidar SHA, digest, inventário e fingerprint sob os gates do próprio workflow.
- [ ] Obter aprovação humana no environment protegido antes de qualquer etapa mutável.
- [ ] Alterar somente os serviços previstos no runbook daquele release; não executar `docker compose up` genérico como atalho.
- [ ] Executar smoke tests não destrutivos e conferir saúde, identidade do artefato e recursos fora do escopo.
- [ ] Registrar a execução e os resultados sem segredos ou dados de clientes.

### Gate do subsistema facial

- [ ] Preservar `FACIAL_PROCESSING_ENABLED=true`, conforme instrução vigente do proprietário; interromper se o artefato ou a configuração alvo exigir desabilitá-lo.
- [ ] Confirmar os gates próprios de segurança, privacidade, capacidade, acesso e recuperação previstos para o release.
- [ ] Manter o fluxo infantil sujeito à autorização e aos controles aplicáveis; esta checklist não concede autorização para ampliá-lo.

## 3. Rollback

- [ ] Usar apenas o modo de recuperação/rollback do workflow e runbook correspondentes, com nova validação de identidade e inventário.
- [ ] Confirmar que a imagem restaurada corresponde ao recibo saudável registrado; não inferir identidade por tag móvel.
- [ ] Repetir os smoke tests e verificações de saúde do release.
- [ ] Tratar restauração de banco separadamente: exige autorização própria e procedimento validado em CI efêmera com dados sintéticos. Rollback de container não recupera dados.
- [ ] Se o subsistema facial estiver afetado, seguir o plano aprovado para suspender admissões, preservar auditoria e comprovar o lifecycle de dados.
- [ ] Registrar incidente, causa e evidências para o proprietário.

## 4. Pós-deploy

- [ ] Confirmar que nenhum serviço, dado ou recurso de outro projeto foi alterado.
- [ ] Atualizar a change OpenSpec de release somente com evidência observada; sincronizar specs e arquivar após revisão humana.
- [ ] Atualizar `docs/DECISOES-TECNICAS.md` quando houver decisão nova.
