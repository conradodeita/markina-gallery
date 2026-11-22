## 1. Contexto e contrato
- [x] 1.1 Conferir branch, main e trabalho local/conversas disponíveis; registrar diagnóstico medido e escopo isolado.
- [x] 1.2 Definir autorização, cache por tenant, frescor e confinamento sem alterar contrato de UI.

## 2. Correção
- [x] 2.1 Implementar e testar medição com queries constantes, cache limitado, autorização em cache hit/saída e paths seguros equivalentes. Próprios: 13 passed/2 skips Windows; três limites symlink passaram em Linux; comparação real READ ONLY 5/2 SELECTs e mesmos bytes.
- [x] 2.2 Agregar contagens do resumo no SQL e validar contrato/autorização/isolamento existentes. Quatro regressões API aprovadas (três do resumo e uma entre tenants).

## 3. Validação e entrega
- [x] 3.1 Executar regressões focadas de mídia/tenancy, lint e OpenSpec; comparar desempenho por queries e registrar limites. 20 passed/2 skips Windows, 3 fronteiras Linux; Ruff/compile/OpenSpec aprovados. Medição real isolada 16,3s→3,6s/1,16ms, bytes idênticos.
- [x] 3.2 Revisar diff, remover somente duplicações diretamente substituídas, separar trabalho preexistente e registrar implementação e situação de publicação. Delta exclusivo de resumo/medição e seus testes; artefatos de limpeza anterior preservados fora do commit. Sem publicação automática.
