# 📞 AI-Powered Call Quality Analyzer

> KrenexAI Hackathon Project

## 🎯 Problem Statement

Call center managers receive thousands of calls daily but have no way
to automatically analyze agent quality, customer issues, or call outcomes
at scale. This system uses AI to automatically score, classify, and
summarize every call.

## 🏗️ Architecture
```
Raw JSON Files → ETL Pipeline → DuckDB → AI Scoring → ML Models
                                   ↓
                            GenAI RAG Agent (ChromaDB + LangChain)
                                   ↓
                         Streamlit Dashboard (Manager UI)
```

## 👥 Team & Division of Work

| Person | Role | Responsibilities |
|--------|------|-----------------|
| Data + ML Engineer | Data Pipeline | ETL, Database, Quality Scoring, ML Models, Simulator |
| GenAI Engineer | AI/RAG | ChromaDB, LangChain RAG, AI Summaries, Chat Interface |

## 📁 Project Structure
```
call_quality_analyzer/
├── data/
│   ├── raw/                    # Company JSON files (gitignored)
│   └── processed/              # Clean CSV exports
├── database/
│   └── call_quality.duckdb     # Main DuckDB database (gitignored)
├── etl/
│   └── etl_pipeline.py         # ETL: Extract → Transform → Load
├── ml/
│   ├── train_models.py         # ML model training
│   └── models/                 # Saved .pkl model files
├── simulator/
│   └── data_simulator.py       # Live data generator (60s intervals)
├── dashboard/
│   └── dashboard.py            # Streamlit analytics dashboard
├── tools/
│   ├── qsdd_admin.py           # QSDD rule management (GenAI team)
│   ├── db_overview.py          # Database inspector
│   └── create_ai_summary_table.py
├── scripts/
│   └── setup_database.py       # One-time DB schema creation
├── requirements.txt
├── .env.example                # Environment variables template
└── README.md
```

## 🗄️ Database Schema (DuckDB — Medallion Architecture)

### 🥉 Bronze (Raw)
| Table | Description |
|-------|-------------|
| `calls` | Raw call metadata from company JSON files |
| `transcripts` | Full agent + customer conversation text |
| `data_quality_log` | ETL issues: outliers, missing fields |

### 🥈 Silver (Cleaned + Enriched)
| Table | Description |
|-------|-------------|
| `agents` | Agent profiles built from calls data |
| `quality_scores` | 12 QSDD criteria scored per call by AI |
| `qsdd_framework` | Configurable quality rules (editable from UI) |

### 🥇 Gold (Analytics Ready)
| Table | Description |
|-------|-------------|
| `call_summary` | Overall score, resolution, ML predictions |
| `ai_summary` | HuggingFace generated summaries (GenAI team) |

## 🚀 Quick Start
```bash
# 1. Clone
git clone https://github.com/Pratham0086/call_quality_analyzer.git
cd call_quality_analyzer

# 2. Install
pip install -r requirements.txt

# 3. Setup database
python scripts/setup_database.py

# 4. Run ETL (place raw files in data/raw/ first)
python etl/etl_pipeline.py

# 5. Train ML models
python ml/train_models.py

# 6. Generate AI summaries (GenAI team)
python generate_ai_summary_overwrite_hf.py

# 7. Run dashboard
streamlit run dashboard/dashboard.py
```

## 📊 What the System Does

| Component | Technology | Output |
|-----------|-----------|--------|
| ETL Pipeline | Python + DuckDB | Clean structured data |
| Quality Scoring | NLP + Sentiment | 12 QSDD criteria scores |
| Issue Classifier | TF-IDF + Logistic Regression | Auto-tag issue type |
| Resolution Predictor | Gradient Boosting | Predict call outcome |
| RAG Chatbot | ChromaDB + LangChain + HuggingFace | Natural language answers |
| Dashboard | Streamlit + Plotly | Visual analytics |
| Simulator | Python scheduler | New calls every 60s |

## 🔧 Environment Variables

Copy `.env.example` to `.env` and fill in:
```
DB_PATH=database/call_quality.duckdb
RAW_DATA_PATH=data/raw
PROCESSED_PATH=data/processed
MODEL_PATH=ml/models
```
