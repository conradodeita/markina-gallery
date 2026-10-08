## 1. Base visual

- [x] 1.1 Consolidar tokens e componentes base, verificando contraste, foco e testes de componente. (tokens globais, foco visível, redução de movimento, kit reutilizável e `frontend/app/ui-kit.test.tsx` + `tsc --noEmit` em 2026-08-28)
- [x] 1.2 Reestruturar shells e navegação responsiva por papel, verificando desktop e mobile. (navegação com seção ativa, shells responsivos e `admin-navigation.test.tsx`; validado por `tsc --noEmit`, lint e build em 2026-08-28)

## 2. Superfícies prioritárias

- [x] 2.1 Implementar dashboard operacional do fotógrafo com estados e ações prioritárias, verificando carregamento, vazio e erro. (`admin/page.test.tsx`, componentes de estado e build em 2026-08-28)
- [x] 2.2 Refinar galeria e jornada da cliente com hierarquia fotográfica e resumo de seleção, verificando acessibilidade. (`gallery.test.tsx`, `library.test.tsx`, resumo com região nomeada e build em 2026-08-28)

## 3. Qualidade

- [x] 3.1 Executar testes, lint, typecheck, build e validação OpenSpec estrita. (`npm test`: 11 arquivos/33 testes; `tsc --noEmit`; `npm run lint` sem erros, 16 avisos preexistentes; `npm run build`; `openspec validate --strict --all --no-interactive`: 20 aprovados em 2026-08-28)
