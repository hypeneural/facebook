"""Script de validação e coleta de evidências das 7 simulações de resiliência da Fase 7."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import tempfile
from datetime import datetime, timezone
from app.daily_queue import DailyQueue
from scripts.daily_tick import tick, select_content

def run_all_simulations():
    results = {}
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        photo = tdp / "test.png"
        photo.write_bytes(b"PNG_BYTES_FOR_AUDIT")

        cfg = {
            "enabled": True, "allow_unattended": True, "timezone": "America/Sao_Paulo",
            "account_id": "principal", "rotation_seed": "audit-simulations-seed",
            "slots": ["08:00"], "groups_per_slot": 1,
            "groups": [{"url": "https://www.facebook.com/groups/123456/", "authorized": True}],
            "creatives": [{"id": "c1", "files": [str(photo)]}],
            "captions": [{"id": "t1", "text": "Texto teste"}]
        }

        # 1. Servidor Offline
        db1 = DailyQueue(tdp / "db1.sqlite")
        res1 = tick(cfg, db1, now=datetime(2026, 10, 31, 11, 5, tzinfo=timezone.utc), execute=True,
                    state_fetch=lambda _: (_ for _ in ()).throw(RuntimeError("SERVER_NOT_READY")))
        results["1_server_offline"] = res1
        db1.close()

        # 2. Build Divergente
        db2 = DailyQueue(tdp / "db2.sqlite")
        res2 = tick(cfg, db2, now=datetime(2026, 10, 31, 11, 5, tzinfo=timezone.utc), execute=True,
                    state_fetch=lambda _: (_ for _ in ()).throw(RuntimeError("STALE_SERVER")))
        results["2_stale_server"] = res2
        db2.close()

        # 3. Conta Incorreta / Deslogada
        db3 = DailyQueue(tdp / "db3.sqlite")
        res3 = tick(cfg, db3, now=datetime(2026, 10, 31, 11, 5, tzinfo=timezone.utc), execute=True,
                    state_fetch=lambda _: (_ for _ in ()).throw(RuntimeError("ACCOUNT_NOT_READY")))
        results["3_account_not_ready"] = res3
        db3.close()

        # 4. Post Anterior Não Limpo
        db4 = DailyQueue(tdp / "db4.sqlite")
        res4 = tick(cfg, db4, now=datetime(2026, 10, 31, 11, 5, tzinfo=timezone.utc), execute=True,
                    state_fetch=lambda _: (_ for _ in ()).throw(RuntimeError("PREVIOUS_POST_NOT_CLEARED")))
        results["4_previous_post_not_cleared"] = res4
        db4.close()

        # 5. Mídia Modificada Pós-Planejamento
        db5 = DailyQueue(tdp / "db5.sqlite")
        db5.plan(cfg, "2026-10-31")
        photo.write_bytes(b"ALTERED_BYTES_AFTER_PLANNING")
        job5 = db5.summary()[0]
        try:
            select_content(job5, cfg)
            res5 = {"status": "UNEXPECTED_PASS"}
        except ValueError as exc:
            res5 = {"detected": True, "error": str(exc)}
        results["5_media_modified"] = res5
        db5.close()

        # 6. Slot Expirado (>20 minutos)
        db6 = DailyQueue(tdp / "db6.sqlite")
        db6.plan(cfg, "2026-10-31")
        # 08:00 SP = 11:00 UTC. 11:25 UTC = 25 min atrasado
        res6 = tick(cfg, db6, now=datetime(2026, 10, 31, 11, 25, tzinfo=timezone.utc), execute=True,
                    state_fetch=lambda _: None)
        job6 = db6.summary()[0]
        results["6_slot_expired"] = {"state": res6["state"], "job_status": job6["status"]}
        db6.close()

        # 7. Falha de Transporte Pós-Claim (Sem auto-retry)
        db7 = DailyQueue(tdp / "db7.sqlite")
        calls = []
        def failing_transport(u, c, p):
            calls.append(1)
            raise ConnectionResetError("Conexao interrompida durante upload")

        photo.write_bytes(b"PNG_BYTES_FOR_AUDIT") # restaura bytes para hash bater
        res7_first = tick(cfg, db7, now=datetime(2026, 10, 31, 11, 5, tzinfo=timezone.utc), execute=True,
                          transport=failing_transport, state_fetch=lambda _: None)
        res7_second = tick(cfg, db7, now=datetime(2026, 10, 31, 11, 6, tzinfo=timezone.utc), execute=True,
                           transport=failing_transport, state_fetch=lambda _: None)
        job7 = db7.summary()[0]
        results["7_post_claim_crash_no_retry"] = {
            "first_call_state": res7_first["state"],
            "second_call_state": res7_second["state"],
            "total_transport_calls": len(calls),
            "final_job_status": job7["status"]
        }
        db7.close()

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_all_simulations()
