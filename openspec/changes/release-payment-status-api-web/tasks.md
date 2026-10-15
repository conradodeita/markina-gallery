## 1. Preparação e integração

- [ ] 1.1 Conferir inventário somente-leitura e relação entre runtime e main; registrar imagens, configuração e revisão do banco sem segredos.
- [ ] 1.2 Reconciliar a versão instalada com a melhoria de pagamentos em branch isolada; revisar diff contra produção e validar contratos afetados.
- [ ] 1.3 Documentar runbook com comandos restritos, guardas, verificações e rollback pelas imagens reais.
- [ ] 1.4 Publicar PR, obter CI verde e integrar à main conforme autorização de push/merge existente.

## 2. Publicação

- [ ] 2.1 Apresentar inventário final e plano do SHA integrado, com impacto e recuperação, e obter aprovação específica antes da mutação.
- [ ] 2.2 Executar release aprovado, conferir serviços/saúde/HTTPS e registrar evidência; validar o comportamento autenticado quando houver sessão autorizada disponível.
