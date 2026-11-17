# Validação local

## Confirmação de e-mail sem travamento em falha — 15/11/2026

- Revisão de `account-action.tsx` encontrou que a confirmação de novo e-mail não tratava rejeição de `fetch` e descartava o token mesmo com erro HTTP. Dois testes novos reproduziram os defeitos: rede deixou o botão em Confirmando e gerou rejeição não tratada; HTTP 503 retirou a ação de confirmação (6 passed/2 failed antes da correção).
- `confirmEmail` agora encerra o carregamento em finally, mostra feedback de rede e limpa o token somente no sucesso. O token continua apenas em memória após erro, fora do URL/storage, e o reenvio exige outro clique. A prova confirma exatamente uma chamada antes desse clique, o mesmo token somente no POST e conclusão de sucesso depois da repetição explícita. Backend, expiração, unicidade e revogação de sessões não foram alterados.
- Seleção serial de account-action, auth-entry, admin-navigation, tenant-address-panel, onboarding-gate-notice e photographer-onboarding-gate: **58 passed em seis arquivos**, 73,25 s. Os oito casos do componente de ação pública passaram. ESLint dos dois arquivos alterados e `tsc --noEmit`: exit 0. O guia local Next use-client foi conferido antes da edição.
- Leitura dos helpers/consumidores confirmou avisos de onboarding com retorno local sem query/fragmento, navegação de créditos/console e preparação de hostname separada da ativação. Nenhuma alteração especulativa foi feita nesses contratos. A inspeção visual autenticada atual continua pendente.
