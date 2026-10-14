## 1. Modelo e autorização

- [x] 1.1 Modelar acervo-mãe, galeria derivada, referências, configurações, interações e relações comerciais em migration aditiva.
- [x] 1.2 Implementar APIs autorizadas para criação, acesso, prazo, mensagem e permissões por galeria derivada.
- [x] 1.3 Implementar seleções, favoritos e comentários privados com desfazer, remoção e auditoria.

## 2. Estatísticas e interface

- [x] 2.1 Implementar agregados de compra confirmada, seleção não comprada, listas e exportação TXT autorizada, inclusive filtro por cliente.
- [x] 2.2 Implementar página administrativa responsiva de estatísticas, filtros, gráfico temporal e conferência de compras com preview administrativo protegido.
- [x] 2.3 Implementar portal do cliente para revisão, favoritos, comentários, estados de permissão/prazo e histórico de compras com prévias protegidas.

## 3. Qualidade e operação

- [x] 3.1 Cobrir isolamento entre clientes, comentários, métricas, TXT e expiração com testes automatizados.
- [x] 3.2 Validar lint, build, migration, OpenSpec e homologação com dados sintéticos.
- [x] 3.3 Atualizar documentação e registrar que busca facial depende do spike separado.

## Registro de continuidade — 2026-08-26

- Aplicação iniciada após aprovação do proprietário. Os artefatos OpenSpec foram lidos e o código existente foi mapeado; nenhuma tarefa de implementação está concluída.
- O ambiente de homologação autentica o administrador corretamente, mas o frontend ainda não possui a rota `/admin`; após o login visual ocorre `404`. A criação da base administrativa será tratada dentro desta mudança, sem declarar a interface como pronta antes disso.
- Busca facial permanece integralmente fora do escopo desta mudança e depende de `spike-private-facial-discovery`.
- A base visual de `/admin` foi iniciada no frontend para eliminar o 404 pós-login. O build do frontend foi validado localmente em 2026-08-26; a página de estatísticas ainda será entregue na tarefa 2.2.
- A tarefa 1.1 foi concluída em 2026-08-26 com modelos e migration aditiva `20260826_0002`. A migration foi aplicada em banco SQLite descartável e criou todas as tabelas previstas, sem alterar as tabelas de autenticação existentes.
- A tarefa 1.2 foi concluída em 2026-08-26. As APIs administrativas criam acervo-mãe, registram fotos e criam/configuram galerias derivadas; a biblioteca do cliente retorna somente galerias derivadas ativas atribuídas à sua sessão. Foram adicionados testes de referência sem cópia, pertencimento da foto ao acervo e ausência de exposição por acesso legado.
- A tarefa 1.3 foi concluída em 2026-08-26. Seleções respeitam o prazo, favoritos e comentários respeitam as permissões da galeria, e desfazer/remoção registram auditoria. O fotógrafo pode consultar e remover comentários da respectiva galeria privada.
- Em 2026-08-26, o proprietário aprovou ampliar esta mudança com filtro por cliente nas estatísticas e histórico de compras para ambos os papéis. A prévia sem marca-d'água, ampliação e exportação de compras ficam restritas ao fotógrafo; o cliente vê somente prévias protegidas. A integração WhatsApp de confirmação de pagamento foi separada na mudança `add-payment-confirmation-notifications`.
- A tarefa 2.1 foi concluída em 2026-08-26. A API administrativa calcula fotos compradas distintas, selecionadas sem compra, receita confirmada e série diária, com filtros por período, cliente, evento, acervo e galeria derivada. Os TXT de compradas e não compradas contêm exclusivamente identificador e nome de arquivo.
- A tarefa 2.2 foi concluída em 2026-08-26. A rota administrativa `/admin/statistics` oferece filtros com seletores autorizados, indicadores, gráfico temporal, listas e TXT filtrado; a conferência protegida de compras permanece em `/admin/purchases`.
- A tarefa 2.3 foi concluída em 2026-08-26. A rota privada `/gallery/{id}` exibe a revisão, a mensagem, o prazo e as permissões da galeria, com seleção, favorito e comentários reversíveis; o histórico protegido permanece em `/library`.
- A tarefa 3.1 foi concluída em 2026-08-26 com testes de isolamento, prazo, interações, métricas, exportação e prévias por papel. A tarefa 3.3 registra que reconhecimento facial continua condicionado exclusivamente ao spike `spike-private-facial-discovery`.
- A tarefa 3.2 foi reconciliada em 2026-08-28 com evidência verificável: `pytest tests -q` passou 48/48 em SQLite temporário; `vitest run --pool=threads --maxWorkers=1` passou 22/22; `ruff check app tests`, typecheck e build passaram; `openspec validate --all --strict --no-interactive` passou 17/17. A migration aditiva desta change permanece aplicada antes das revisões posteriores e a homologação `markina-homolog.duckdns.org` está saudável no commit que contém essa linhagem, usando somente dados sintéticos documentados para o fluxo.
- Supersession registrada em 2026-08-31: `improve-gallery-and-client-data-lifecycle` é a autoridade para herança de configuração, disponibilidade versus seleção, derivação sob demanda e histórico desacoplado. As tasks concluídas acima não autorizam reaplicar o comportamento anterior conflitante.
