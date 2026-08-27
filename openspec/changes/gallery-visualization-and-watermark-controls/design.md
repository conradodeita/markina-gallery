## Contexto

A configuração pertence à galeria do evento e deve ser aplicada pelo backend. O navegador apenas envia comandos e renderiza contratos autorizados.

## Decisões

- Persistir configurações visuais na galeria-mãe, com valores padrão neutros e validação de limites.
- Gerar derivados com a configuração vigente; prévias existentes não serão reescritas silenciosamente.
- Usar uma rota autenticada de visualização da galeria, distinguindo sessão de fotógrafo e cliente.
- O modo de pastas será um enum explícito (`individual` ou `sequential`), sem inferência no navegador.
- A exclusão em massa reutilizará a mesma regra contextual da exclusão unitária e retornará itens bloqueados sem apagar parcialmente sem informar o resultado.

## Segurança e reversão

Originais, chaves de armazenamento e dados de outras galerias nunca serão enviados. A migration terá downgrade reversível; falha de processamento manterá a foto em estado pendente.
