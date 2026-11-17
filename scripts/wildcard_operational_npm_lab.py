"""Reutiliza a prova NPM protegida, injetando somente o novo instalador."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wildcard_npm_lab import run
from scripts.wildcard_operational_bundle import validate_bundle
from scripts.wildcard_operational_installer import DurableInstaller, InstallationError

if __name__ == "__main__":
    run(
        installer_factory=DurableInstaller,
        bundle_validator=validate_bundle,
        installation_error=InstallationError,
    )
