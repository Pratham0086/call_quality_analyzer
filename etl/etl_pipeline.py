
# etl/etl_pipeline.py
# Phase 2 — ETL Pipeline
# Extracts raw JSON files, validates, loads into DuckDB
# Run: python etl/etl_pipeline.py

import duckdb, json, uuid, os, re
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

DB_PATH    = os.getenv("DB_PATH", "database/call_quality.duckdb")
CALLS_PATH = os.getenv("RAW_DATA_PATH", "data/raw") + "/Call Details 1/Call Details"
TRANS_PATH = os.getenv("RAW_DATA_PATH", "data/raw") + "/Call Transcripts 1/Call Transcripts"

def log_issue(con, cid, field, itype, desc, sev):
    con.execute("""
        INSERT OR IGNORE INTO data_quality_log VALUES (?,?,?,?,?,?,?)
    """, [str(uuid.uuid4()), cid, field, itype, desc, sev, datetime.now()])

def safe_float(val, default=0.0):
    try:    return round(float(val), 3)
    except: return default

def parse_ts(ts_str):
    if not ts_str: return None
    try:
        return datetime.fromisoformat(
            str(ts_str).replace("Z","+00:00")
        ).replace(tzinfo=None)
    except: return None

def run_etl():
    con = duckdb.connect(DB_PATH)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ETL Starting...")

    call_files = [f for f in os.listdir(CALLS_PATH) if f.endswith(".json")]
    agent_seen = {}
    c_loaded   = 0

    for fname in sorted(call_files):
        with open(f"{CALLS_PATH}/{fname}", "r") as f:
            raw = json.load(f)
        if isinstance(raw, list): raw = raw[0]

        cid = raw.get("contactId")
        if not cid: continue
        if con.execute("SELECT 1 FROM calls WHERE contact_id=?",
                       [cid]).fetchone(): continue

        total_dur = safe_float(raw.get("totalDurationSeconds", 0))
        hold_sec  = safe_float(raw.get("holdSeconds", 0))
        queue_sec = safe_float(raw.get("inQueueSeconds", 0))

        if total_dur > 86400:
            log_issue(con,cid,"totalDurationSeconds","outlier",
                      f"Impossible duration:{total_dur}s","high")
        if hold_sec > 1800:
            log_issue(con,cid,"holdSeconds","outlier",
                      f"Long hold:{hold_sec}s>30min","high")
        if queue_sec > 600:
            log_issue(con,cid,"inQueueSeconds","outlier",
                      f"Long queue:{queue_sec}s>10min","medium")
        if total_dur < 30 and not raw.get("abandoned", False):
            log_issue(con,cid,"totalDurationSeconds","outlier",
                      f"Very short:{total_dur}s","low")

        ts = parse_ts(raw.get("contactStart",""))
        con.execute("""
            INSERT OR IGNORE INTO calls VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
            cid, raw.get("agentId"),
            raw.get("campaignName","Unknown"),
            raw.get("skillName","Unknown"),
            raw.get("teamName","Unknown"),
            raw.get("firstName",""),
            raw.get("lastName",""),
            str(raw.get("fromAddr","")),
            str(raw.get("toAddr","")),
            ts, total_dur,
            safe_float(raw.get("agentSeconds",0)),
            queue_sec, hold_sec,
            safe_float(raw.get("ACWSeconds",0)),
            int(raw.get("holdCount",0)),
            bool(raw.get("abandoned",False)),
            bool(raw.get("isOutbound",False)),
            str(raw.get("serviceLevelFlag","0")),
            raw.get("state","Unknown"),
            raw.get("mediaTypeName","Call"),
            False, datetime.now()
        ])

        aid = raw.get("agentId")
        if aid and aid not in agent_seen:
            agent_seen[aid] = {
                "team": raw.get("teamName","Unknown"),
                "skill": raw.get("skillName","Unknown"),
            }
        c_loaded += 1

    trans_files = [f for f in os.listdir(TRANS_PATH) if f.endswith(".json")]
    t_loaded    = 0

    for fname in sorted(trans_files):
        with open(f"{TRANS_PATH}/{fname}", "r") as f:
            raw = json.load(f)
        try:
            keys = list(raw.keys())
            if len(keys)==1 and isinstance(raw[keys[0]], dict):
                cid  = int(keys[0])
                conv = raw[keys[0]]
            else:
                cid  = int(fname.replace(".json",""))
                conv = raw
        except: continue

        if not con.execute("SELECT 1 FROM calls WHERE contact_id=?",
                           [cid]).fetchone(): continue
        if con.execute("SELECT 1 FROM transcripts WHERE contact_id=?",
                       [cid]).fetchone(): continue

        at = str(conv.get("agent_conversation","")    or "")
        ct = str(conv.get("customer_conversation","") or "")
        aw = len(at.split())
        cw = len(ct.split())
        tw = aw + cw
        tr = round(aw/tw, 3) if tw > 0 else 0.0

        if len(at) < 20:
            log_issue(con,cid,"agent_text","missing",
                      "Agent text too short","high")
        if len(ct) < 10:
            log_issue(con,cid,"customer_text","missing",
                      "Customer text too short","medium")
        if tr > 0.88:
            log_issue(con,cid,"talk_ratio","outlier",
                      f"Agent monologue:{tr*100:.0f}%","low")
        if tr < 0.25 and tw > 50:
            log_issue(con,cid,"talk_ratio","outlier",
                      f"Silent agent:{tr*100:.0f}%","medium")

        con.execute("""
            INSERT OR IGNORE INTO transcripts VALUES (?,?,?,?,?,?,?,?,?)
        """, [str(uuid.uuid4()), cid, at, ct,
              f"{at} {ct}".strip(), aw, cw, tr, datetime.now()])
        t_loaded += 1

    for aid, info in agent_seen.items():
        stats = con.execute("""
            SELECT COUNT(*), AVG(total_duration_sec), MAX(contact_start)
            FROM calls WHERE agent_id=?
        """, [aid]).fetchone()
        con.execute("""
            INSERT OR REPLACE INTO agents VALUES (?,?,?,?,?,?,?,?)
        """, [int(aid), info["team"], info["skill"],
              int(stats[0] or 0), 0.0,
              round(float(stats[1] or 0), 1),
              stats[2], datetime.now()])

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ETL Done!")
    print(f"  Calls loaded      : {c_loaded}")
    print(f"  Transcripts loaded: {t_loaded}")
    con.close()

if __name__ == "__main__":
    run_etl()
