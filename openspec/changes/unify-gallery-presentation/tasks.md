## 1. Modelo visual e composição compartilhada

- [x] 1.1 Inventariar os contratos de prévia administrativa e galeria derivada, definindo um modelo visual mínimo sem ampliar dados expostos; verificar autorização e ausência de originais.
- [x] 1.2 Criar o componente compartilhado de capa, contexto, navegação de pastas, grade e estados; verificar acessibilidade, foco e responsividade.
- [x] 1.3 Adaptar a prévia do fotógrafo para usar a composição compartilhada e identificar o modo de prévia sem executar ações de cliente.
- [x] 1.4 Adaptar a galeria derivada da cliente para usar a mesma composição, limitada às pastas liberadas e fotos autorizadas.
- [x] 1.5 Reestruturar a personalização administrativa em painéis de marca-d’água, capa/título e organização, com prévia protegida e controles acessíveis; verificar que não há opções livres de CSS ou template.

## 2. Estados, interações e proteção

- [x] 2.1 Implementar estados intencionais de carregamento, erro, ausência de capa, pasta vazia e galeria sem fotos; verificar ações de recuperação sem expor detalhes internos.
- [x] 2.2 Integrar visualizador de prévias protegidas na composição compartilhada; verificar fechamento por teclado, foco, texto alternativo e ausência de URL de original.
- [x] 2.3 Preservar seleção, favorito, comentário e prazo somente no papel da cliente, conforme capacidades devolvidas pelo backend; verificar que a prévia não infere nem concede autorização.

## 3. Qualidade e validação

- [x] 3.1 Cobrir adaptadores, estrutura visual, estados e limites de autorização com testes frontend/backend relevantes.
- [x] 3.1a Cobrir a organização dos painéis de personalização, seus valores controlados, estados de prévia e acessibilidade com testes de componente.
- [x] 3.2 Executar lint, typecheck, testes e build aplicáveis; registrar comandos e resultados.
- [ ] 3.3 Validar as duas superfícies em desktop e smartphone na homologação com dados sintéticos; verificar que a composição é reconhecivelmente a mesma e que cada papel vê apenas o escopo autorizado.
- [ ] 3.4 Validar a change em modo estrito no OpenSpec e manter artefatos sincronizados.

## Evidências de validação

- Frontend: `npx vitest run app/admin/galleries/gallery-editor.test.tsx app/admin/galleries/sources/[sourceId]/preview/page.test.tsx app/gallery/gallery.test.tsx --pool=threads --maxWorkers=1` — 15 testes aprovados. A cobertura da galeria privada também verifica capa servida pela rota protegida, exclusão de foto atribuída mas ainda em pasta `preparing` e estado explícito para falha de autorização.
- Frontend: `npx tsc --noEmit`, `npm run lint` (sem erros; avisos preexistentes de `<img>`), `npm run build` — aprovados.
- Backend: `DATABASE_URL` temporário fora do workspace com `.venv\\Scripts\\python.exe -m pytest tests/test_derived_galleries.py -q` — 31 testes aprovados; `.venv\\Scripts\\python.exe -m ruff check app tests` — aprovado.
- Homologação autenticada (fotógrafo, 2026-08-28): prévia da galeria `Anabella Markina` confirmou modo fotógrafo, capa e prévias protegidas, coleção, visualizador com fechamento por `Escape` e painéis acessíveis de personalização. A rota privada vinculada mostrou corretamente o estado vazio, pois a pasta ainda estava em preparação.
- Homologação sintética (2026-08-28): criada a galeria `Validação visual sintética 20260828` (`76de7895-3d07-46e0-a1db-867e6872990c`) com JPEG abstrato gerado para teste, sem dados pessoais ou imagem de criança. A pasta `Coleção sintética` foi vinculada e liberada para a galeria privada `66ae4a03-d5d2-44a5-b0eb-e21843bf0162`; consulta somente de leitura no banco de homologação confirmou 1 foto e 1 referência de galeria derivada, com a pasta em estado `released`. A sessão de cliente disponível no navegador integrado pertencia a outra cliente e, corretamente, não revelou essa foto. Não foi contornada autenticação/OTP para forjar essa validação. A implementação passou a filtrar a revisão por pastas liberadas e a entregar capa somente pela rota protegida da própria galeria derivada; o teste de regressão cobre uma foto atribuída em pasta ainda em preparação e confirma que ela não aparece no contrato de revisão.
- Pendente: validação visual autenticada das duas superfícies em homologação (3.3), incluindo desktop humano e sessão OTP da cliente sintética; validação estrita pela CLI do OpenSpec, indisponível neste ambiente (3.4). A execução completa da suíte backend também está temporariamente indisponível porque o interpretador-base Python 3.12 referenciado por `backend/.venv` não existe mais na máquina; os testes específicos haviam sido aprovados antes dessa indisponibilidade.
