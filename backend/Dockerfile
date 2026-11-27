# Ferramentas de backup são baixadas e verificadas em uma etapa de build isolada.
# Nenhum binário ou utilitário de extração deste estágio entra na imagem da API.
FROM python:3.13-slim AS backup-tools-build

ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends bzip2 ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY backup-tools.lock /tmp/backup-tools.lock

RUN set -eu; \
    . /tmp/backup-tools.lock; \
    case "${TARGETARCH:-}" in \
      amd64) \
        restic_asset="$RESTIC_LINUX_AMD64_ASSET"; \
        restic_sha256="$RESTIC_LINUX_AMD64_SHA256"; \
        rclone_asset="$RCLONE_LINUX_AMD64_ASSET"; \
        rclone_sha256="$RCLONE_LINUX_AMD64_SHA256" ;; \
      arm64) \
        restic_asset="$RESTIC_LINUX_ARM64_ASSET"; \
        restic_sha256="$RESTIC_LINUX_ARM64_SHA256"; \
        rclone_asset="$RCLONE_LINUX_ARM64_ASSET"; \
        rclone_sha256="$RCLONE_LINUX_ARM64_SHA256" ;; \
      *) echo 'backup_tools_unsupported_architecture' >&2; exit 1 ;; \
    esac; \
    restic_archive="/tmp/$restic_asset"; \
    rclone_archive="/tmp/$rclone_asset"; \
    curl --fail --location --retry 3 --retry-all-errors "$RESTIC_RELEASE_BASE/$restic_asset" --output "$restic_archive"; \
    printf '%s  %s\n' "$restic_sha256" "$restic_archive" | sha256sum --check --status; \
    bzip2 --decompress --stdout "$restic_archive" > /usr/local/bin/restic; \
    curl --fail --location --retry 3 --retry-all-errors "$RCLONE_RELEASE_BASE/$rclone_asset" --output "$rclone_archive"; \
    printf '%s  %s\n' "$rclone_sha256" "$rclone_archive" | sha256sum --check --status; \
    python -c 'import os, sys, zipfile; z=zipfile.ZipFile(sys.argv[1]); names=[n for n in z.namelist() if n.rsplit("/", 1)[-1] == "rclone"]; assert len(names) == 1 and z.testzip() is None, "rclone_release_archive_invalid"; open(sys.argv[2], "wb").write(z.read(names[0])); os.chmod(sys.argv[2], 0o755)' "$rclone_archive" /usr/local/bin/rclone; \
    chmod 0755 /usr/local/bin/restic; \
    restic_output="$(restic version)"; \
    case "$restic_output" in "restic $RESTIC_VERSION "*) ;; *) echo 'backup_tools_restic_version_mismatch' >&2; exit 1 ;; esac; \
    rclone_output="$(rclone version | sed -n '1p')"; \
    test "$rclone_output" = "rclone v$RCLONE_VERSION" || { echo 'backup_tools_rclone_version_mismatch' >&2; exit 1; }; \
    printf '%s\n%s\n' "$(printf '%s\n' "$restic_output" | sed -n '1p')" "$rclone_output"; \
    rm -f "$restic_archive" "$rclone_archive"

# Runtime comum da API e dos workers; ferramentas Python permanecem nas
# dependências de execução atuais, sem dependências de desenvolvimento novas.
FROM python:3.13-slim AS backend-runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# curl (healthcheck) e procps (pgrep para o worker)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-push.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY facial-assets ./facial-assets
COPY migrations ./migrations
COPY alembic.ini ./
COPY tests ./tests

# Este target é selecionado somente pelo serviço worker. A aplicação continua
# com o entrypoint já existente; a integração do executor é uma task posterior.
FROM backend-runtime-base AS backup-worker

ARG TARGETARCH

LABEL com.markina-gallery.build-target="backup-worker"

