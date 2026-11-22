"""Offline synthetic compatibility probe; never connects to queues or model services."""
from __future__ import annotations

import hashlib
import io
import json
import resource
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageOps


def pixels(image):
    return {'size': list(image.size), 'mode': image.mode,
            'sha256': hashlib.sha256(image.tobytes()).hexdigest()}


def probe():
    started = time.monotonic()
    rgb = Image.new('RGB', (257, 193))
    rgb.putdata([((x * 17 + y * 3) % 256, (x + y * 11) % 256, (x * y) % 256)
                 for y in range(193) for x in range(257)])
    result, automatic = {}, {}
    # Exercise each orientation and each supported photographic JPEG input mode.
    for mode in ('RGB', 'L', 'CMYK'):
        for orientation in (1, 3, 6, 8):
            data = io.BytesIO()
            exif = Image.Exif()
            exif[274] = orientation
            exif[271] = 'SYNTHETIC'
            rgb.convert(mode).save(data, format='JPEG', quality=95, exif=exif)
            payload = data.getvalue()
            with Image.open(io.BytesIO(payload)) as opened:
                opened.load()
                visual = ImageOps.exif_transpose(opened).convert('RGB')
                expected_size = (193, 257) if orientation in (6, 8) else (257, 193)
                assert visual.size == expected_size
                record = {'decoded': pixels(visual)}
                for size in (480, 1600, 2000):
                    derivative = visual.copy()
                    derivative.thumbnail((size, size), Image.Resampling.LANCZOS)
                    record[str(size)] = pixels(derivative)
                horizontal = visual.resize((128, visual.height), Image.Resampling.LANCZOS)
                horizontal = horizontal.resize((128, 96), Image.Resampling.LANCZOS)
                vertical = visual.resize((visual.width, 96), Image.Resampling.LANCZOS)
                vertical = vertical.resize((128, 96), Image.Resampling.LANCZOS)
                record['horizontal_first'] = pixels(horizontal)
                record['vertical_first'] = pixels(vertical)
                automatic[mode + '/' + str(orientation)] = pixels(
                    visual.resize((128, 96), Image.Resampling.LANCZOS))
            # Call the actual installed normalization and protection implementations.
            from app.media import save_presentation_jpeg, watermark

            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                marked = watermark(visual)
                assert marked.size == expected_size
                assert pixels(marked)['sha256'] != pixels(visual)['sha256']
                record['protected'] = pixels(marked)
                presentation = root / 'presentation.jpg'
                save_presentation_jpeg(marked, presentation)
                with Image.open(presentation) as output:
                    assert output.format == 'JPEG' and output.size == expected_size
                    record['presentation'] = pixels(output.convert('RGB'))
            # NumPy/OpenCV are present only in facial images: require their real path there.
            try:
                import numpy  # noqa: F401
            except ImportError:
                record['facial_reference'] = 'not_installed'
            else:
                from app.facial.reference import decode_reference_bytes
                reference = decode_reference_bytes(payload, max_pixels=1_000_000)
                assert list(reference.shape) == [expected_size[1], expected_size[0], 3]
                assert hashlib.sha256(reference[:, :, ::-1].copy().tobytes()).hexdigest() == record['decoded']['sha256']
                record['facial_reference'] = hashlib.sha256(reference.tobytes()).hexdigest()
            result[mode + '/' + str(orientation)] = record
    # Alpha, palette and 16-bit PNG are ancillary derivative/import regression contracts.
    for mode in ('RGBA', 'P', 'I;16'):
        data = io.BytesIO()
        source = rgb.convert('L').convert(mode) if mode == 'I;16' else rgb.convert(mode)
        source.save(data, format='PNG')
        data.seek(0)
        with Image.open(data) as opened:
            opened.load()
            result['PNG/' + mode] = pixels(opened.convert('RGB'))
    # Representative 7MP synthetic photograph: the production thumbnail sizes
    # must really shrink it, rather than only exercise the no-op path above.
    large = rgb.resize((3084, 2316), Image.Resampling.NEAREST)
    for side in (480, 1600, 2000):
        small = large.copy()
        small.thumbnail((side, side), Image.Resampling.LANCZOS)
        assert small.width == side
        result['large_thumbnail/' + str(side)] = pixels(small)
    return {'contracts': result, 'automatic_resize': automatic,
            'seconds': round(time.monotonic() - started, 3),
            'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


if __name__ == '__main__':
    print(json.dumps(probe(), sort_keys=True))
