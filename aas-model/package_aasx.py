"""Package the AAS V3 XML environment into an .aasx (OPC package).

    python aas-model/package_aasx.py
"""
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
XML = HERE / "vehicle-digitaltwin.aas.xml"
OUT = HERE / "vehicle-digitaltwin.aasx"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="text/xml"/>
  <Override PartName="/aasx/aasx-origin" ContentType="text/plain"/>
</Types>
"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://admin-shell.io/aasx/relationships/aasx-origin" Target="/aasx/aasx-origin"/>
</Relationships>
"""

ORIGIN_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://admin-shell.io/aasx/relationships/aas-spec" Target="/aasx/data.xml"/>
</Relationships>
"""


def main() -> None:
    data = XML.read_text(encoding="utf-8")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("aasx/aasx-origin", "")
        z.writestr("aasx/_rels/aasx-origin.rels", ORIGIN_RELS)
        z.writestr("aasx/data.xml", data)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
