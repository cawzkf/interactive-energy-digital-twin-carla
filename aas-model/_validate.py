import sys
from pathlib import Path

XML = Path(__file__).resolve().parent / "vehicle-digitaltwin.aas.xml"

try:
    from basyx.aas.adapter.xml import read_aas_xml_file
except Exception as e:
    print("SDK_IMPORT_FAIL:", e)
    sys.exit(2)

try:
    objs = read_aas_xml_file(str(XML))
    shells = [o for o in objs if type(o).__name__ == "AssetAdministrationShell"]
    submodels = [o for o in objs if type(o).__name__ == "Submodel"]
    print("VALID OK")
    print("shells:", [s.id_short for s in shells])
    print("submodels:", [s.id_short for s in submodels])
    for sm in submodels:
        names = [getattr(e, "id_short", "?") for e in sm.submodel_element]
        print(f"  {sm.id_short} -> {names}")
except Exception as e:
    print("VALIDATION_ERROR:", type(e).__name__, e)
    sys.exit(1)
