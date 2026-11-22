# QEMU TCG dentro de container sem privilégios/devices do host. Somente laboratório.
FROM ubuntu@sha256:8a2321a92b438238f93b4346fff61bc4259c99fdd4d9b52ee86f153fee0c344f
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    qemu-system-arm qemu-utils qemu-efi-aarch64 genisoimage curl ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/lab/share && curl --fail --location --retry 2 \
    https://cloud-images.ubuntu.com/releases/jammy/release/ubuntu-22.04-server-cloudimg-arm64.img \
    -o /opt/lab/base.qcow2 && echo '7fc0212296c65f8e20f8e9af89aaab9500ea4ec73cfb245afa0f2b509bb90785  /opt/lab/base.qcow2' | sha256sum --check
COPY scripts/ /opt/lab/share/scripts/
COPY backend/ /opt/lab/share/backend/
COPY wheels/ /opt/lab/share/wheels/
COPY requirements-linux-arm64.lock /opt/lab/share/requirements.lock
COPY dependency-manifest.json /opt/lab/share/dependency-manifest.json
COPY wildcard_systemd_vm.py /opt/lab/run.py
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["python3", "/opt/lab/run.py"]
