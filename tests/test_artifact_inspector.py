import base64
import csv
import hashlib
import io
import zipfile

from scripts.inspect_python_artifacts import assert_record


def record_hash(payload):
    digest = hashlib.sha256(payload).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def test_assert_record_accepts_windows_path_separators():
    record_name = "example-1.0.dist-info/RECORD"
    files = {
        "example/__init__.py": b"VALUE = 1\n",
        "example-1.0.dist-info/METADATA": b"Name: example\nVersion: 1.0\n",
    }
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for path, payload in files.items():
        writer.writerow((path.replace("/", "\\"), record_hash(payload), len(payload)))
    writer.writerow((record_name.replace("/", "\\"), "", ""))
    record = output.getvalue().encode("utf-8")

    wheel = io.BytesIO()
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, payload in files.items():
            archive.writestr(path, payload)
        archive.writestr(record_name, record)

    wheel.seek(0)
    with zipfile.ZipFile(wheel) as archive:
        assert_record(archive, archive.namelist())
