"""Fila SQLite de publicações autorizadas: planejamento/claim, SEM envio automático.

Um job pode ser reclamado uma única vez, antes de qualquer tentativa de HTTP.
Em caso de crash, permanece NEEDS_REVIEW e não pode ser repetido por acaso.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import sqlite3
from zoneinfo import ZoneInfo
from app.validation import group_url

TIMEZONE = ZoneInfo("America/Sao_Paulo")
CLOCK = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
STATES = {"PLANNED", "NEEDS_REVIEW", "MISSED", "SKIPPED", "VERIFIED_EXTERNALLY"}
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  day TEXT NOT NULL,
  slot TEXT NOT NULL,
  due_utc TEXT NOT NULL,
  account_id TEXT NOT NULL,
  group_id TEXT NOT NULL,
  creative_id TEXT NOT NULL,
  caption_id TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN
    ('PLANNED','NEEDS_REVIEW','MISSED','SKIPPED','VERIFIED_EXTERNALLY')),
  operation_id TEXT,
  checked_at TEXT,
  UNIQUE(day,group_id)
);
CREATE INDEX IF NOT EXISTS idx_due ON jobs(status,due_utc);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  job_id TEXT NOT NULL,
  event TEXT NOT NULL,
  code TEXT NOT NULL DEFAULT ''
);
"""
def _now():
    return datetime.now(timezone.utc).isoformat()

def validate_config(cfg):
    if not isinstance(cfg,dict) or type(cfg.get("enabled")) is not bool:
        raise ValueError("enabled deve ser booleano.")
    if cfg.get("timezone") != "America/Sao_Paulo":
        raise ValueError("Use timezone America/Sao_Paulo.")
    slots = cfg.get("slots")
    if not isinstance(slots,list) or not 1 <= len(slots) <= 12 or any(
        not isinstance(x,str) or CLOCK.fullmatch(x) is None for x in slots
    ) or len(set(slots)) != len(slots):
        raise ValueError("Horários HH:MM únicos são obrigatórios.")
    groups = cfg.get("groups")
    if not isinstance(groups,list) or not groups or len(groups)>100:
        raise ValueError("Cadastre grupos autorizados explicitamente.")
    ids = []
    for group in groups:
        if not isinstance(group,dict) or group.get("authorized") is not True:
            raise ValueError("Cada grupo precisa authorized=true após revisão das regras.")
        ids.append(group_url(group.get("url","")).split("/groups/")[1].strip("/"))
    if len(ids)!=len(set(ids)):
        raise ValueError("Grupo duplicado na campanha.")
    for kind in ("creatives","captions"):
        variants = cfg.get(kind)
        if not isinstance(variants,list) or not variants or len(variants)>100:
            raise ValueError("Cadastre ao menos uma variante aprovada: "+kind)
        keys = []
        for item in variants:
            if not isinstance(item,dict) or not isinstance(item.get("id"),str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}",item["id"]):
                raise ValueError("Identificador de variante inválido.")
            keys.append(item["id"])
        if len(set(keys))!=len(keys):
            raise ValueError("Variante duplicada: "+kind)
    max_per_slot=cfg.get("groups_per_slot",1)
    if type(max_per_slot) is not int or not 1<=max_per_slot<=3:
        raise ValueError("groups_per_slot permitido entre 1 e 3 para MVP.")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}",str(cfg.get("account_id",""))):
        raise ValueError("Perfil local inválido.")
    if not isinstance(cfg.get("rotation_seed"),str) or len(cfg["rotation_seed"])<12:
        raise ValueError("Defina rotation_seed único e estável.")
    return cfg

