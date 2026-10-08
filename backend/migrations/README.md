# Migrations de autenticação

`app.auth.Base.metadata` define o esquema inicial de autenticação desta mudança: `admin_user`, `client`, `gallery_access`, `auth_challenge`, `auth_session` e `audit_event`.

A migration revisável está em `versions/20260825_0001_unified_authentication.py`. Antes de iniciar a API em qualquer ambiente, aplique-a explicitamente com `alembic upgrade head`; o container HTTP não altera o schema automaticamente. Os testes criam o schema isolado pela metadata SQLAlchemy.