COPY --from=backup-tools-build /usr/local/bin/restic /usr/local/bin/restic
COPY --from=backup-tools-build /usr/local/bin/rclone /usr/local/bin/rclone
RUN mkdir -p /usr/share/licenses/restic /usr/share/licenses/rclone /usr/share/doc/pyp-backup-tools
COPY backup-tools.lock /tmp/backup-tools.lock
RUN set -eu; \
    . /tmp/backup-tools.lock; \
    case "${TARGETARCH:-}" in \
      amd64) deb_arch=amd64; client_sha256="$POSTGRESQL_CLIENT_AMD64_SHA256" ;; \
      arm64) deb_arch=arm64; client_sha256="$POSTGRESQL_CLIENT_ARM64_SHA256" ;; \
      *) echo 'postgresql_client_unsupported_architecture' >&2; exit 1 ;; \
    esac; \
    test "$(dpkg --print-architecture)" = "$deb_arch"; \
    . /etc/os-release; \
    test "${VERSION_CODENAME:-}" = "$PGDG_DEBIAN_CODENAME"; \
    key_path=/usr/share/keyrings/pyp-pgdg.asc; \
    key_download=/tmp/pyp-pgdg.asc; \
    curl --fail --location --retry 3 --retry-all-errors "$PGDG_KEY_URL" --output "$key_download"; \
    printf '%s  %s\n' "$PGDG_KEY_SHA256" "$key_download" | sha256sum --check --status; \
    install -D -m 0644 "$key_download" "$key_path"; \
    printf 'deb [arch=%s signed-by=%s] %s %s %s\n' "$deb_arch" "$key_path" "$PGDG_REPOSITORY" "$PGDG_SUITE" "$PGDG_COMPONENT" > /etc/apt/sources.list.d/pyp-pgdg.list; \
    apt-get update; \
    cd /tmp; \
    apt-get download "$POSTGRESQL_CLIENT_PACKAGE=$POSTGRESQL_CLIENT_PACKAGE_VERSION"; \
    deb_path="/tmp/${POSTGRESQL_CLIENT_PACKAGE}_${POSTGRESQL_CLIENT_PACKAGE_VERSION}_${deb_arch}.deb"; \
    printf '%s  %s\n' "$client_sha256" "$deb_path" | sha256sum --check --status; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$deb_path"; \
    pg_dump_version="$(pg_dump --version)"; \
    case "$pg_dump_version" in \
      "pg_dump (PostgreSQL) $POSTGRESQL_CLIENT_VERSION"|"pg_dump (PostgreSQL) $POSTGRESQL_CLIENT_VERSION (Debian $POSTGRESQL_CLIENT_PACKAGE_VERSION)") ;; \
      *) echo 'postgresql_client_pg_dump_version_mismatch' >&2; exit 1 ;; \
    esac; \
    pg_restore_version="$(pg_restore --version)"; \
    case "$pg_restore_version" in \
      "pg_restore (PostgreSQL) $POSTGRESQL_CLIENT_VERSION"|"pg_restore (PostgreSQL) $POSTGRESQL_CLIENT_VERSION (Debian $POSTGRESQL_CLIENT_PACKAGE_VERSION)") ;; \
      *) echo 'postgresql_client_pg_restore_version_mismatch' >&2; exit 1 ;; \
    esac; \
    test -s /usr/share/doc/postgresql-client-17/copyright || { echo 'postgresql_client_license_notice_missing' >&2; exit 1; }; \
    rm -f "$deb_path" "$key_download" "$key_path" /etc/apt/sources.list.d/pyp-pgdg.list; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/backup-tools.lock
COPY backup-tools.lock /usr/share/doc/pyp-backup-tools/backup-tools.lock
COPY licenses/backup-tools/restic-LICENSE /usr/share/licenses/restic/LICENSE
COPY licenses/backup-tools/rclone-COPYING /usr/share/licenses/rclone/COPYING

CMD ["python", "-m", "app.worker"]

# Mantido como último estágio para que os builds existentes da API/migrate
# continuem sem Restic/Rclone e sem exigir TARGETARCH.
FROM backend-runtime-base AS api-runtime

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
