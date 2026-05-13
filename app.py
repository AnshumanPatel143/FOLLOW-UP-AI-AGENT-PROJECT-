"""
app.py — Finance Co. | FinCredit AI Dashboard
"Quiet Luxury SaaS" redesign — Satoshi + Blue-Indigo + Glassmorphic light sidebar
Author: Anshuman Patel, Finance Manager
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib, json, time
from datetime import datetime
from pathlib import Path

from utils.config import config
from utils.invoice_processor import load_invoices, get_overdue_invoices, get_summary_stats
from utils.logger import follow_up_logger
from agent import run_agent

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Co. · FinCredit AI",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM CSS — "Quiet Luxury SaaS"
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Fonts ─────────────────────────────────────────────────────────────────── */
@import url('https://api.fontshare.com/v2/css?f[]=satoshi@700,600,500,400,300&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Design tokens ─────────────────────────────────────────────────────────── */
:root {
    /* Palette */
    --bg:          #FAF9F6;
    --surface:     #FFFFFF;
    --surface-2:   #F4F3F0;
    --border:      #E8E6E1;
    --border-soft: rgba(0,0,0,0.06);

    /* Text */
    --text-1: #0F172A;
    --text-2: #475569;
    --text-3: #94A3B8;

    /* Accent — Blue → Indigo */
    --blue:    #3B82F6;
    --indigo:  #6366F1;
    --grad:    linear-gradient(135deg, #3B82F6 0%, #6366F1 100%);
    --grad-soft: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(99,102,241,0.08) 100%);

    /* Semantic */
    --green:   #10B981;
    --amber:   #F59E0B;
    --rose:    #F43F5E;
    --violet:  #8B5CF6;

    /* Shadows — multi-layer for depth */
    --shadow-xs: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.03);
    --shadow-lg: 0 10px 15px rgba(0,0,0,0.05), 0 4px 6px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.03);
    --shadow-xl: 0 20px 25px rgba(0,0,0,0.06), 0 8px 10px rgba(0,0,0,0.04), 0 0 0 1px rgba(0,0,0,0.03);
    --shadow-blue: 0 4px 14px rgba(59,130,246,0.22), 0 1px 3px rgba(59,130,246,0.12);

    /* Radius */
    --r-xs: 6px;
    --r-sm: 10px;
    --r-md: 14px;
    --r-lg: 20px;
    --r-xl: 28px;
    --r-full: 999px;
}

/* ── Reset & base ───────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
    font-family: 'Satoshi', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: var(--bg) !important;
    color: var(--text-1) !important;
    -webkit-font-smoothing: antialiased;
}

/* ── Stagger animation ──────────────────────────────────────────────────────── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position:  200% 0; }
}
@keyframes pulse-ring {
    0%   { box-shadow: 0 0 0 0 rgba(59,130,246,0.35); }
    70%  { box-shadow: 0 0 0 8px rgba(59,130,246,0); }
    100% { box-shadow: 0 0 0 0 rgba(59,130,246,0); }
}

.fade-up-1 { animation: fadeUp 0.5s 0.05s both ease-out; }
.fade-up-2 { animation: fadeUp 0.5s 0.12s both ease-out; }
.fade-up-3 { animation: fadeUp 0.5s 0.19s both ease-out; }
.fade-up-4 { animation: fadeUp 0.5s 0.26s both ease-out; }

/* ══ SIDEBAR — Glassmorphic Light ══════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.82) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 20px rgba(0,0,0,0.04) !important;
}
[data-testid="stSidebar"] * { color: var(--text-1) !important; }

/* Sidebar brand */
.sb-brand {
    display: flex; align-items: center; gap: 10px;
    padding: 6px 0 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
}
.sb-brand-icon {
    width: 36px; height: 36px; border-radius: var(--r-sm);
    background: var(--grad); display: flex; align-items: center;
    justify-content: center; font-size: 18px;
    box-shadow: var(--shadow-blue);
}
.sb-brand-text { font-size: 15px; font-weight: 700; color: var(--text-1); }
.sb-brand-sub  { font-size: 11px; color: var(--text-3); font-weight: 500; margin-top: 1px; }

/* Sidebar nav pills */
.sb-nav-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--text-3);
    margin: 0 0 8px; padding: 0 4px;
}

[data-testid="stSidebar"] .stRadio > div { gap: 4px !important; }
[data-testid="stSidebar"] .stRadio label {
    background: transparent !important;
    border-radius: var(--r-sm) !important;
    padding: 10px 14px !important;
    margin: 2px 0 !important;
    border: 1px solid transparent !important;
    cursor: pointer !important;
    transition: all 0.18s ease !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    color: var(--text-2) !important;
    display: flex !important; align-items: center !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--surface-2) !important;
    color: var(--text-1) !important;
    border-color: var(--border) !important;
}
[data-testid="stSidebar"] .stRadio label[data-checked="true"],
[data-testid="stSidebar"] .stRadio input:checked + label {
    background: var(--grad-soft) !important;
    color: var(--blue) !important;
    border-color: rgba(59,130,246,0.2) !important;
    font-weight: 600 !important;
}

/* Sidebar user card */
.sb-user {
    background: var(--surface-2);
    border-radius: var(--r-md);
    border: 1px solid var(--border);
    padding: 12px 14px;
    display: flex; align-items: center; gap: 10px;
    margin-top: 8px;
}
.sb-avatar {
    width: 34px; height: 34px; border-radius: var(--r-full);
    background: var(--grad); display: flex; align-items: center;
    justify-content: center; font-size: 13px; font-weight: 700;
    color: #fff; flex-shrink: 0;
    box-shadow: var(--shadow-blue);
}
.sb-user-name  { font-size: 13px; font-weight: 600; color: var(--text-1); }
.sb-user-role  { font-size: 11px; color: var(--text-3); margin-top: 1px; }

/* Sidebar trust badges */
.sb-trust {
    display: flex; gap: 6px; flex-wrap: wrap;
    padding: 14px 0 0;
    border-top: 1px solid var(--border);
    margin-top: 14px;
}
.sb-badge {
    font-size: 10px; font-weight: 600; color: var(--text-3);
    background: var(--surface-2); border: 1px solid var(--border);
    border-radius: var(--r-full); padding: 3px 8px;
    display: flex; align-items: center; gap: 4px;
}

/* ══ AUTH PAGE ════════════════════════════════════════════════════════════════ */
.auth-bg {
    min-height: 80vh; display: flex; align-items: center; justify-content: center;
    padding: 40px 20px;
}
.auth-card {
    width: 100%; max-width: 420px;
    background: var(--surface);
    border-radius: var(--r-xl);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-xl), 0 0 0 1px rgba(255,255,255,0.8) inset;
    overflow: hidden;
    animation: fadeUp 0.5s ease both;
}
.auth-top {
    background: var(--grad);
    padding: 36px 40px 32px;
    text-align: center; position: relative; overflow: hidden;
}
.auth-top::before {
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 180px; height: 180px; border-radius: 50%;
    background: rgba(255,255,255,0.08);
}
.auth-top::after {
    content: '';
    position: absolute; bottom: -40px; left: -40px;
    width: 120px; height: 120px; border-radius: 50%;
    background: rgba(255,255,255,0.06);
}
.auth-logo-wrap {
    width: 60px; height: 60px; border-radius: var(--r-lg);
    background: rgba(255,255,255,0.18);
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; margin: 0 auto 16px;
    border: 1px solid rgba(255,255,255,0.25);
    position: relative; z-index: 1;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.auth-title { font-size: 22px; font-weight: 700; color: #fff; margin: 0 0 4px; position: relative; z-index: 1; }
.auth-sub   { font-size: 13px; color: rgba(255,255,255,0.72); margin: 0; position: relative; z-index: 1; }
.auth-body  { padding: 28px 36px 36px; }
.auth-section-title {
    font-size: 18px; font-weight: 700; color: var(--text-1);
    margin: 0 0 6px;
}
.auth-section-sub {
    font-size: 13px; color: var(--text-3); margin: 0 0 24px;
}

/* ══ PAGE HEADERS ══════════════════════════════════════════════════════════════ */
.page-head { margin-bottom: 28px; animation: fadeUp 0.4s ease both; }
.page-title {
    font-size: 30px; font-weight: 700; color: var(--text-1);
    letter-spacing: -0.5px; line-height: 1.2; margin: 0 0 4px;
}
.page-sub { font-size: 14px; color: var(--text-2); margin: 0; font-weight: 400; }
.page-divider {
    height: 1px; background: var(--border);
    margin: 20px 0 28px;
}

/* ══ KPI CARDS ══════════════════════════════════════════════════════════════════ */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 28px; }

.kpi {
    background: var(--surface);
    border-radius: var(--r-lg);
    border: 1px solid var(--border);
    padding: 22px 20px 20px;
    box-shadow: var(--shadow-md);
    position: relative; overflow: hidden;
    transition: transform 0.22s ease, box-shadow 0.22s ease;
    cursor: default;
}
.kpi:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-xl);
}
/* Gradient orb in corner */
.kpi::after {
    content: '';
    position: absolute; top: -20px; right: -20px;
    width: 80px; height: 80px; border-radius: 50%;
    opacity: 0.07;
    transition: transform 0.3s ease;
}
.kpi:hover::after { transform: scale(1.2); }
.kpi.k-blue::after   { background: var(--blue); }
.kpi.k-green::after  { background: var(--green); }
.kpi.k-amber::after  { background: var(--amber); }
.kpi.k-rose::after   { background: var(--rose); }

/* Accent line */
.kpi-accent {
    height: 3px; border-radius: var(--r-full);
    margin-bottom: 16px;
}
.k-blue  .kpi-accent { background: var(--grad); }
.k-green .kpi-accent { background: linear-gradient(90deg,#10B981,#34D399); }
.k-amber .kpi-accent { background: linear-gradient(90deg,#F59E0B,#FCD34D); }
.k-rose  .kpi-accent { background: linear-gradient(90deg,#F43F5E,#FB7185); }

.kpi-icon {
    width: 38px; height: 38px; border-radius: var(--r-sm);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; margin-bottom: 14px;
}
.k-blue  .kpi-icon { background: rgba(59,130,246,0.10); }
.k-green .kpi-icon { background: rgba(16,185,129,0.10); }
.k-amber .kpi-icon { background: rgba(245,158,11,0.10); }
.k-rose  .kpi-icon { background: rgba(244,63,94,0.10);  }

.kpi-label {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: var(--text-3); margin-bottom: 4px;
}
.kpi-value {
    font-size: 30px; font-weight: 700; color: var(--text-1);
    line-height: 1.1; letter-spacing: -0.5px; margin-bottom: 4px;
}
.kpi-sub { font-size: 12px; color: var(--text-3); font-weight: 500; }
.kpi-trend {
    display: inline-flex; align-items: center; gap: 3px;
    font-size: 11px; font-weight: 600;
    padding: 2px 7px; border-radius: var(--r-full); margin-top: 6px;
}
.trend-up   { background: rgba(244,63,94,0.10); color: #F43F5E; }
.trend-down { background: rgba(16,185,129,0.10); color: #10B981; }
.trend-neu  { background: rgba(148,163,184,0.12); color: var(--text-3); }

/* ══ SECTION CARDS ══════════════════════════════════════════════════════════════ */
.card {
    background: var(--surface);
    border-radius: var(--r-lg);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-md);
    overflow: hidden;
}
.card-head {
    padding: 18px 22px 14px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
}
.card-title { font-size: 14px; font-weight: 700; color: var(--text-1); margin: 0; }
.card-sub   { font-size: 12px; color: var(--text-3); margin-top: 2px; }
.card-body  { padding: 20px 22px; }

/* ══ STAGE BADGES ════════════════════════════════════════════════════════════════ */
.stage-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: var(--r-full);
    font-size: 11px; font-weight: 700; letter-spacing: 0.03em;
}
.s1 { background: rgba(59,130,246,0.10); color: #2563EB; border: 1px solid rgba(59,130,246,0.2); }
.s2 { background: rgba(245,158,11,0.10); color: #B45309; border: 1px solid rgba(245,158,11,0.2); }
.s3 { background: rgba(244,63,94,0.10);  color: #BE185D; border: 1px solid rgba(244,63,94,0.2); }
.s4 { background: #0F172A; color: #F87171; border: 1px solid rgba(248,113,113,0.3); }

/* Stage stepper */
.stage-stepper { display: flex; gap: 0; margin: 20px 0; }
.stage-step {
    flex: 1; padding: 12px 14px; text-align: center;
    font-size: 11px; font-weight: 700; position: relative;
}
.stage-step:not(:last-child)::after {
    content: ''; position: absolute; right: -1px; top: 50%;
    transform: translateY(-50%); width: 2px; height: 60%;
    background: var(--border);
}
.ss1 { background: rgba(59,130,246,0.07); color: #2563EB; border-radius: var(--r-sm) 0 0 var(--r-sm); }
.ss2 { background: rgba(245,158,11,0.07); color: #B45309; }
.ss3 { background: rgba(244,63,94,0.07);  color: #BE185D; }
.ss4 { background: rgba(15,23,42,0.06);   color: #7F1D1D; border-radius: 0 var(--r-sm) var(--r-sm) 0; }
.stage-step-label { font-size: 10px; font-weight: 500; color: inherit; opacity: 0.7; margin-top: 2px; }

/* ══ INVOICE DETAIL CARD ═════════════════════════════════════════════════════════ */
.inv-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-md);
    padding: 20px 24px;
    display: flex; justify-content: space-between; align-items: flex-start;
    margin: 16px 0;
    transition: box-shadow 0.2s;
}
.inv-card:hover { box-shadow: var(--shadow-lg); }
.inv-id    { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-3); margin-bottom: 3px; }
.inv-name  { font-size: 18px; font-weight: 700; color: var(--text-1); margin-bottom: 3px; }
.inv-meta  { font-size: 12px; color: var(--text-3); }
.inv-amount { font-size: 24px; font-weight: 700; color: var(--text-1); letter-spacing: -0.5px; text-align: right; }
.inv-days  { font-size: 12px; color: var(--text-3); text-align: right; margin-top: 2px; }

/* ══ EMAIL PREVIEW ════════════════════════════════════════════════════════════════ */
.email-client {
    background: var(--surface);
    border-radius: var(--r-lg);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-lg);
    overflow: hidden;
    margin-top: 16px;
}
.email-topbar {
    background: var(--surface-2);
    border-bottom: 1px solid var(--border);
    padding: 10px 16px;
    display: flex; align-items: center; gap: 6px;
}
.email-dot { width: 10px; height: 10px; border-radius: 50%; }
.email-dot.r { background: #FF5F57; } .email-dot.y { background: #FEBC2E; } .email-dot.g { background: #28C840; }
.email-winbar { flex: 1; background: var(--surface); border-radius: var(--r-xs); height: 22px; margin: 0 8px; border: 1px solid var(--border); display: flex; align-items: center; padding: 0 8px; }
.email-url { font-size: 10px; font-family: 'JetBrains Mono', monospace; color: var(--text-3); }
.email-head {
    background: var(--grad);
    padding: 22px 28px 20px;
}
.email-head-to      { font-size: 12px; color: rgba(255,255,255,0.65); font-weight: 600; margin-bottom: 4px; }
.email-head-subject { font-size: 17px; font-weight: 700; color: #fff; line-height: 1.3; }
.email-ai-badge {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.25);
    border-radius: var(--r-full); padding: 3px 10px;
    font-size: 10px; font-weight: 700; color: rgba(255,255,255,0.9);
    margin-top: 10px;
}
.email-body {
    padding: 28px; font-size: 14px; line-height: 1.9;
    white-space: pre-wrap; color: var(--text-1);
    font-family: 'Satoshi', sans-serif;
    border-top: 1px solid var(--border);
}

/* ══ ALERTS ════════════════════════════════════════════════════════════════════════ */
.alert {
    border-radius: var(--r-md); padding: 13px 18px;
    font-size: 13px; font-weight: 500; margin: 12px 0;
    display: flex; align-items: center; gap: 10px;
    border: 1px solid;
}
.alert-ok   { background: rgba(16,185,129,0.08); border-color: rgba(16,185,129,0.2); color: #047857; }
.alert-warn { background: rgba(59,130,246,0.07); border-color: rgba(59,130,246,0.2); color: #1D4ED8; }
.alert-err  { background: rgba(244,63,94,0.07);  border-color: rgba(244,63,94,0.2);  color: #BE123C; }
.alert-icon { font-size: 16px; flex-shrink: 0; }

/* ══ SETTINGS ITEMS ════════════════════════════════════════════════════════════════ */
.setting-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 0; border-bottom: 1px solid var(--border);
}
.setting-row:last-child { border-bottom: none; }
.setting-label { font-size: 13px; font-weight: 500; color: var(--text-1); }
.setting-sub   { font-size: 11px; color: var(--text-3); margin-top: 1px; }
.setting-value { font-size: 12px; font-family: 'JetBrains Mono', monospace; color: var(--text-2); text-align: right; max-width: 55%; word-break: break-all; }
.status-ok  { display: inline-flex; align-items: center; gap: 4px; color: var(--green); font-size: 12px; font-weight: 600; }
.status-err { display: inline-flex; align-items: center; gap: 4px; color: var(--rose);  font-size: 12px; font-weight: 600; }

/* ══ DATAFRAME OVERRIDES ════════════════════════════════════════════════════════════ */
.stDataFrame { border-radius: var(--r-md) !important; overflow: hidden !important; border: 1px solid var(--border) !important; }
[data-testid="stDataFrame"] { background: var(--surface) !important; }
[data-testid="stDataFrame"] * { color: var(--text-1) !important; font-family: 'Satoshi', sans-serif !important; }
[data-testid="stDataFrame"] thead th { background: var(--surface-2) !important; color: var(--text-2) !important; font-weight: 700 !important; font-size: 12px !important; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border) !important; }
[data-testid="stDataFrame"] tbody tr:hover td { background: rgba(59,130,246,0.04) !important; }
[data-testid="stDataFrame"] td { color: var(--text-1) !important; font-size: 13px !important; border-bottom: 1px solid var(--border) !important; }

/* ══ BUTTONS ════════════════════════════════════════════════════════════════════════ */
.stButton > button {
    font-family: 'Satoshi', sans-serif !important;
    font-weight: 600 !important;
    border-radius: var(--r-sm) !important;
    transition: all 0.18s ease !important;
    letter-spacing: 0.01em !important;
}
.stButton > button[kind="primary"] {
    background: var(--grad) !important;
    border: none !important; color: #fff !important;
    box-shadow: var(--shadow-blue) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(59,130,246,0.35), 0 2px 6px rgba(59,130,246,0.2) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-1) !important;
    box-shadow: var(--shadow-sm) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: var(--surface-2) !important;
    transform: translateY(-1px) !important;
}

/* ══ INPUTS ════════════════════════════════════════════════════════════════════════ */
.stTextInput input, .stSelectbox > div, .stCheckbox label {
    font-family: 'Satoshi', sans-serif !important;
    color: var(--text-1) !important;
}
.stTextInput input {
    border-radius: var(--r-sm) !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow-xs) !important;
    font-size: 14px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextInput input:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
}
.stTextInput input::placeholder {
    color: #9CA3AF !important;
    opacity: 1 !important;
    font-size: 14px !important;
}
.stSelectbox > div {
    border-radius: var(--r-sm) !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
}

/* ══ MISC ══════════════════════════════════════════════════════════════════════════ */
hr { border: none; border-top: 1px solid var(--border) !important; margin: 20px 0 !important; }
.stProgress > div > div { background: var(--grad) !important; border-radius: var(--r-full) !important; }
.stCheckbox label { font-size: 13px !important; color: var(--text-2) !important; font-weight: 500 !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# USER STORE
# ══════════════════════════════════════════════════════════════════════════════

USERS_FILE = Path(__file__).parent / "users.json"

def _hash(pw: str) -> str:
    """Hash password with bcrypt (preferred) or PBKDF2 fallback."""
    try:
        import bcrypt
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12)).decode()
    except ImportError:
        import secrets as _sec
        salt = _sec.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 260_000)
        return f"pbkdf2${salt}${dk.hex()}"

def _verify(pw: str, stored: str) -> bool:
    """Verify password against bcrypt, pbkdf2, OR legacy sha256 hash."""
    if stored.startswith("$2"):           # bcrypt
        try:
            import bcrypt
            return bcrypt.checkpw(pw.encode(), stored.encode())
        except ImportError:
            return False
    if stored.startswith("pbkdf2$"):      # pbkdf2
        _, salt, dk_hex = stored.split("$", 2)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 260_000)
        import secrets as _sec
        return _sec.compare_digest(dk.hex(), dk_hex)
    # Legacy plain sha256 — allow login, then upgrade hash
    import secrets as _sec
    return _sec.compare_digest(hashlib.sha256(pw.encode()).hexdigest(), stored)

def _load_users() -> dict:
    if USERS_FILE.exists():
        try: return json.loads(USERS_FILE.read_text())
        except: pass
    users = {
        config.APP_USERNAME: {
            "password_hash": _hash(config.APP_PASSWORD),
            "role": "admin", "full_name": "Anshuman Patel",
            "created_at": datetime.utcnow().isoformat(),
        }
    }
    USERS_FILE.write_text(json.dumps(users, indent=2))
    return users

def _save_users(u: dict): USERS_FILE.write_text(json.dumps(u, indent=2))
def user_exists(u: str) -> bool: return u in _load_users()

def authenticate(username: str, password: str) -> bool:
    users = _load_users()
    u = users.get(username)
    if not u:
        return False
    stored = u["password_hash"]
    if not _verify(password, stored):
        return False
    # Silently upgrade legacy sha256 hash to bcrypt on successful login
    if not (stored.startswith("$2") or stored.startswith("pbkdf2$")):
        users[username]["password_hash"] = _hash(password)
        _save_users(users)
    return True

def register_user(username: str, password: str, full_name: str) -> tuple[bool, str]:
    username = username.strip().lower()
    if len(username) < 3: return False, "Username must be at least 3 characters."
    if len(password) < 6: return False, "Password must be at least 6 characters."
    if user_exists(username): return False, f"Username '{username}' is already taken."
    users = _load_users()
    users[username] = {"password_hash": _hash(password), "role": "viewer",
                       "full_name": full_name.strip() or username.title(),
                       "created_at": datetime.utcnow().isoformat()}
    _save_users(users); return True, ""

def get_user_info(u: str) -> dict: return _load_users().get(u, {})


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGE
# ══════════════════════════════════════════════════════════════════════════════

def auth_page():
    if "auth_tab" not in st.session_state:
        st.session_state["auth_tab"] = "login"

    st.markdown("""
    <div class="auth-card" style="max-width:420px;margin:40px auto 0">
        <div class="auth-top">
            <div class="auth-logo-wrap">💳</div>
            <div class="auth-title">Finance Co.</div>
            <div class="auth-sub">FinCredit AI — Intelligent credit automation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        tc = st.columns(2)
        with tc[0]:
            if st.button("Sign In", type="primary" if st.session_state["auth_tab"]=="login" else "secondary", use_container_width=True):
                st.session_state["auth_tab"] = "login"; st.rerun()
        with tc[1]:
            if st.button("Register", type="primary" if st.session_state["auth_tab"]=="register" else "secondary", use_container_width=True):
                st.session_state["auth_tab"] = "register"; st.rerun()
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        if st.session_state["auth_tab"] == "login":
            st.markdown('<div class="auth-section-title">Welcome back</div><div class="auth-section-sub">Sign in to your account to continue</div>', unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Enter your username", key="lu")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="lp")
            if st.button("Sign In →", type="primary", use_container_width=True):
                if not username or not password:
                    st.markdown('<div class="alert alert-err"><span class="alert-icon">⚠️</span> Please enter both username and password.</div>', unsafe_allow_html=True)
                elif authenticate(username.strip().lower(), password):
                    info = get_user_info(username.strip().lower())
                    st.session_state.update({
                        "authenticated": True,
                        "username": username.strip().lower(),
                        "full_name": info.get("full_name", "Anshuman Patel"),
                        "role": info.get("role", "viewer"),
                    })
                    st.rerun()
                else:
                    st.markdown('<div class="alert alert-err"><span class="alert-icon">🔒</span> Incorrect username or password.</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;margin-top:14px;font-size:12px;color:var(--text-3)">Default: <code>admin</code> / <code>changeme123</code></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="auth-section-title">Create account</div><div class="auth-section-sub">Join Finance Co. FinCredit AI platform</div>', unsafe_allow_html=True)
            full_name = st.text_input("Full Name", placeholder="e.g. Anshuman Patel", key="rn")
            new_user  = st.text_input("Username",  placeholder="Choose a username (min 3 chars)", key="ru")
            new_pw    = st.text_input("Password",  type="password", placeholder="Min 6 characters", key="rp")
            new_pw2   = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="rp2")
            if st.button("Create Account →", type="primary", use_container_width=True):
                if not all([full_name, new_user, new_pw]):
                    st.markdown('<div class="alert alert-err"><span class="alert-icon">⚠️</span> Please fill in all fields.</div>', unsafe_allow_html=True)
                elif new_pw != new_pw2:
                    st.markdown('<div class="alert alert-err"><span class="alert-icon">⚠️</span> Passwords do not match.</div>', unsafe_allow_html=True)
                else:
                    ok, err = register_user(new_user, new_pw, full_name)
                    if ok:
                        st.markdown(f'<div class="alert alert-ok"><span class="alert-icon">✅</span> Account created for <b>{full_name}</b>! Signing you in…</div>', unsafe_allow_html=True)
                        st.session_state["auth_tab"] = "login"; st.rerun()
                    else:
                        st.markdown(f'<div class="alert alert-err"><span class="alert-icon">⚠️</span> {err}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    full_name = st.session_state.get("full_name", "Anshuman Patel")
    role      = st.session_state.get("role", "viewer")
    initials  = "".join(p[0].upper() for p in full_name.split()[:2])

    with st.sidebar:
        st.markdown(f"""
        <div class="sb-brand">
            <div class="sb-brand-icon">💳</div>
            <div>
                <div class="sb-brand-text">Finance Co.</div>
                <div class="sb-brand-sub">FinCredit AI</div>
            </div>
        </div>
        <div class="sb-nav-label">Navigation</div>
        """, unsafe_allow_html=True)

        page = st.radio("nav", [
            "📊  Dashboard",
            "🤖  AI Email Generator",
            "📋  Audit Log",
            "⚙️  Settings",
        ], label_visibility="collapsed")

        st.markdown(f"""
        <div class="sb-user" style="margin-top:24px">
            <div class="sb-avatar">{initials}</div>
            <div>
                <div class="sb-user-name">{full_name}</div>
                <div class="sb-user-role">Finance Manager · {role.title()}</div>
            </div>
        </div>
        <div class="sb-trust">
            <div class="sb-badge">🔒 Secure</div>
            <div class="sb-badge">🤖 OpenAI</div>
            <div class="sb-badge">✅ GDPR</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            for k in ["authenticated","username","full_name","role","auth_tab"]:
                st.session_state.pop(k, None)
            st.rerun()

    return page.split("  ", 1)[1].strip()


# ══════════════════════════════════════════════════════════════════════════════
# CHART DEFAULTS — clean, readable, on-brand
# ══════════════════════════════════════════════════════════════════════════════

CHART = dict(
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    font=dict(family="Satoshi, sans-serif", color="#0F172A", size=12),
    title_font=dict(size=14, color="#0F172A", family="Satoshi"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                font=dict(color="#475569", size=11)),
    xaxis=dict(tickfont=dict(color="#475569", size=11),
               gridcolor="#F1F5F9", linecolor="#E2E8F0",
               title_font=dict(color="#475569")),
    yaxis=dict(tickfont=dict(color="#475569", size=11),
               gridcolor="#F1F5F9", linecolor="#E2E8F0",
               title_font=dict(color="#475569")),
    margin=dict(l=8, r=8, t=44, b=8),
    height=300,
)

STAGE_COLORS = {
    "Stage 1": "#3B82F6",
    "Stage 2": "#F59E0B",
    "Stage 3": "#F43F5E",
    "Stage 4": "#0F172A",
}


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def page_dashboard():
    st.markdown("""
    <div class="page-head">
        <div class="page-title">Invoice Dashboard</div>
        <div class="page-sub">Good morning, Anshuman — here's your receivables overview for today</div>
    </div>
    """, unsafe_allow_html=True)

    invoices, _ = load_invoices()
    stats  = get_summary_stats(invoices)
    overdue = get_overdue_invoices(invoices)

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "k-blue",  "💼", "Total Invoices",   str(stats["total_invoices"]),
         f"{stats['paid_count']} paid · {stats['pending_count']} pending", "fade-up-1"),
        (c2, "k-rose",  "🔴", "Overdue",           str(stats["overdue_count"]),
         f"Avg {stats['avg_days_overdue']:.0f} days past due", "fade-up-2"),
        (c3, "k-amber", "💰", "Outstanding",
         f"${stats['total_overdue_amount']:,.0f}",
         f"Across {stats['overdue_count']} invoices", "fade-up-3"),
        (c4, "k-green" if stats["by_stage"].get(4,0)==0 else "k-rose",
         "⚠️", "Critical (60+ days)", str(stats["by_stage"].get(4,0)),
         "Stage 4 — Legal warning", "fade-up-4"),
    ]
    for col, cls, icon, label, value, sub, anim in cards:
        with col:
            st.markdown(f"""
            <div class="kpi {cls} {anim}">
                <div class="kpi-accent"></div>
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Stage stepper ─────────────────────────────────────────────────────────
    s = stats["by_stage"]
    st.markdown(f"""
    <div class="card fade-up-2" style="margin:20px 0 0">
        <div class="card-head">
            <div><div class="card-title">Escalation Pipeline</div>
            <div class="card-sub">Invoices grouped by urgency stage</div></div>
        </div>
        <div class="stage-stepper" style="border-radius:0 0 var(--r-lg) var(--r-lg);overflow:hidden">
            <div class="stage-step ss1">
                <div style="font-size:20px;font-weight:800">{s.get(1,0)}</div>
                <div class="stage-step-label">Stage 1 · Friendly</div>
            </div>
            <div class="stage-step ss2">
                <div style="font-size:20px;font-weight:800">{s.get(2,0)}</div>
                <div class="stage-step-label">Stage 2 · Formal</div>
            </div>
            <div class="stage-step ss3">
                <div style="font-size:20px;font-weight:800">{s.get(3,0)}</div>
                <div class="stage-step-label">Stage 3 · Urgent</div>
            </div>
            <div class="stage-step ss4">
                <div style="font-size:20px;font-weight:800">{s.get(4,0)}</div>
                <div class="stage-step-label">Stage 4 · Legal</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    cl, cr = st.columns([1.5, 1])

    with cl:
        if overdue:
            df_c = pd.DataFrame([{
                "Invoice": i.invoice_id, "Client": i.client_name,
                "Amount": int(i.amount), "Days Overdue": i.days_overdue,
                "Stage": f"Stage {i.escalation_stage}",
            } for i in overdue[:20]])
            fig = px.bar(df_c.sort_values("Days Overdue"), x="Days Overdue", y="Invoice",
                         color="Stage", color_discrete_map=STAGE_COLORS,
                         orientation="h", title="Top 20 — Days Overdue",
                         hover_data=["Client","Amount"])
            fig.update_traces(marker_line_width=0)
            fig.update_layout(**CHART)
            st.plotly_chart(fig, use_container_width=True)

    with cr:
        stage_data = {
            f"S{k} {['Friendly','Formal','Urgent','Legal'][k-1]}": v
            for k, v in stats["by_stage"].items() if v > 0
        }
        if stage_data:
            fig2 = go.Figure(go.Pie(
                labels=list(stage_data.keys()),
                values=list(stage_data.values()),
                hole=0.65,
                marker=dict(colors=["#3B82F6","#F59E0B","#F43F5E","#0F172A"],
                            line=dict(color="#FAF9F6", width=3)),
                textfont=dict(color="#0F172A", size=11),
                textinfo="label+value",
            ))
            fig2.update_layout(**{**CHART, "showlegend": False,
                                  "title": dict(text="Stage Distribution",
                                                font=dict(size=14,color="#0F172A"))})
            # Add total annotation
            total_overdue = sum(stage_data.values())
            fig2.add_annotation(
                text=f"<b>{total_overdue}</b><br><span style='font-size:11px'>overdue</span>",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=16, color="#0F172A", family="Satoshi"),
                align="center",
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Invoice table ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="card-head" style="background:var(--surface);border-radius:var(--r-lg) var(--r-lg) 0 0;border:1px solid var(--border);border-bottom:none;margin-top:8px">
        <div><div class="card-title">All Invoices</div>
        <div class="card-sub">Sorted by days overdue — most critical first</div></div>
    </div>
    """, unsafe_allow_html=True)

    status_map = {"overdue": "🔴 Overdue", "paid": "✅ Paid", "pending": "🟡 Pending"}
    df_all = pd.DataFrame([{
        "ID":           i.invoice_id,
        "Client":       i.client_name,
        "Company":      i.company,
        "Amount":       i.amount_formatted,
        "Due Date":     i.due_date.strftime("%d %b %Y"),
        "Status":       status_map.get(i.status, i.status.title()),
        "Days Overdue": i.days_overdue if i.days_overdue > 0 else "—",
        "Stage":        i.escalation_label if i.is_overdue else "—",
    } for i in sorted(invoices, key=lambda x: x.days_overdue, reverse=True)])

    st.dataframe(df_all, use_container_width=True, hide_index=True,
                 column_config={
                     "ID":     st.column_config.TextColumn(width="small"),
                     "Client": st.column_config.TextColumn(width="medium"),
                     "Amount": st.column_config.TextColumn(width="small"),
                 })


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — AI EMAIL GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def page_email_generator():
    st.markdown("""
    <div class="page-head">
        <div class="page-title">AI Email Generator</div>
        <div class="page-sub">Generate personalised, stage-appropriate follow-up emails powered by GPT-4o</div>
    </div>
    """, unsafe_allow_html=True)

    # API status banner
    api_ok = bool(config.OPENAI_API_KEY and not config.OPENAI_API_KEY.startswith("sk-your") and len(config.OPENAI_API_KEY) > 20)
    dbg    = config.debug_info()
    if api_ok:
        st.markdown(f'<div class="alert alert-ok"><span class="alert-icon">🤖</span> <b>OpenAI {config.OPENAI_MODEL}</b> connected — emails generated by AI</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="alert alert-warn"><span class="alert-icon">📝</span> <b>Professional templates active</b> — Add OPENAI_API_KEY to .env for AI generation &nbsp;|&nbsp; .env path: <code>{dbg["env_file_found"]}</code></div>', unsafe_allow_html=True)

    invoices, _ = load_invoices()
    overdue = get_overdue_invoices(invoices)

    if not overdue:
        st.markdown('<div class="alert alert-ok"><span class="alert-icon">🎉</span> No overdue invoices — all accounts are current!</div>', unsafe_allow_html=True)
        return

    # Controls
    ca, cb, cc = st.columns([2.5, 1.5, 1])
    with ca:
        opts = {f"{i.invoice_id} — {i.client_name} · {i.days_overdue}d overdue · Stage {i.escalation_stage}": i for i in overdue}
        sel  = st.selectbox("Select Invoice", list(opts.keys()))
        inv  = opts[sel]
    with cb:
        sender_name = st.text_input("Sender Name", value=st.session_state.get("full_name","Finance Team"))
    with cc:
        dry_run = st.checkbox("Dry Run", value=True, help="Preview without sending via SMTP")

    # Invoice info card
    stage_cls = f"s{inv.escalation_stage}"
    stage_dot = ["🔵","🟡","🔴","⚫"][inv.escalation_stage-1]
    st.markdown(f"""
    <div class="inv-card fade-up-1">
        <div>
            <div class="inv-id">{inv.invoice_id}</div>
            <div class="inv-name">{inv.client_name}</div>
            <div class="inv-meta">{inv.contact_person} &nbsp;·&nbsp; {inv.client_email} &nbsp;·&nbsp; {inv.company}</div>
            <div style="margin-top:10px">
                <span class="stage-badge {stage_cls}">{stage_dot} {inv.escalation_label}</span>
                &nbsp;<span style="font-size:12px;color:var(--text-3)">{inv.days_overdue} days overdue &nbsp;·&nbsp; {inv.previous_reminders} reminder(s) sent</span>
            </div>
        </div>
        <div>
            <div class="inv-amount">{inv.amount_formatted}</div>
            <div class="inv-days">Due {inv.due_date.strftime('%d %b %Y')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    gc, bc = st.columns(2)
    with gc: gen_clicked   = st.button("⚡  Generate Email",  type="primary", use_container_width=True)
    with bc: batch_clicked = st.button("🚀  Run All Overdue", use_container_width=True)

    # Single generate
    if gen_clicked:
        with st.spinner("Generating email…"):
            result = run_agent(dry_run=dry_run, invoice_id_filter=inv.invoice_id, sender_name=sender_name)

        if result.get("error"):
            st.markdown(f'<div class="alert alert-err"><span class="alert-icon">❌</span> {result["error"]}</div>', unsafe_allow_html=True)
        elif result.get("results"):
            r      = result["results"][0]
            status = r["status"]
            model  = r.get("model_used","mock")
            ai_tag = "🤖 AI Generated" if "mock" not in model else ("📝 Template (API Fallback)" if "fallback" in model else "📝 Template")

            if status in ("sent","dry_run"):
                mode = "Sent ✉️" if status == "sent" else "Ready · Dry Run"
                st.markdown(f'<div class="alert alert-ok"><span class="alert-icon">✅</span> Email {mode} &nbsp;·&nbsp; {ai_tag}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert alert-warn"><span class="alert-icon">⚠️</span> SMTP failed — email generated below &nbsp;·&nbsp; {ai_tag}</div>', unsafe_allow_html=True)

            subject = r.get("subject","")
            body    = r.get("body","")
            if subject and body and "[Generation Failed]" not in subject:
                st.markdown(f"""
                <div class="email-client">
                    <div class="email-topbar">
                        <div class="email-dot r"></div>
                        <div class="email-dot y"></div>
                        <div class="email-dot g"></div>
                        <div class="email-winbar"><span class="email-url">📧 &nbsp; New Message — Finance Co. Credit Control</span></div>
                    </div>
                    <div class="email-head">
                        <div class="email-head-to">To: {inv.client_email}</div>
                        <div class="email-head-subject">{subject}</div>
                        <div class="email-ai-badge">✨ {ai_tag}</div>
                    </div>
                    <div class="email-body">{body}</div>
                </div>
                """, unsafe_allow_html=True)

    # Batch run
    if batch_clicked:
        bar = st.progress(0, text="Initialising batch run…")
        result = run_agent(dry_run=dry_run, sender_name=sender_name)
        total  = result.get("total_processed", 0)
        ok     = result.get("sent",0) + result.get("dry_run",0)
        failed = result.get("failed",0)
        bar.progress(1.0, text=f"Done — {ok}/{total} emails processed")
        st.markdown(f'<div class="alert alert-ok"><span class="alert-icon">🚀</span> Batch complete: <b>{ok}</b> OK &nbsp;·&nbsp; {failed} failed &nbsp;·&nbsp; {total} total</div>', unsafe_allow_html=True)
        if result.get("results"):
            df_res = pd.DataFrame([{
                "Invoice": r["invoice_id"], "Client": r["client"],
                "Stage": r["stage_label"], "Amount": r["amount"],
                "Subject": r["subject"][:65]+"…" if len(r["subject"])>65 else r["subject"],
                "Status": r["status"].upper(),
            } for r in result["results"]])
            st.dataframe(df_res, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

def page_audit_log():
    st.markdown("""
    <div class="page-head">
        <div class="page-title">Audit Log</div>
        <div class="page-sub">Complete history of every email generated and sent by the system</div>
    </div>
    """, unsafe_allow_html=True)

    logs = follow_up_logger.get_all_logs()
    if not logs:
        st.markdown('<div class="alert alert-warn"><span class="alert-icon">📭</span> No logs yet — generate some emails first.</div>', unsafe_allow_html=True)
        return

    ca, cb = st.columns([3,1])
    with ca:
        search = st.text_input("Search logs", placeholder="🔍  Invoice ID, client name, or status…")
    with cb:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Clear All Logs", use_container_width=True):
            follow_up_logger.clear_logs()
            st.success("Logs cleared"); st.rerun()

    df = pd.DataFrame(logs)
    if search:
        df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]

    cols = ["created_at","invoice_id","client_name","client_email","amount","currency",
            "days_overdue","escalation_label","email_subject","send_status","model_used"]
    df_d = df[[c for c in cols if c in df.columns]].copy()
    df_d["created_at"] = pd.to_datetime(df_d["created_at"]).dt.strftime("%d %b · %H:%M")
    st.dataframe(df_d, use_container_width=True, hide_index=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="card-title" style="margin-bottom:10px">Email Preview</div>', unsafe_allow_html=True)
    idx = st.selectbox("Select entry", range(len(df)),
        format_func=lambda i: f"{df.iloc[i]['invoice_id']}  ·  {df.iloc[i].get('client_name','')}  ·  {str(df.iloc[i].get('created_at',''))[:16]}")
    if idx is not None and len(df):
        row  = df.iloc[idx]
        body = row.get("email_body","")
        if body:
            st.markdown(f"""
            <div class="email-client">
                <div class="email-topbar">
                    <div class="email-dot r"></div><div class="email-dot y"></div><div class="email-dot g"></div>
                    <div class="email-winbar"><span class="email-url">📧 &nbsp; {row.get('invoice_id','')} — Audit Preview</span></div>
                </div>
                <div class="email-head">
                    <div class="email-head-to">To: {row.get('client_email','')}</div>
                    <div class="email-head-subject">{row.get('email_subject','')}</div>
                    <div class="email-ai-badge">📋 {row.get('send_status','').upper()} · {row.get('model_used','')}</div>
                </div>
                <div class="email-body">{body}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No email body stored for this entry.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

def page_settings():
    st.markdown("""
    <div class="page-head">
        <div class="page-title">Settings</div>
        <div class="page-sub">Configuration, environment status, and registered users</div>
    </div>
    """, unsafe_allow_html=True)

    api_ok   = bool(config.OPENAI_API_KEY and not config.OPENAI_API_KEY.startswith("sk-your") and len(config.OPENAI_API_KEY)>20)
    email_ok = bool(config.EMAIL_USER and "your-email" not in config.EMAIL_USER)
    dbg      = config.debug_info()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="card" style="margin-bottom:16px">
            <div class="card-head"><div class="card-title">🔑 OpenAI API</div></div>
            <div class="card-body">
                <div class="setting-row">
                    <div><div class="setting-label">API Key</div><div class="setting-sub">Used for email generation</div></div>
                    <div class="{'status-ok' if api_ok else 'status-err'}">{'✅ Configured' if api_ok else '❌ Not set'}</div>
                </div>
                <div class="setting-row">
                    <div class="setting-label">Key Prefix</div>
                    <div class="setting-value">{dbg['api_key_prefix']}</div>
                </div>
                <div class="setting-row">
                    <div class="setting-label">Model</div>
                    <div class="setting-value">{config.OPENAI_MODEL}</div>
                </div>
                <div class="setting-row">
                    <div><div class="setting-label">.env File</div><div class="setting-sub">Location loaded from</div></div>
                    <div class="setting-value">{dbg['env_file_found']}</div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-head"><div class="card-title">📧 Email / SMTP</div></div>
            <div class="card-body">
                <div class="setting-row">
                    <div class="setting-label">SMTP Host</div>
                    <div class="setting-value">{config.EMAIL_HOST}:{config.EMAIL_PORT}</div>
                </div>
                <div class="setting-row">
                    <div class="setting-label">Email User</div>
                    <div class="{'status-ok' if email_ok else 'status-err'}">{'✅ ' + config.EMAIL_USER if email_ok else '❌ Not configured'}</div>
                </div>
                <div class="setting-row">
                    <div class="setting-label">From Name</div>
                    <div class="setting-value">{config.EMAIL_FROM_NAME}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="card" style="margin-bottom:16px">
            <div class="card-head"><div class="card-title">📂 File Paths</div></div>
            <div class="card-body">
                <div class="setting-row">
                    <div class="setting-label">Invoices CSV</div>
                    <div class="setting-value">{'✅' if dbg['csv_exists'] else '❌'} {str(config.INVOICES_CSV).split('/')[-1]}</div>
                </div>
                <div class="setting-row">
                    <div class="setting-label">Database</div>
                    <div class="setting-value">{str(config.DB_PATH).split('/')[-1]}</div>
                </div>
                <div class="setting-row">
                    <div class="setting-label">Working Dir</div>
                    <div class="setting-value">{dbg['cwd'][-40:]}…</div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-head"><div class="card-title">📊 Escalation Thresholds</div></div>
            <div class="card-body">
                {''.join(f"""<div class="setting-row">
                    <div><div class="setting-label">Stage {s} — {lbl}</div></div>
                    <div class="setting-value">{d}+ days</div>
                </div>""" for s, d, lbl in [(1,config.STAGE_1_DAYS,"Friendly"),(2,config.STAGE_2_DAYS,"Formal"),(3,config.STAGE_3_DAYS,"Urgent"),(4,config.STAGE_4_DAYS,"Legal")])}
            </div>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.get("role") == "admin":
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="card-title" style="margin-bottom:10px">👥 Registered Users</div>', unsafe_allow_html=True)
        users = _load_users()
        df_u = pd.DataFrame([{"Username":u,"Full Name":d.get("full_name",""),"Role":d.get("role",""),"Created":d.get("created_at","")[:10]} for u,d in users.items()])
        st.dataframe(df_u, use_container_width=True, hide_index=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("🧪  Validate Configuration", type="primary"):
        errs = config.validate()
        if errs:
            for e in errs: st.markdown(f'<div class="alert alert-err"><span class="alert-icon">⚠️</span> {e}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert alert-ok"><span class="alert-icon">✅</span> All configuration checks passed!</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.get("authenticated"):
        auth_page(); return

    page = render_sidebar()
    if   page == "Dashboard":          page_dashboard()
    elif page == "AI Email Generator": page_email_generator()
    elif page == "Audit Log":          page_audit_log()
    elif page == "Settings":           page_settings()

if __name__ == "__main__":
    main()
