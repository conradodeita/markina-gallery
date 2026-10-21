# Ownership do cofre

`infinitepay_credential` é R/K: configuração própria do tenant, não infraestrutura global. A chave primária UUID tem candidate key `(id, tenant_id)`; as referências da configuração e compra são compostas por credencial/tenant. O resolvedor lê somente com UUID próprio e tenant derivado da sessão ou compra persistida. Nenhum endpoint recebe tenant/credential-id para leitura de segredo. `homolog_cleanup.PRESERVED_TABLES` conserva os envelopes como configuração, sem descriptografá-los.

Migration 0085 ensaiada em PostgreSQL 17 descartável: upgrade/downgrade vazio/legado e inserts diretos de configuração/compra de B com referência de A; ambos violam FK. Nenhuma credencial legada é copiada, gerada ou convertida. Novas referências são nullable e a origem existente recebe `server_binding`.

O gerador estático anterior de `add-small-multi-photographer-pilot` falha nesta base ao encontrar `RawDevelopmentSettings`, já presente em `auth.py` mas ausente de `TABLE_GROUPS`. Foi acrescido somente `InfinitePayCredential` ao grupo R/K do mapa; não alterar a missão RAW para produzir um relatório aparentemente verde. Esta classificação explícita e os testes de FK são a evidência desta change; resultado global novamente delimitado em `validation.md`.
