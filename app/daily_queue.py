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
-- v2: conserva a tabela legada e permite repetir um grupo em slots distintos
-- somente se a campanha explicitamente elevar o limite por dia.
CREATE TABLE IF NOT EXISTS jobs_v2 (
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
  UNIQUE(day,slot,group_id)
);
CREATE INDEX IF NOT EXISTS idx_due_v2 ON jobs_v2(status,due_utc);
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
    daily_cap=cfg.get("max_posts_per_group_per_day",1)
    if type(daily_cap) is not int or not 1<=daily_cap<=3:
        raise ValueError("max_posts_per_group_per_day deve ser entre 1 e 3.")
    if daily_cap>1 and cfg.get("allow_repeat_group_per_day") is not True:
        raise ValueError("Repetições no mesmo grupo exigem allow_repeat_group_per_day=true.")
    if cfg.get("allow_repeat_group_per_day") not in (None,False,True):
        raise ValueError("allow_repeat_group_per_day inválido.")
    occupied=set()
    for slot in slots:
        h,m=map(int,slot.split(":"))
        for n in range(max_per_slot):
            minute=h*60+m+10*n
            if minute>=24*60 or minute in occupied:
                raise ValueError("Janelas sobrepostas ou após meia-noite.")
            occupied.add(minute)
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}",str(cfg.get("account_id",""))):
        raise ValueError("Perfil local inválido.")
    if not isinstance(cfg.get("rotation_seed"),str) or len(cfg["rotation_seed"])<12:
        raise ValueError("Defina rotation_seed único e estável.")
    return cfg

