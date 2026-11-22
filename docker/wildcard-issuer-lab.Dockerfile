# Laboratório isolado; não instalar no Oracle ou usar como runtime da aplicação.
FROM python@sha256:5545cc064ff154ca41f886e5e2223ce85f28445d00eb83cd517ce3dd4ba688df
LABEL pyp.lab="operational-wildcard" purpose="synthetic-offline-tests"
COPY requirements-linux-arm64.lock /lab/requirements.lock
RUN python -m pip install --no-cache-dir --no-compile --only-binary=:all: --require-hashes -r /lab/requirements.lock
WORKDIR /lab
COPY scripts/ /lab/scripts/
COPY backend/ /lab/backend/
ENTRYPOINT ["python", "-B", "-m", "unittest", "discover", "-s", "scripts", "-p", "test_wildcard*.py", "-v"]
