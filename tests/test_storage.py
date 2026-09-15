import hashlib

from vrf.adapters.outbound.storage.files import FileStorage


def test_save_conserva_metadatos(tmp_path) -> None:
    storage = FileStorage(str(tmp_path))
    data = b"contenido de la factura"
    result = storage.save(data, "factura.pdf", "application/pdf")

    assert result.nombre_original == "factura.pdf"
    assert result.mime == "application/pdf"
    assert result.size == len(data)
    assert result.sha256 == hashlib.sha256(data).hexdigest()
    assert (tmp_path / result.path).exists()


def test_read_devuelve_bytes_originales(tmp_path) -> None:
    storage = FileStorage(str(tmp_path))
    data = b"pdf-raw-bytes"
    result = storage.save(data, "f.pdf", "application/pdf")

    assert storage.read(result.path) == data


def test_contenido_identico_no_se_duplica(tmp_path) -> None:
    storage = FileStorage(str(tmp_path))
    data = b"mismo contenido"
    primero = storage.save(data, "a.pdf", "application/pdf")
    segundo = storage.save(data, "b.pdf", "application/pdf")

    assert primero.path == segundo.path
    assert len(list(tmp_path.iterdir())) == 1
