## 1. Correção e validação

- [ ] 1.1 Confirmar o canal SSH restrito do backup disponível a `production`; se faltar credencial apropriada, documentar provisionamento protegido e obter autorização própria.
- [ ] 1.2 Corrigir o job `operate`, inclusive leitura posterior, e cobrir configuração ausente, igualdade de destino, uso exclusivo do canal protegido e preservação dos modos/fingerprints em testes de política.
- [ ] 1.3 Validar OpenSpec, testes e CI da PR. Após revisão, merge autorizado e CI da main, comprovar inventário somente leitura pelo canal protegido e obter aprovação do novo snapshot antes de tentar `install`.
