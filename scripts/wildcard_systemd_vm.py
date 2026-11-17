"""Harness QEMU sem KVM, interfaces de rede, cgroups ou dispositivos do host."""

import json
import os
import subprocess
from pathlib import Path


def run():
    if os.environ.get("PYP_WILDCARD_LAB") != "synthetic-qemu-network-none":
        raise RuntimeError("lab_only")
    if any(
        line.split()[1] == "00000000"
        for line in Path("/proc/net/route").read_text().splitlines()[1:]
    ):
        raise RuntimeError("network_not_isolated")
    work = Path("/tmp/pyp-wildcard-vm")
    work.mkdir(mode=0o700)
    bootstrap = Path("/opt/lab/share/scripts/wildcard_systemd_guest.py").read_text()
    config = {
        "hostname": "pyp-synthetic-systemd-lab",
        "ssh_pwauth": False,
        "ssh_keys": {},
        "write_files": [
            {
                "path": "/var/lib/pyp-wildcard-bootstrap.py",
                "permissions": "0700",
                "content": bootstrap,
            }
        ],
        "runcmd": [["python3", "/var/lib/pyp-wildcard-bootstrap.py", "prepare"]],
        "power_state": {
            "delay": "now",
            "mode": "reboot",
            "timeout": 30,
            "condition": "test -f /var/lib/pyp-wildcard-prepared",
        },
    }
    (work / "user-data").write_text("#cloud-config\n" + json.dumps(config))
    (work / "meta-data").write_text("instance-id: pyp-wildcard-synthetic-20261108\n")
    (work / "network-config").write_text("version: 2\nethernets: {}\n")
    subprocess.run(
        [
            "genisoimage",
            "-quiet",
            "-output",
            str(work / "seed.iso"),
            "-volid",
            "cidata",
            "-joliet",
            "-rock",
            str(work / "user-data"),
            str(work / "meta-data"),
            str(work / "network-config"),
        ],
        check=True,
    )
    subprocess.run(
        [
            "qemu-img",
            "create",
            "-q",
            "-f",
            "qcow2",
            "-F",
            "qcow2",
            "-b",
            "/opt/lab/base.qcow2",
            str(work / "disk.qcow2"),
            "6G",
        ],
        check=True,
    )
    subprocess.run(
        [
            "qemu-system-aarch64",
            "-machine",
            "virt-6.2",
            "-cpu",
            "cortex-a57",
            "-accel",
            "tcg,thread=multi",
            "-smp",
            "4",
            "-m",
            "1536",
            "-bios",
            "/usr/share/qemu-efi-aarch64/QEMU_EFI.fd",
            "-object",
            "rng-random,id=rng0,filename=/dev/urandom",
            "-device",
            "virtio-rng-pci,rng=rng0",
            "-drive",
            f"if=none,id=system,file={work}/disk.qcow2,format=qcow2",
            "-device",
            "virtio-blk-pci,drive=system",
            "-drive",
            f"if=none,id=seed,file={work}/seed.iso,format=raw,readonly=on",
            "-device",
            "virtio-blk-pci,drive=seed",
            "-virtfs",
            "local,path=/opt/lab/share,mount_tag=pyp-lab,security_model=none,readonly=on",
            "-nic",
            "none",
            "-nographic",
        ],
        check=True,
        timeout=1500,
    )


if __name__ == "__main__":
    run()
