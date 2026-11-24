"""Storage exclusivamente em memória para composição local sintética."""

import hashlib

from app.media_archive_storage import ArchiveDownloadReceipt, ArchiveRemoteObject


class SyntheticMediaArchiveStorage:
    """Sem transporte, callbacks, credenciais ou acesso ao filesystem."""

    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.by_key: dict[str, str] = {}

    def upload_object(self, *, object_key, mime_type, size_bytes, sha256, stream):
        payload = stream.read(size_bytes + 1)
        if len(payload) != size_bytes or hashlib.sha256(payload).hexdigest() != sha256:
            raise ValueError("Conteúdo sintético incompatível.")
        remote_id = self.by_key.get(object_key)
        if remote_id is not None:
            if self.objects.get(remote_id) != (payload, mime_type):
                raise ValueError("Chave sintética divergente.")
        else:
            remote_id = f"synthetic-{len(self.by_key) + 1}"
            self.by_key[object_key] = remote_id
            self.objects[remote_id] = (payload, mime_type)
        return ArchiveRemoteObject(remote_id, len(payload), mime_type)

    def read_object(self, *, remote_id):
        stored = self.objects.get(remote_id)
        if stored is None:
            return None
        payload, mime_type = stored
        return ArchiveRemoteObject(remote_id, len(payload), mime_type)

    def download_object(self, *, remote_id, destination):
        payload, _ = self.objects[remote_id]
        destination.write(payload)
        return ArchiveDownloadReceipt(len(payload), hashlib.sha256(payload).hexdigest())

    def delete_object(self, *, remote_id):
        self.objects.pop(remote_id, None)
