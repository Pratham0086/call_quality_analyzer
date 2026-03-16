
# scripts/setup_database.py
# Creates all 8 tables in DuckDB
# Run ONCE: python scripts/setup_database.py

import duckdb, os, uuid
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "database/call_quality.duckdb")
os.makedirs("database", exist_ok=True)

con = duckdb.connect(DB_PATH)
print("Creating tables...")

con.execute("""CREATE TABLE IF NOT EXISTS calls (
    contact_id BIGINT PRIMARY KEY, agent_id BIGINT,
    campaign_name VARCHAR, skill_name VARCHAR, team_name VARCHAR,
    first_name VARCHAR, last_name VARCHAR,
    from_addr VARCHAR, to_addr VARCHAR, contact_start TIMESTAMP,
    total_duration_sec FLOAT, agent_seconds FLOAT,
    in_queue_seconds FLOAT, hold_seconds FLOAT, acw_seconds FLOAT,
    hold_count INTEGER, is_abandoned BOOLEAN DEFAULT FALSE,
    is_outbound BOOLEAN DEFAULT FALSE, service_level_flag VARCHAR,
    state VARCHAR, media_type_name VARCHAR DEFAULT 'Call',
    is_simulated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

con.execute("""CREATE TABLE IF NOT EXISTS transcripts (
    transcript_id VARCHAR PRIMARY KEY, contact_id BIGINT,
    agent_text TEXT, customer_text TEXT, full_text TEXT,
    agent_word_count INTEGER, customer_word_count INTEGER,
    talk_ratio FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

con.execute("""CREATE TABLE IF NOT EXISTS data_quality_log (
    log_id VARCHAR PRIMARY KEY, contact_id BIGINT,
    field_name VARCHAR, issue_type VARCHAR,
    issue_description TEXT, severity VARCHAR,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

con.execute("""CREATE TABLE IF NOT EXISTS agents (
    agent_id BIGINT PRIMARY KEY, team_name VARCHAR,
    skill_name VARCHAR, total_calls INTEGER DEFAULT 0,
    avg_quality_score FLOAT DEFAULT 0,
    avg_handle_time FLOAT DEFAULT 0,
    last_call_date TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

con.execute("""CREATE TABLE IF NOT EXISTS quality_scores (
    score_id VARCHAR PRIMARY KEY, contact_id BIGINT,
    agent_id BIGINT, section_name VARCHAR, criteria_name VARCHAR,
    score FLOAT, passed BOOLEAN, reasoning TEXT, scored_by VARCHAR,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

con.execute("""CREATE TABLE IF NOT EXISTS qsdd_framework (
    framework_id VARCHAR PRIMARY KEY,
    section_name VARCHAR, criteria_name VARCHAR,
    section_weight FLOAT, criteria_weight FLOAT,
    effective_weight FLOAT, enabled BOOLEAN DEFAULT TRUE,
    what_to_check TEXT, when_to_check TEXT,
    good_example TEXT, bad_example TEXT, scoring_method VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

con.execute("""CREATE TABLE IF NOT EXISTS call_summary (
    contact_id BIGINT PRIMARY KEY, issue_category VARCHAR,
    issue_description TEXT, resolution VARCHAR,
    sentiment_agent VARCHAR, sentiment_customer VARCHAR,
    overall_score FLOAT, key_moments TEXT,
    ai_recommendation TEXT, pred_issue_category VARCHAR,
    pred_resolution VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

con.execute("""CREATE TABLE IF NOT EXISTS ai_summary (
    contact_id BIGINT PRIMARY KEY, agent_id BIGINT,
    summary TEXT, strengths TEXT, improvements TEXT,
    failed_criteria TEXT, model_name VARCHAR, version VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

tables = con.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema='main' ORDER BY table_name
""").fetchall()

print(f"Done! {len(tables)} tables created:")
for (t,) in tables:
    print(f"  → {t}")
con.close()
