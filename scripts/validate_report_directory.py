"""CI gate: valida TODOS os relatórios versionáveis em reports/forensic/."""
from __future__ import annotations
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.validate_forensic_report import main as validate_one

def verify_directory(folder):
    folder=Path(folder)
    if not folder.exists():
        print("NO_COMMITTED_SNAPSHOTS")
        return 0
    report_files=sorted(folder.glob("*.json"))
    for file in report_files:
        try:
            validate_one(file)
        except (OSError,ValueError,TypeError) as e:
            print("INVALID_SNAPSHOT_"+type(e).__name__)
            return 2
    print("VALID_SNAPSHOTS="+str(len(report_files)))
    return 0

if __name__=="__main__":
    raise SystemExit(verify_directory(ROOT/"reports"/"forensic"))
