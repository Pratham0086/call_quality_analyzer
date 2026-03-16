
# simulator/data_simulator.py
# Run: python simulator/data_simulator.py
# Generates new calls every 60 seconds + scores them

import random, time, uuid, duckdb, json, re, os
from datetime import datetime, timedelta
from textblob import TextBlob
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "database/call_quality.duckdb")

# Import scoring engine
import sys
sys.path.append(".")
from scripts.scoring_engine import score_one_call, generate_call

def run_simulator(batches=999, calls_per_batch=5, interval=60):
    print(f"Simulator starting: {batches} batches, "
          f"{calls_per_batch} calls/batch, {interval}s interval")
    total = 0
    for batch in range(batches):
        print(f"Batch {batch+1}/{batches} — {datetime.now().strftime('%H:%M:%S')}")
        for _ in range(calls_per_batch):
            data = generate_call()
            con  = duckdb.connect(DB_PATH)
            raw  = data["call"]
            t    = data["transcript"]
            cid  = raw["contactId"]
            if con.execute("SELECT 1 FROM calls WHERE contact_id=?",
                           [cid]).fetchone():
                con.close()
                continue
            try:
                ts = datetime.fromisoformat(
                    raw["contactStart"].replace("Z","+00:00")
                ).replace(tzinfo=None)
            except:
                ts = datetime.now()
            at = str(t["agent_text"]    or "")
            ct = str(t["customer_text"] or "")
            aw = len(at.split())
            cw = len(ct.split())
            tr = round(aw/(aw+cw),3) if (aw+cw)>0 else 0.0
            con.execute("""
                INSERT OR IGNORE INTO calls VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, [cid,raw["agentId"],raw["campaignName"],
                  raw["skillName"],raw["teamName"],
                  raw["firstName"],raw["lastName"],
                  str(raw["fromAddr"]),str(raw["toAddr"]),
                  ts,float(raw["totalDurationSeconds"]),
                  float(raw["agentSeconds"]),
                  float(raw["inQueueSeconds"]),
                  float(raw["holdSeconds"]),float(raw["ACWSeconds"]),
                  int(raw["holdCount"]),bool(raw["abandoned"]),
                  bool(raw["isOutbound"]),str(raw["serviceLevelFlag"]),
                  raw["state"],raw["mediaTypeName"],True,datetime.now()])
            con.execute("""
                INSERT OR IGNORE INTO transcripts VALUES (?,?,?,?,?,?,?,?,?)
            """, [str(uuid.uuid4()),cid,at,ct,f"{at} {ct}",
                  aw,cw,tr,datetime.now()])
            sc,res,cat = score_one_call(con,cid,raw["agentId"],
                                        at,ct,
                                        float(raw["totalDurationSeconds"]),
                                        bool(raw["abandoned"]))
            con.close()
            total += 1
            print(f"  Added call {cid} | Score:{sc}% | {res}")
        if batch < batches-1:
            time.sleep(interval)
    print(f"Done! {total} calls generated")

if __name__ == "__main__":
    run_simulator()
