
# ml/train_models.py
# Phase 4 — ML Models (Updated with Dynamic Clustering)
# Run: python ml/train_models.py

import duckdb, joblib, os, re, warnings
import pandas as pd
import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import (LabelEncoder, OneHotEncoder,
                                   StandardScaler, normalize)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, cross_val_score
from sklearn.model_selection import StratifiedKFold
from dotenv import load_dotenv
load_dotenv()
warnings.filterwarnings("ignore")

DB_PATH    = os.getenv("DB_PATH",    "database/call_quality.duckdb")
MODEL_PATH = os.getenv("MODEL_PATH", "ml/models")
os.makedirs(MODEL_PATH, exist_ok=True)

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def find_best_k(X_norm, max_k=10):
    best_k, best_score = 2, -1
    for k in range(2, min(max_k, len(X_norm)//3)+1):
        km  = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbl = km.fit_predict(X_norm)
        if len(set(lbl)) < 2: continue
        sil = silhouette_score(X_norm, lbl,
                               sample_size=min(500, len(X_norm)))
        if sil > best_score:
            best_score, best_k = sil, k
    return best_k, best_score

def train_all():
    con = duckdb.connect(DB_PATH)
    df  = con.execute("""
        SELECT t.contact_id, t.agent_text, t.customer_text,
               t.full_text, t.agent_word_count,
               t.customer_word_count, t.talk_ratio,
               c.campaign_name, c.total_duration_sec,
               c.agent_seconds, c.in_queue_seconds,
               c.hold_seconds, c.hold_count, c.acw_seconds,
               c.is_abandoned, c.is_outbound,
               c.service_level_flag, c.is_simulated,
               cs.overall_score, cs.sentiment_agent,
               cs.sentiment_customer, cs.resolution
        FROM transcripts t
        JOIN calls c         ON t.contact_id = c.contact_id
        JOIN call_summary cs ON t.contact_id = cs.contact_id
    """).fetchdf()
    con.close()

    print(f"Training on {len(df)} calls")
    df["customer_text"] = df["customer_text"].fillna("")
    df["agent_text"]    = df["agent_text"].fillna("")
    df["campaign_name"] = df["campaign_name"].fillna("Unknown")

    # ── MODEL 1: Dynamic Issue Clustering ────────────────────
    tfidf_c = TfidfVectorizer(max_features=500, ngram_range=(1,2),
                               stop_words="english", sublinear_tf=True)
    X_c     = tfidf_c.fit_transform(
                  df["customer_text"].apply(clean_text))
    X_norm  = normalize(X_c)

    best_k, best_sil = find_best_k(X_norm)
    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = km.fit_predict(X_norm)

    feat_names = tfidf_c.get_feature_names_out()
    cluster_names = {}
    for cid in range(best_k):
        top_words = feat_names[km.cluster_centers_[cid]
                               .argsort()[-3:][::-1]]
        cluster_names[cid] = " + ".join(
            w.title() for w in top_words)

    joblib.dump({
        "model":km, "tfidf":tfidf_c,
        "cluster_names":cluster_names,
        "best_k":best_k, "silhouette":best_sil,
        "model_name":"KMeans Dynamic Clustering",
        "trained_on":len(df)
    }, f"{MODEL_PATH}/dynamic_issue_classifier.pkl")
    print(f"Model 1 (Dynamic): {best_k} clusters, "
          f"silhouette={best_sil:.3f}")

    # ── MODEL 2: Resolution Predictor ────────────────────────
    df2 = df[df["resolution"] != "Abandoned"].copy()
    sm  = {"Positive":2,"Neutral":1,"Negative":0}
    df2["sentiment_agent_num"]    = df2["sentiment_agent"].map(sm).fillna(1)
    df2["sentiment_customer_num"] = df2["sentiment_customer"].map(sm).fillna(1)
    df2["sla_met"]   = (df2["service_level_flag"]=="1").astype(int)
    df2["issue_num"] = (df2["resolution"]
                        .map({"Resolved":0,"Escalated":1,
                              "Unresolved":2}).fillna(0))

    NUM_M2  = ["total_duration_sec","agent_seconds","acw_seconds",
               "in_queue_seconds","hold_seconds","hold_count",
               "agent_word_count","customer_word_count","talk_ratio",
               "overall_score","sentiment_agent_num",
               "sentiment_customer_num","sla_met",
               "is_abandoned","is_outbound"]
    scaler  = StandardScaler()
    X_m2_sc = scaler.fit_transform(
                  df2[NUM_M2].fillna(0).astype(float).values)
    le_m2   = LabelEncoder()
    y_m2    = le_m2.fit_transform(df2["resolution"])

    cv      = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    model2  = GradientBoostingClassifier(n_estimators=100,
                                          max_depth=3, random_state=42)
    s2      = cross_val_score(model2, X_m2_sc, y_m2,
                               cv=cv, scoring="accuracy")
    model2.fit(X_m2_sc, y_m2)

    joblib.dump({
        "model":model2, "scaler":scaler, "label_encoder":le_m2,
        "model_name":"Gradient Boosting","cv_accuracy":s2.mean(),
        "classes":list(le_m2.classes_),"feature_cols":NUM_M2,
        "num_cols":NUM_M2, "trained_on":len(df2)
    }, f"{MODEL_PATH}/resolution_predictor.pkl")
    print(f"Model 2 (Resolution): CV={s2.mean()*100:.1f}% | "
          f"Classes: {list(le_m2.classes_)}")

    print("Both models saved!")

if __name__ == "__main__":
    train_all()
