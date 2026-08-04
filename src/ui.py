from __future__ import annotations

import streamlit as st


THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {
  --bg-main: #09111a;
  --bg-surface: #121a26;
  --bg-surface-2: #0f1722;
  --border: #273247;
  --border-soft: #263141;
  --text-main: #f3f7fb;
  --text-soft: #9fb0c3;
  --cyan: #6ee7f9;
  --amber: #fbbf24;
  --emerald: #34d399;
}
.stApp {
  background: radial-gradient(circle at top, #10233b 0%, #09111a 42%, #071018 100%);
  color: var(--text-main);
  font-family: 'Inter', sans-serif;
}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #101923 0%, #0d141e 100%);
  border-right: 1px solid var(--border);
}
[data-testid="stSidebarNav"] {
  display: none;
}
.card-shell {
  background: linear-gradient(180deg, rgba(18,26,38,0.96) 0%, rgba(14,20,30,0.98) 100%);
  border: 1px solid var(--border);
  border-radius: 22px;
  padding: 1.1rem 1.2rem;
  box-shadow: 0 18px 50px rgba(0,0,0,0.24);
}
.hero-shell {
  background: linear-gradient(135deg, rgba(18,28,45,0.98) 0%, rgba(15,23,36,0.96) 48%, rgba(9,17,26,0.98) 100%);
  border: 1px solid var(--border);
  border-radius: 28px;
  padding: 1.4rem 1.5rem;
  box-shadow: 0 24px 60px rgba(0,0,0,0.28);
}
.section-title {
  font-size: 1.08rem;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 0.25rem;
}
.section-desc {
  color: var(--text-soft);
  font-size: 0.92rem;
}
.metric-pill {
  border-radius: 18px;
  border: 1px solid rgba(110,231,249,0.18);
  background: rgba(110,231,249,0.08);
  padding: 0.8rem 0.95rem;
}
.metric-pill.amber {border-color: rgba(251,191,36,0.18); background: rgba(251,191,36,0.08);}
.metric-pill.green {border-color: rgba(52,211,153,0.18); background: rgba(52,211,153,0.08);}
.metric-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: #9fb0c3;
}
.metric-value {
  margin-top: 0.35rem;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-main);
}
.small-note {
  color: var(--text-soft);
  font-size: 0.84rem;
}
.sidebar-group-title {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: #7f92a8;
  margin-top: 0.4rem;
  margin-bottom: 0.35rem;
}
.sidebar-item {
  border: 1px solid transparent;
  border-radius: 16px;
  background: rgba(255,255,255,0.03);
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.35rem;
}
.sidebar-item.active {
  border-color: rgba(110,231,249,0.16);
  background: rgba(110,231,249,0.07);
}
.sidebar-item-label {
  color: #f3f7fb;
  font-weight: 600;
  font-size: 0.95rem;
}
.sidebar-item-meta {
  color: #9fb0c3;
  font-size: 0.8rem;
  margin-top: 0.1rem;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] {
  border-radius: 14px;
  padding: 0.15rem 0.15rem 0.15rem 0.1rem;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
  border-radius: 14px;
}
[data-testid="stSidebar"] button[kind="secondary"] {
  border-radius: 14px;
}
.chat-shell {
  width: min(920px, 100%);
  margin: 0 auto;
  padding-bottom: 7rem;
}
.chat-empty-state {
  min-height: 48vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}
.chat-empty-title {
  font-size: 3rem;
  font-weight: 300;
  color: #e8edf5;
  line-height: 1.08;
}
.chat-empty-subtitle {
  max-width: 760px;
  margin-top: 1rem;
  color: #9fb0c3;
  font-size: 1.02rem;
  line-height: 1.65;
}
.user-row {
  display: flex;
  justify-content: flex-end;
  margin: 1.1rem 0;
}
.user-bubble {
  max-width: min(76%, 780px);
  background: linear-gradient(180deg, rgba(33,43,61,0.96) 0%, rgba(27,36,51,0.96) 100%);
  border: 1px solid rgba(142, 164, 192, 0.16);
  border-radius: 22px;
  padding: 0.9rem 1.05rem;
  color: #eef4fb;
  box-shadow: 0 14px 34px rgba(0,0,0,0.22);
}
.user-bubble-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 0.55rem;
  color: #a9bbcf;
  font-size: 0.82rem;
}
.avatar-chip {
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 700;
}
.avatar-user {
  background: rgba(109, 207, 255, 0.14);
  border: 1px solid rgba(110,231,249,0.2);
  color: #dff7fb;
}
.assistant-block {
  display: grid;
  grid-template-columns: 2.2rem minmax(0, 1fr);
  gap: 0.9rem;
  margin: 1.35rem 0 1.7rem;
  align-items: start;
}
.assistant-avatar {
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(52,211,153,0.14);
  border: 1px solid rgba(52,211,153,0.24);
  color: #d7f9e9;
  font-size: 0.7rem;
  font-weight: 700;
}
.assistant-copy {
  color: #edf2f8;
}
.assistant-label {
  color: #9db0c3;
  font-size: 0.82rem;
  margin-bottom: 0.35rem;
}
.assistant-copy p,
.assistant-copy li,
.assistant-copy code {
  font-size: 0.98rem;
}
.assistant-copy ul,
.assistant-copy ol {
  padding-left: 1.15rem;
}
.assistant-copy hr {
  border: none;
  border-top: 1px solid rgba(159,176,195,0.14);
  margin: 1rem 0;
}
[data-testid="stBottomBlockContainer"] {
  background: linear-gradient(180deg, rgba(8,12,18,0) 0%, rgba(8,12,18,0.82) 18%, rgba(8,12,18,0.96) 100%);
  padding-top: 1.2rem;
}
</style>
"""


def inject_theme() -> None:
    st.set_page_config(page_title="Manutenção Prescritiva", page_icon="🛠️", layout="wide", initial_sidebar_state="expanded")
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, eyebrow: str = "LLM-first local") -> None:
    st.markdown(
        f"""
        <div class="hero-shell">
          <div class="small-note" style="text-transform: uppercase; letter-spacing: 0.22em; color: #8ddff0;">{eyebrow}</div>
          <div style="font-size: 2rem; font-weight: 800; color: #f3f7fb; margin-top: 0.4rem;">{title}</div>
          <div class="section-desc" style="margin-top: 0.6rem;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="card-shell">
          <div class="section-title">{title}</div>
          <div class="section-desc">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, tone: str = "cyan") -> None:
    tone_class = {"cyan": "", "amber": " amber", "green": " green"}.get(tone, "")
    st.markdown(
        f"""
        <div class="metric-pill{tone_class}">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_section_title(title: str) -> None:
    st.markdown(f'<div class="sidebar-group-title">{title}</div>', unsafe_allow_html=True)
