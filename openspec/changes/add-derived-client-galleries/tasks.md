## 1. Modelo e autorização

- [x] 1.1 Modelar acervo-mãe, galeria derivada, referências, configurações, interações e relações comerciais em migration aditiva.
- [x] 1.2 Implementar APIs autorizadas para criação, acesso, prazo, mensagem e permissões por galeria derivada.
- [x] 1.3 Implementar seleções, favoritos e comentários privados com desfazer, remoção e auditoria.

## 2. Estatísticas e interface

- [ ] 2.1 Implementar agregados de compra confirmada, seleção não comprada, listas e exportação TXT autorizada.
- [ ] 2.2 Implementar página administrativa responsiva de estatísticas, filtros e gráfico temporal.
- [ ] 2.3 Implementar portal do cliente para revisão, favoritos, comentários e estados de permissão/prazo.

## 3. Qualidade e operação

- [ ] 3.1 Cobrir isolamento entre clientes, comentários, métricas, TXT e expiração com testes automatizados.
- [ ] 3.2 Validar lint, build, migration, OpenSpec e homologação com dados sintéticos.
- [ ] 3.3 Atualizar documentação e registrar que busca facial depende do spike separado.

## Registro de continuidade — 2026-08-26

- Aplicação iniciada após aprovação do proprietário. Os artefatos OpenSpec foram lidos e o código existente foi mapeado; nenhuma tarefa de implementação está concluída.
- O ambiente de homologação autentica o administrador corretamente, mas o frontend ainda não possui a rota `/admin`; após o login visual ocorre `404`. A criação da base administrativa será tratada dentro desta mudança, sem declarar a interface como pronta antes disso.
- Busca facial permanece integralmente fora do escopo desta mudança e depende de `spike-private-facial-discovery`.
- A base visual de `/admin` foi iniciada no frontend para eliminar o 404 pós-login. O build do frontend foi validado localmente em 2026-08-26; a página de estatísticas ainda será entregue na tarefa 2.2.
- A tarefa 1.1 foi concluída em 2026-08-26 com modelos e migration aditiva `20260826_0002`. A migration foi aplicada em banco SQLite descartável e criou todas as tabelas previstas, sem alterar as tabelas de autenticação existentes.
- A tarefa 1.2 foi concluída em 2026-08-26. As APIs administrativas criam acervo-mãe, registram fotos e criam/configuram galerias derivadas; a biblioteca do cliente retorna somente galerias derivadas ativas atribuídas à sua sessão. Foram adicionados testes de referência sem cópia, pertencimento da foto ao acervo e ausência de exposição por acesso legado.
- A tarefa 1.3 foi concluída em 2026-08-26. Seleções respeitam o prazo, favoritos e comentários respeitam as permissões da galeria, e desfazer/remoção registram auditoria. O fotógrafo pode consultar e remover comentários da respectiva galeria privada.
