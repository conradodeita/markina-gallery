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

- Frontend: `npx vitest run app/admin/galleries/gallery-editor.test.tsx app/admin/galleries/sources/[sourceId]/preview/page.test.tsx app/gallery/gallery.test.tsx --pool=threads --maxWorkers=1` — 15 testes aprovados.
- Frontend: `npx tsc --noEmit`, `npm run lint` (sem erros; avisos preexistentes de `<img>`), `npm run build` — aprovados.
- Backend: `DATABASE_URL` temporário fora do workspace com `.venv\\Scripts\\python.exe -m pytest tests/test_derived_galleries.py -q` — 31 testes aprovados; `.venv\\Scripts\\python.exe -m ruff check app tests` — aprovado.
- Homologação autenticada (fotógrafo, 2026-08-28): prévia da galeria `Anabella Markina` confirmou modo fotógrafo, capa e prévias protegidas, coleção, visualizador com fechamento por `Escape` e painéis acessíveis de personalização. A rota privada vinculada mostrou corretamente o estado vazio, pois a pasta ainda está em preparação. A composição da cliente com fotos liberadas permanece pendente: as galerias sintéticas disponíveis não possuem fotos liberadas e a única foto disponível aparenta retratar uma criança, portanto não foi liberada nem reutilizada para teste. O navegador integrado também não aplicou o override de viewport desktop; a verificação visual desktop continua humana.
- Pendente: validação visual autenticada das duas superfícies em homologação (3.3) e validação estrita pela CLI do OpenSpec, indisponível neste ambiente (3.4).