class DailyQueue:
    def __init__(self, database):
        self.path=Path(database)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=5)
        self.db.row_factory=sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def _event(self,job_id,event,code=""):
        self.db.execute(
            "INSERT INTO events(at,job_id,event,code) VALUES(?,?,?,?)",
            (_now(),job_id,event,code))

    def plan(self, cfg, target_day):
        validate_config(cfg)
        if isinstance(target_day,str):
            target_day=date.fromisoformat(target_day)
        if not isinstance(target_day,date):
            raise ValueError("Data inválida.")
        seed=int.from_bytes(hashlib.sha256(
            (cfg["rotation_seed"]+"|"+target_day.isoformat()).encode()).digest()[:8],"big")
        rng=random.Random(seed)
        groups=list(cfg["groups"])
        rng.shuffle(groups)
        creative_ids=[x["id"] for x in cfg["creatives"]]
        caption_ids=[x["id"] for x in cfg["captions"]]
        results=[]
        cursor=0
        self.db.execute("BEGIN IMMEDIATE")
        try:
            for slot in sorted(cfg["slots"]):
                for offset in range(cfg.get("groups_per_slot",1)):
                    if cursor>=len(groups):
                        break
                    group=groups[cursor]
                    cursor+=1
                    gid=group_url(group["url"]).split("/groups/")[1].strip("/")
                    creative=rng.choice(creative_ids)
                    caption=rng.choice(caption_ids)
                    creative_item=next(x for x in cfg["creatives"] if x["id"]==creative)
                    caption_item=next(x for x in cfg["captions"] if x["id"]==caption)
                    manifest=json.dumps({"group_id":gid,"creative":creative_item,
                                         "caption":caption_item},sort_keys=True,ensure_ascii=False)
                    manifest_digest=hashlib.sha256(manifest.encode("utf-8")).hexdigest()
                    time_local=datetime.combine(target_day,datetime.strptime(slot,"%H:%M").time(),tzinfo=TIMEZONE)
                    due=(time_local+timedelta(minutes=offset*10)).astimezone(timezone.utc).isoformat()
                    raw="|".join([target_day.isoformat(),slot,gid,cfg["account_id"]])
                    jid=hashlib.sha256(raw.encode()).hexdigest()[:32]
                    self.db.execute(
                        "INSERT OR IGNORE INTO jobs(id,day,slot,due_utc,account_id,group_id,creative_id,caption_id,manifest_sha256,status) "
                        "VALUES(?,?,?,?,?,?,?,?,?, 'PLANNED')",
                        (jid,target_day.isoformat(),slot,due,cfg["account_id"],gid,creative,caption,manifest_digest))
                    results.append(jid)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return results

    def summary(self):
        return [dict(r) for r in self.db.execute(
            "SELECT id,day,slot,due_utc,account_id,group_id,creative_id,caption_id,manifest_sha256,status,operation_id "
            "FROM jobs ORDER BY due_utc,id")]

    def claim_one(self,now=None,grace_minutes=20):
        """Não reclama nada se uma tentativa anterior precisar de revisão humana."""
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("now precisa timezone.")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            pending=self.db.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE status='NEEDS_REVIEW'").fetchone()["n"]
            if pending:
                self.db.commit()
                return None
            # Faltas não devem ser executadas horas depois do previsto.
            expired=self.db.execute(
                "SELECT id FROM jobs WHERE status='PLANNED' AND due_utc < ?",
                ((now-timedelta(minutes=grace_minutes)).isoformat(),)).fetchall()
            for item in expired:
                self.db.execute("UPDATE jobs SET status='MISSED' WHERE id=?",(item["id"],))
                self._event(item["id"],"MISSED","MISSED_WINDOW")
            item=self.db.execute(
                "SELECT * FROM jobs WHERE status='PLANNED' AND due_utc <= ? "
                "ORDER BY due_utc,id LIMIT 1",(now.isoformat(),)).fetchone()
            if not item:
                self.db.commit()
                return None
            # Marcar incerto ANTES de transferir controle ao navegador/publicador.
            self.db.execute("UPDATE jobs SET status='NEEDS_REVIEW',checked_at=? WHERE id=?",
                            (_now(),item["id"]))
            self._event(item["id"],"CLAIMED_UNCERTAIN","NO_AUTORETRY")
            self.db.commit()
            return dict(item)
        except Exception:
            self.db.rollback()
            raise

    def annotate(self,job_id,operation_id=None,code="SUBMITTED_UNVERIFIED"):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            item=self.db.execute("SELECT status FROM jobs WHERE id=?",(job_id,)).fetchone()
            if not item or item["status"]!="NEEDS_REVIEW":
                raise ValueError("Job não está aguardando revisão.")
            self.db.execute("UPDATE jobs SET operation_id=? WHERE id=?",(operation_id,job_id))
            self._event(job_id,"DISPATCH_RESULT",re.sub(r"[^A-Z0-9_]","",code.upper())[:60])
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def resolve(self,job_id,status,reason):
        """Apenas revisão manual; nunca muda uma pendência para PLANNED."""
        if status not in {"VERIFIED_EXTERNALLY","SKIPPED"} or not isinstance(reason,str) or len(reason.strip())<8:
            raise ValueError("Revisão manual deve informar status e justificativa.")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result=self.db.execute(
                "UPDATE jobs SET status=?,checked_at=? WHERE id=? AND status='NEEDS_REVIEW'",
                (status,_now(),job_id))
            if result.rowcount!=1:
                raise ValueError("Job não está aguardando revisão.")
            # Não armazenar a justificativa textual, somente prova de que foi fornecida.
            digest=hashlib.sha256(reason.strip().encode()).hexdigest()[:12]
            self._event(job_id,"MANUAL_RESOLUTION",status+"_"+digest)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def note_preflight(self,job_id,code):
        """Avisa o motivo da não execução. Não reclama nem reenvia a tarefa."""
        permitted={"SERVER_NOT_READY","STALE_SERVER","ACCOUNT_NOT_READY",
                   "PREVIOUS_POST_NOT_CLEARED","PREFLIGHT_UNKNOWN"}
        safe=code if code in permitted else "PREFLIGHT_UNKNOWN"
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self._event(job_id,"PREFLIGHT_FAILED",safe)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def events(self,job_id):
        return [dict(x) for x in self.db.execute(
            "SELECT at,event,code FROM events WHERE job_id=? ORDER BY id",(job_id,))]