def manifest_digest(group_id,creative,caption):
    """Hash de conteúdo aprovado e BYTES das mídias locais; não guarda fotos no DB."""
    snapshots=[]
    for filename in creative.get("files",[]):
        path=Path(filename)
        if not path.is_file() or path.is_symlink():
            snapshots.append("MISSING_OR_SYMLINK")
            continue
        digest=hashlib.sha256()
        with path.open("rb") as stream:
            while data:=stream.read(1024*1024):
                digest.update(data)
        snapshots.append(digest.hexdigest())
    payload=json.dumps({"group_id":group_id,"creative":creative,
                        "caption":caption,"media_digests":snapshots},
                       sort_keys=True,ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def inspect_day_plan(cfg, rows, target_day):
    """Read-only diagnosis: config changes must never rewrite an existing day.

    No paths, captions, group IDs, or account IDs leave this function.
    The result is safe for a public forensic snapshot.
    """
    validate_config(cfg)
    if isinstance(target_day,str):
        target_day=date.fromisoformat(target_day)
    group_ids={group_url(g["url"]).split("/groups/")[1].strip("/")
               for g in cfg["groups"]}
    slots=set(cfg["slots"])
    per_slot=cfg.get("groups_per_slot",1)
    group_cap=cfg.get("max_posts_per_group_per_day",1)
    expected=min(len(slots)*min(per_slot,len(group_ids)),len(group_ids)*group_cap)
    today=[x for x in rows if x.get("day")==target_day.isoformat()]
    errors=set()
    if not today:
        return {"state":"PLAN_EMPTY","day":target_day.isoformat(),
                "planned_jobs":0,"expected_jobs":expected,"codes":[]}
    if len(today)!=expected:
        errors.add("PLAN_COUNT_MISMATCH")
    by_group={}
    by_slot={}
    for job in today:
        group=job.get("group_id")
        slot=job.get("slot")
        if group not in group_ids:
            errors.add("PLAN_GROUP_MISMATCH")
        if job.get("account_id")!=cfg["account_id"]:
            errors.add("PLAN_ACCOUNT_MISMATCH")
        if slot not in slots:
            errors.add("PLAN_SLOT_MISMATCH")
        by_group[group]=by_group.get(group,0)+1
        by_slot[slot]=by_slot.get(slot,0)+1
        try:
            moment=datetime.fromisoformat(job["due_utc"]).astimezone(TIMEZONE)
            if moment.date()!=target_day or slot not in slots:
                errors.add("PLAN_DUE_MISMATCH")
            else:
                minute=moment.hour*60+moment.minute
                hour,minute_base=map(int,slot.split(":"))
                offset=minute-(hour*60+minute_base)
                if moment.second or offset<0 or offset%10 or offset>=per_slot*10:
                    errors.add("PLAN_DUE_MISMATCH")
        except (ValueError,TypeError,KeyError,AttributeError):
            errors.add("PLAN_DUE_MISMATCH")
    if any(n>group_cap for n in by_group.values()):
        errors.add("PLAN_GROUP_LIMIT_EXCEEDED")
    if any(n>per_slot for n in by_slot.values()):
        errors.add("PLAN_SLOT_LIMIT_EXCEEDED")
    return {"state":"PLAN_CONFIG_DRIFT" if errors else "PLAN_MATCH",
            "day":target_day.isoformat(),"planned_jobs":len(today),
            "expected_jobs":expected,"codes":sorted(errors)}


class DailyQueue:
    def __init__(self, database):
        self.path=Path(database)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=5)
        self.db.row_factory=sqlite3.Row
        self.db.executescript(SCHEMA)
        # Importação não destrutiva. Mantém jobs originais para reversão/auditoria.
        self.db.execute(
            "INSERT OR IGNORE INTO jobs_v2 "
            "(id,day,slot,due_utc,account_id,group_id,creative_id,caption_id,manifest_sha256,status,operation_id,checked_at) "
            "SELECT id,day,slot,due_utc,account_id,group_id,creative_id,caption_id,manifest_sha256,status,operation_id,checked_at FROM jobs")
        self.db.commit()

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
        # Pre-approved variants rotate in seeded shuffled decks rather than
        # independent random.choice(), which can over-select one creative.
        # Deterministic replay only for preview; existing jobs are immutable.
        creative_deck=[]
        caption_deck=[]
        last_creative=None
        last_caption=None
        def take_variant(ids,deck,previous):
            if not deck:
                deck.extend(ids)
                rng.shuffle(deck)
                if len(deck)>1 and deck[-1]==previous:
                    deck.insert(0,deck.pop())
            return deck.pop()
        results=[]
        daily_cap=cfg.get("max_posts_per_group_per_day",1)
        counts={group_url(g["url"]).split("/groups/")[1].strip("/"):0 for g in groups}
        self.db.execute("BEGIN IMMEDIATE")
        try:
            # Um dia já planejado é imutável: não adicionar jobs após restart ou edição da configuração.
            previously=self.db.execute(
                "SELECT id FROM jobs_v2 WHERE day=? ORDER BY due_utc,id",
                (target_day.isoformat(),)).fetchall()
            if previously:
                self.db.commit()
                return [row["id"] for row in previously]
            existing=self.db.execute(
                "SELECT group_id,COUNT(*) AS n FROM jobs_v2 WHERE day=? "
                "GROUP BY group_id",(target_day.isoformat(),)).fetchall()
            for item in existing:
                if item["group_id"] in counts:
                    counts[item["group_id"]]=item["n"]
            for slot in sorted(cfg["slots"]):
                available=[g for g in groups
                           if counts[group_url(g["url"]).split("/groups/")[1].strip("/")]<daily_cap]
                rng.shuffle(available)
                # Distribuição justa: grupos menos usados são priorizados, com desempate randômico determinístico.
                available.sort(key=lambda g:counts[group_url(g["url"]).split("/groups/")[1].strip("/")])
                for offset,group in enumerate(available[:cfg.get("groups_per_slot",1)]):
                    gid=group_url(group["url"]).split("/groups/")[1].strip("/")
                    creative=take_variant(creative_ids,creative_deck,last_creative)
                    caption=take_variant(caption_ids,caption_deck,last_caption)
                    last_creative,last_caption=creative,caption
                    creative_item=next(x for x in cfg["creatives"] if x["id"]==creative)
                    caption_item=next(x for x in cfg["captions"] if x["id"]==caption)
                    digest=manifest_digest(gid,creative_item,caption_item)
                    time_local=datetime.combine(target_day,datetime.strptime(slot,"%H:%M").time(),tzinfo=TIMEZONE)
                    due=(time_local+timedelta(minutes=offset*10)).astimezone(timezone.utc).isoformat()
                    raw="|".join([target_day.isoformat(),slot,gid,cfg["account_id"]])
                    jid=hashlib.sha256(raw.encode()).hexdigest()[:32]
                    result=self.db.execute(
                        "INSERT OR IGNORE INTO jobs_v2"
                        "(id,day,slot,due_utc,account_id,group_id,creative_id,caption_id,manifest_sha256,status) "
                        "VALUES(?,?,?,?,?,?,?,?,?, 'PLANNED')",
                        (jid,target_day.isoformat(),slot,due,cfg["account_id"],gid,creative,caption,digest))
                    if result.rowcount:
                        counts[gid]+=1
                    results.append(jid)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return results

    def summary(self):
        return [dict(r) for r in self.db.execute(
            "SELECT id,day,slot,due_utc,account_id,group_id,creative_id,caption_id,manifest_sha256,status,operation_id "
            "FROM jobs_v2 ORDER BY due_utc,id")]

    def expire_missed(self,now=None,grace_minutes=20):
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("now precisa timezone.")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            expired=self.db.execute(
                "SELECT id FROM jobs_v2 WHERE status='PLANNED' AND due_utc < ?",
                ((now-timedelta(minutes=grace_minutes)).isoformat(),)).fetchall()
            for item in expired:
                self.db.execute("UPDATE jobs_v2 SET status='MISSED' WHERE id=?",(item["id"],))
                self._event(item["id"],"MISSED","MISSED_WINDOW")
            self.db.commit()
            return len(expired)
        except Exception:
            self.db.rollback()
            raise

    def claim_one(self,now=None,grace_minutes=20):
        """Não reclama nada se uma tentativa anterior precisar de revisão humana."""
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("now precisa timezone.")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            pending=self.db.execute(
                "SELECT COUNT(*) AS n FROM jobs_v2 WHERE status='NEEDS_REVIEW'").fetchone()["n"]
            if pending:
                self.db.commit()
                return None
            # Faltas não devem ser executadas horas depois do previsto.
            expired=self.db.execute(
                "SELECT id FROM jobs_v2 WHERE status='PLANNED' AND due_utc < ?",
                ((now-timedelta(minutes=grace_minutes)).isoformat(),)).fetchall()
            for item in expired:
                self.db.execute("UPDATE jobs_v2 SET status='MISSED' WHERE id=?",(item["id"],))
                self._event(item["id"],"MISSED","MISSED_WINDOW")
            item=self.db.execute(
                "SELECT * FROM jobs_v2 WHERE status='PLANNED' AND due_utc <= ? "
                "ORDER BY due_utc,id LIMIT 1",(now.isoformat(),)).fetchone()
            if not item:
                self.db.commit()
                return None
            # Marcar incerto ANTES de transferir controle ao navegador/publicador.
            self.db.execute("UPDATE jobs_v2 SET status='NEEDS_REVIEW',checked_at=? WHERE id=?",
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
            item=self.db.execute("SELECT status FROM jobs_v2 WHERE id=?",(job_id,)).fetchone()
            if not item or item["status"]!="NEEDS_REVIEW":
                raise ValueError("Job não está aguardando revisão.")
            self.db.execute("UPDATE jobs_v2 SET operation_id=? WHERE id=?",(operation_id,job_id))
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
                "UPDATE jobs_v2 SET status=?,checked_at=? WHERE id=? AND status='NEEDS_REVIEW'",
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
        permitted={"SERVER_NOT_READY","STALE_SERVER","ACCOUNT_NOT_READY","NETWORK_NOT_READY",
                   "PREVIOUS_POST_NOT_CLEARED","PREFLIGHT_UNKNOWN",
                   "CONFIG_OR_MEDIA_CHANGED","CONFIG_CHANGED","CAPTION_INVALID",
                   "MEDIA_MANIFEST_INVALID","MEDIA_MISSING_OR_SYMLINK",
                   "MEDIA_SIZE_INVALID","CONTENT_CHECK_FAILED"}
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
