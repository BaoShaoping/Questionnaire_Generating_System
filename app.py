"""
AI Survey QR Code Instant Audit Tool  –  v0.2
==============================================
New in v0.2:
  • Dual input: QR screenshot upload  OR  paste a direct survey URL
  • Scrollable "Full Questionnaire" panel — every extracted question + options
  • Side-by-side layout: questionnaire viewer on the left, report on the right
"""

import re
import time
from datetime import datetime
from typing import Optional, Tuple, Dict

import cv2
import numpy as np
import requests
import streamlit as st
from pyzbar import pyzbar
from PIL import Image

# ──────────────────────────────────────────────
# PAGE CONFIG  (must be the very first st call)
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="AI Survey QR Audit",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CUSTOM CSS
# ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    /* ── Hero ── */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0f4c81 100%);
        border-radius: 16px;
        padding: 2.4rem 2.8rem 2rem;
        margin-bottom: 1.8rem;
        border: 1px solid rgba(99,179,237,0.18);
        box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    }
    .hero-banner h1 {
        font-size: 2.1rem; font-weight: 600; color: #e2e8f0;
        margin: 0 0 .45rem; letter-spacing: -0.5px;
    }
    .hero-banner p { font-size: 1.02rem; color: #94a3b8; margin: 0; line-height: 1.6; }
    .hero-badge {
        display: inline-block; background: rgba(56,189,248,0.15); color: #38bdf8;
        border: 1px solid rgba(56,189,248,0.35); border-radius: 20px;
        padding: 2px 12px; font-size: .75rem; font-weight: 500;
        letter-spacing: .5px; text-transform: uppercase; margin-bottom: .8rem;
    }

    /* ── Scrollable questionnaire panel ── */
    .q-panel {
        background: #0f172a;
        border: 1px solid #1e3a5f;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        height: 440px;          /* fixed height – scrolls inside */
        overflow-y: auto;
        overflow-x: hidden;
        margin-bottom: 1rem;
    }
    /* Custom scrollbar */
    .q-panel::-webkit-scrollbar       { width: 6px; }
    .q-panel::-webkit-scrollbar-track { background: #0f172a; border-radius: 4px; }
    .q-panel::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    .q-panel::-webkit-scrollbar-thumb:hover { background: #38bdf8; }

    .q-item {
        background: #1e293b;
        border-radius: 10px;
        padding: .9rem 1.1rem;
        margin-bottom: .65rem;
        border-left: 3px solid #38bdf8;
    }
    .q-num  {
        font-family: 'DM Mono', monospace; font-size: .7rem;
        color: #38bdf8; text-transform: uppercase; letter-spacing: .8px;
        margin-bottom: .3rem;
    }
    .q-text { color: #e2e8f0; font-size: .93rem; line-height: 1.55; margin-bottom: .45rem; }
    .q-opt  { color: #64748b; font-size: .81rem; margin: .12rem 0 .12rem 1rem; }
    .q-opt::before { content: "▸ "; color: #334155; }
    .q-no-opts { color: #334155; font-size: .78rem; font-style: italic; margin-left: 1rem; }

    /* ── Step / info cards ── */
    .step-card {
        background: #1e293b; border-radius: 12px; padding: 1.1rem 1.3rem;
        border-left: 3px solid #38bdf8; margin-bottom: .85rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .step-card h4 { color: #cbd5e1; margin: 0 0 .3rem; font-size: .93rem; }
    .step-card p  { color: #64748b; margin: 0; font-size: .86rem; }

    /* ── Disclaimer ── */
    .disclaimer {
        background: #1e293b; border-radius: 8px; padding: .75rem 1.2rem;
        margin-top: 2.5rem; border: 1px solid #334155;
        font-size: .78rem; color: #475569; text-align: center;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] { background: #0f172a !important; border-right: 1px solid #1e293b; }
    section[data-testid="stSidebar"] * { color: #94a3b8 !important; }

    /* ── Progress bar ── */
    .stProgress > div > div > div { background-color: #38bdf8 !important; }

    img { border-radius: 8px; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px; background: #1e293b; border-radius: 10px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px; padding: 6px 20px; color: #64748b; font-size: .9rem;
    }
    .stTabs [aria-selected="true"] {
        background: #0f172a !important; color: #38bdf8 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════

PERSONAS = {
    "😤 Impatient Gen Z":
        "A 20-year-old who abandons anything over 90 seconds, hates walls of text, "
        "and expects TikTok-length clarity.",
    "👴 Elderly with Poor Vision":
        "A 72-year-old retiree with mild presbyopia who reads slowly, dislikes "
        "jargon, and rarely uses smartphones.",
    "🔬 Rigorous Expert":
        "A PhD researcher who scrutinises every ambiguous term, notices leading "
        "questions immediately, and expects balanced Likert scales.",
    "🌍 Non-Native English Speaker":
        "First language is Mandarin. Idioms, acronyms, and culturally-specific "
        "references create friction.",
    "📱 Mobile-Only User":
        "Filling out the survey on a 5-inch screen with one thumb. Long matrices "
        "and tiny tap-targets are pain points.",
}

JINA_BASE = "https://r.jina.ai/"


# ══════════════════════════════════════════════
#  QR DECODE
# ══════════════════════════════════════════════

def decode_qr(uploaded_file) -> Optional[str]:
    """
    Convert uploaded image → NumPy BGR array → pyzbar decode.
    Falls back to grayscale + sharpening for low-contrast screenshots.
    Returns the first QR URL found, or None.
    """
    pil_img = Image.open(uploaded_file).convert("RGB")
    cv_img  = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    for obj in pyzbar.decode(cv_img):
        if obj.type == "QRCODE":
            return obj.data.decode("utf-8")

    # Fallback: sharpen, retry
    gray      = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    sharpened = cv2.filter2D(gray, -1, np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]]))
    for obj in pyzbar.decode(sharpened):
        if obj.type == "QRCODE":
            return obj.data.decode("utf-8")

    return None


# ══════════════════════════════════════════════
#  URL VALIDATION
# ══════════════════════════════════════════════

def normalise_url(raw: str) -> Optional[str]:
    """
    Accept URLs with or without scheme prefix.
    Returns a full https:// URL or None if it doesn't look valid.
    """
    raw = raw.strip()
    if not raw:
        return None
    if not re.match(r'^https?://', raw, re.I):
        raw = "https://" + raw
    # Must have at least one dot in the host
    if re.match(r'^https?://[^/]+\.[^/]+', raw, re.I):
        return raw
    return None


# ══════════════════════════════════════════════
#  SCRAPE VIA JINA AI READER
# ══════════════════════════════════════════════

def scrape_survey(url: str) -> str:
    """
    Fetch the survey page as clean Markdown via Jina AI Reader proxy.
    Raises requests.RequestException on failure.
    """
    resp = requests.get(
        f"{JINA_BASE}{url}",
        headers={"User-Agent": "Mozilla/5.0 (SurveyAuditBot/1.0)",
                 "Accept":     "text/markdown, text/plain, */*"},
        timeout=25,
    )
    resp.raise_for_status()
    return resp.text


# ══════════════════════════════════════════════
#  PARSE SURVEY CONTENT
# ══════════════════════════════════════════════

def parse_survey_content(markdown_text: str) -> dict:
    """
    Regex-based extraction from scraped Markdown.

    Returns:
      title       – first H1/H2 heading
      questions   – deduplicated list of question strings
      q_with_opts – list of (question_str, [option_str]) tuples
      options     – flat list of all detected option strings
      word_count  – total word count
      raw         – full raw Markdown
    """
    # Title
    title_m = re.search(r'^#{1,2}\s+(.+)', markdown_text, re.MULTILINE)
    title   = title_m.group(1).strip() if title_m else "Untitled Survey"

    # Questions: sentences ending in "?" (with optional list prefix)
    q_pattern = re.compile(
        r'(?:^|\n)(?:\d+[\.\)]\s+|\*\s+|-\s+)?([A-Z][^?\n]{5,120}\?)',
        re.MULTILINE,
    )
    raw_qs = [m.group(1).strip() for m in q_pattern.finditer(markdown_text)]

    # Deduplicate, preserve order
    seen, questions = set(), []
    for q in raw_qs:
        if q not in seen:
            seen.add(q)
            questions.append(q)

    # Options: lines starting with choice markers
    opt_pattern = re.compile(
        r'^\s*(?:[A-Ea-e][\.\)]\s+|[○●□■✓✗]\s+|\(\w\)\s+)(.+)',
        re.MULTILINE,
    )
    all_options = [m.group(1).strip() for m in opt_pattern.finditer(markdown_text)]

    # Associate options with questions by splitting at each question boundary
    q_with_opts: list[tuple[str, list[str]]] = []
    if questions:
        segments = re.split(
            r'(?:^|\n)(?:\d+[\.\)]\s+|\*\s+|-\s+)?[A-Z][^?\n]{5,120}\?',
            markdown_text,
            flags=re.MULTILINE,
        )
        for i, q in enumerate(questions):
            seg      = segments[i + 1] if i + 1 < len(segments) else ""
            seg_opts = [m.group(1).strip() for m in opt_pattern.finditer(seg)]
            q_with_opts.append((q, seg_opts))

    return {
        "title":       title,
        "questions":   questions,
        "q_with_opts": q_with_opts,
        "options":     all_options,
        "word_count":  len(markdown_text.split()),
        "raw":         markdown_text,
    }


# ══════════════════════════════════════════════
#  AI ANALYSIS  (pluggable interface)
# ══════════════════════════════════════════════

def call_ai_agent(survey_data: dict, persona_name: str, persona_desc: str) -> dict:
    """
    Swap this body for a real LLM call when ready.
    Currently uses deterministic heuristics so the app works without API keys.

    Return schema:
      score           int   0-100
      grade           str   A/B/C/D
      friction_points list  [{"q": str, "issues": [str]}]
      ambiguities     list  [str]
      improvements    list  [str]
      persona_journey str
      summary         str
      n_questions     int
      word_count      int
    """
    questions  = survey_data["questions"]
    word_count = survey_data["word_count"]
    n_q        = len(questions)

    # ── Score ──────────────────────────────────────────────────
    score = 75
    if n_q > 20:    score -= 15
    elif n_q > 12:  score -= 7
    if n_q > 0 and (word_count / max(n_q, 1)) > 60:
        score -= 10
    if "Gen Z"      in persona_name and n_q > 10:        score -= 8
    if "Elderly"    in persona_name and word_count > 800: score -= 12
    if "Expert"     in persona_name and n_q < 5:         score -= 5
    if "Non-Native" in persona_name:                     score -= 5
    if "Mobile"     in persona_name and n_q > 15:        score -= 10
    score = max(10, min(99, score))

    # ── Friction points ────────────────────────────────────────
    friction = []
    vague = ["good","bad","often","sometimes","appropriate",
             "relevant","suitable","adequate","generally"]
    for q in questions[:15]:
        issues, ql = [], q.lower()
        if sum(ql.count(f" {w} ") for w in ["and","or"]) >= 2:
            issues.append("Possible double-barrelled question (asks two things at once)")
        found_vague = [w for w in vague if w in ql]
        if found_vague:
            issues.append(f"Vague term(s): {', '.join(found_vague)}")
        if len(q.split()) > 20:
            issues.append("Long question (>20 words) – consider splitting it")
        if re.search(r"don't you|wouldn't you|isn't it|don't you think", ql):
            issues.append("Potential leading question phrasing")
        if issues:
            friction.append({"q": q, "issues": issues})

    # ── Ambiguities ────────────────────────────────────────────
    ambiguities = []
    if any("often" in q.lower() or "regularly" in q.lower() for q in questions):
        ambiguities.append(
            "Frequency terms like 'often' / 'regularly' are subjective – "
            "replace with explicit ranges (e.g. '3–5 times per week')."
        )
    if word_count > 1000:
        ambiguities.append(
            f"Survey text is {word_count} words – above the 800-word comfort threshold."
        )
    ambiguities.append(
        f"{n_q} question(s) detected. "
        "Ideal survey length for >80% completion is under 12 questions."
        if n_q > 0 else
        "No questions parsed – the page may require JavaScript rendering. "
        "Try pasting the direct form URL."
    )

    # ── Improvements ───────────────────────────────────────────
    improvements = [
        "Add a progress bar so respondents know how far through they are.",
        "Replace open-ended text boxes with structured options where possible.",
        "Group related questions into clearly labelled sections.",
        "Test on a mobile viewport before launch – 60%+ of surveys are on phones.",
        "Add a brief thank-you / incentive statement at the start.",
    ]
    if "Elderly"    in persona_name: improvements.insert(0, "Increase font size ≥16 px; minimum tap-target 44×44 px (WCAG 2.1 AA).")
    if "Non-Native" in persona_name: improvements.insert(0, "Replace idioms / acronyms with plain language; offer a translated version.")
    if "Gen Z"      in persona_name: improvements.insert(0, "Front-load the 3 most critical questions – Gen Z often abandons in the first 2 min.")

    # ── Persona journey maps ───────────────────────────────────
    journey_map = {
        "😤 Impatient Gen Z":
            "**Sees survey link** → opens on phone → scrolls to gauge length → "
            "sees 15+ questions → *hesitates* → pushes through 4 → "
            "**hits open-text box** → *abandons*.",
        "👴 Elderly with Poor Vision":
            "**Opens on tablet** → text is small → pinch-zooms → layout breaks → "
            "**re-reads question twice** → unsure what 'NPS' means → leaves blank → "
            "**submits partial response**.",
        "🔬 Rigorous Expert":
            "**Reads every word** → spots undefined scale anchor in Q3 → "
            "**flags mentally** → completes survey but "
            "*unlikely to recommend the instrument*.",
        "🌍 Non-Native English Speaker":
            "**Starts enthusiastically** → Q2 uses idiom 'ballpark figure' → "
            "**confusion** → Google-translates → Q7 references a local event → "
            "*guesses* → **finishes with lower data quality**.",
        "📱 Mobile-Only User":
            "**Opens on 5-inch screen** → matrix question doesn't scroll properly → "
            "**forced to answer randomly** → back button wipes progress → "
            "*abandons in frustration*.",
    }
    persona_journey = journey_map.get(persona_name, "No journey map for this persona.")

    grade   = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"
    summary = (
        f"This survey scores **{score}/100** (Grade {grade}) from the perspective of "
        f"a *{persona_name}* respondent. "
        f"{len(friction)} question(s) flagged for friction; "
        f"{len(ambiguities)} structural ambiguity/ambiguities identified."
    )

    return {
        "score":           score,
        "grade":           grade,
        "friction_points": friction,
        "ambiguities":     ambiguities,
        "improvements":    improvements,
        "persona_journey": persona_journey,
        "summary":         summary,
        "n_questions":     n_q,
        "word_count":      word_count,
    }


# ══════════════════════════════════════════════
#  SCROLLABLE QUESTIONNAIRE PANEL
# ══════════════════════════════════════════════

def render_questionnaire_panel(survey_data: dict):
    """
    Render a fixed-height, scrollable card panel showing every extracted
    question and its answer options.  Uses pure HTML injected via
    st.markdown(unsafe_allow_html=True).
    """
    q_with_opts = survey_data.get("q_with_opts", [])
    n_q         = len(q_with_opts)

    if n_q == 0:
        st.warning(
            "No questions were extracted from the scraped content. "
            "The page may rely on JavaScript rendering — try pasting the direct form URL."
        )
        return

    # Build one card per question
    cards_html = ""
    for i, (q_text, opts) in enumerate(q_with_opts, 1):
        # Escape HTML special chars in question text
        q_safe = (q_text
                  .replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;"))

        if opts:
            opts_html = "".join(
                f'<div class="q-opt">'
                + o.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                + '</div>'
                for o in opts
            )
        else:
            opts_html = '<div class="q-no-opts">No options detected (free-text or JS-rendered)</div>'

        cards_html += f"""
        <div class="q-item">
          <div class="q-num">Question {i} / {n_q}</div>
          <div class="q-text">{q_safe}</div>
          {opts_html}
        </div>
        """

    st.markdown(
        f'<div class="q-panel">{cards_html}</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════
#  REPORT RENDERER
# ══════════════════════════════════════════════

def render_report(report: dict, persona_name: str, survey_url: str, survey_title: str):
    """Render the full diagnostic report."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    st.markdown("## 📊 Diagnostic Report")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score",     f"{report['score']}/100")
    c2.metric("Grade",     report["grade"])
    c3.metric("Questions", report["n_questions"])
    c4.metric("Words",     report["word_count"])

    st.markdown(f"""
    <div class="step-card" style="margin-top:.8rem">
      <h4>🎯 Audit Meta</h4>
      <p><strong>Survey:</strong> {survey_title}</p>
      <p><strong>Persona:</strong> {persona_name}</p>
      <p><strong>URL:</strong> <code style="font-size:.78rem">{survey_url}</code></p>
      <p><strong>Generated:</strong> {ts}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(report["summary"])

    st.markdown("### 🗺️ Persona Journey")
    st.info(report["persona_journey"])

    st.markdown("### ⚠️ Friction Points")
    if report["friction_points"]:
        for i, fp in enumerate(report["friction_points"], 1):
            label = f"Q{i}: {fp['q'][:75]}{'…' if len(fp['q'])>75 else ''}"
            with st.expander(label):
                for issue in fp["issues"]:
                    st.warning(f"🔸 {issue}")
    else:
        st.success("✅ No major friction points detected.")

    st.markdown("### 🔍 Structural Ambiguities")
    for amb in report["ambiguities"]:
        st.markdown(f"- {amb}")

    st.markdown("### 💡 Improvements")
    for idx, imp in enumerate(report["improvements"], 1):
        st.markdown(f"**{idx}.** {imp}")

    # Download button
    md = _build_markdown_report(report, persona_name, survey_url, survey_title, ts)
    st.download_button(
        label="⬇️ Download Report (.md)",
        data=md.encode("utf-8"),
        file_name=f"survey_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )


def _build_markdown_report(report, persona, url, title, ts) -> str:
    lines = [
        "# 📊 Survey Diagnostic Report", "",
        "| Field | Value |", "|---|---|",
        f"| Survey | {title} |", f"| URL | {url} |",
        f"| Persona | {persona} |",
        f"| Score | {report['score']}/100 (Grade {report['grade']}) |",
        f"| Questions | {report['n_questions']} |",
        f"| Word Count | {report['word_count']} |",
        f"| Generated | {ts} |", "",
        "## Summary", "", report["summary"], "",
        "## Persona Journey Map", "", report["persona_journey"], "",
        "## Question-Level Friction Points", "",
    ]
    if report["friction_points"]:
        for fp in report["friction_points"]:
            lines.append(f"**Q:** {fp['q']}")
            lines += [f"- ⚠️ {i}" for i in fp["issues"]]
            lines.append("")
    else:
        lines += ["No major friction points detected.", ""]

    lines += [
        "## Structural Ambiguities", "",
        *[f"- {a}" for a in report["ambiguities"]], "",
        "## Improvement Suggestions", "",
        *[f"{i+1}. {s}" for i, s in enumerate(report["improvements"])], "",
        "---", "*Generated by AI Survey QR Audit Tool – for diagnostic purposes only.*",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════
#  SHARED PIPELINE  (scrape → parse → analyse)
# ══════════════════════════════════════════════

def run_pipeline(survey_url: str, selected_persona: str) -> Optional[Tuple[Dict, Dict]]:
    """
    Steps 2-3 shared by both input modes.
    Renders its own progress UI inline.
    Returns (survey_data, report) or None on error.
    """
    progress = st.progress(0, text="Initialising…")

    with st.spinner("🌐 Fetching survey content via Jina AI Reader…"):
        try:
            raw_md = scrape_survey(survey_url)
            progress.progress(50, text="Step 2/3 – Content scraped")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Failed to fetch survey content: {e}")
            progress.empty()
            return None

    survey_data = parse_survey_content(raw_md)
    n_q = len(survey_data["questions"])
    st.success(
        f"✅ Survey loaded: **{n_q} question(s)** · "
        f"{survey_data['word_count']} words"
    )

    with st.spinner(f"🤖 Analysing with persona '{selected_persona}'…"):
        time.sleep(0.5)
        report = call_ai_agent(survey_data, selected_persona, PERSONAS[selected_persona])
        progress.progress(100, text="Step 3/3 – Analysis complete ✅")
        time.sleep(0.35)
        progress.empty()

    return survey_data, report


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🎭 Simulated Persona")
    st.markdown(
        "Choose whose lens the AI uses to evaluate friction, confusion, "
        "and drop-off risk in the survey."
    )
    selected_persona = st.selectbox(
        "Persona",
        options=list(PERSONAS.keys()),
        index=0,
        label_visibility="collapsed",
    )
    st.markdown(f"*{PERSONAS[selected_persona]}*")

    st.markdown("---")
    st.markdown("### ℹ️ How It Works")
    for step, desc in [
        ("1️⃣ Input",   "Upload QR screenshot OR paste a survey URL."),
        ("2️⃣ Decode",  "pyzbar extracts the URL from the QR image."),
        ("3️⃣ Scrape",  "Jina AI Reader fetches survey content as Markdown."),
        ("4️⃣ Analyse", "AI engine diagnoses friction & ambiguity."),
        ("5️⃣ Explore", "Scroll through every question, then read the report."),
    ]:
        st.markdown(f"**{step}** – {desc}")

    st.markdown("---")
    st.markdown(
        "<div class='disclaimer' style='text-align:left;margin-top:0'>"
        "🔒 No survey response data is stored.<br>"
        "Analysis runs on scraped public content only."
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════
#  MAIN PAGE
# ══════════════════════════════════════════════

st.markdown(
    """
    <div class="hero-banner">
      <div class="hero-badge">AI-Powered · MVP v0.2</div>
      <h1>📷 AI Survey QR Code Instant Audit</h1>
      <p>Upload a QR-code screenshot <em>or</em> paste a direct survey URL —
      then let the AI diagnose logic loopholes, terminology barriers, and completion
      friction through the eyes of your chosen respondent persona.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Dual input via tabs ───────────────────────────────────
tab_qr, tab_url = st.tabs(["📷  QR Code Screenshot", "🔗  Paste Survey URL"])

# Use session_state so results persist across tab switches
if "survey_data" not in st.session_state:
    st.session_state.survey_data = None
if "report"      not in st.session_state:
    st.session_state.report      = None
if "survey_url"  not in st.session_state:
    st.session_state.survey_url  = None

# ─────────────────────────────────────────
#  TAB 1 – QR screenshot
# ─────────────────────────────────────────
with tab_qr:
    uploaded_file = st.file_uploader(
        "Drag & drop a screenshot containing a survey QR code",
        type=["png", "jpg", "jpeg", "webp", "bmp"],
        help="The QR code must be fully visible and reasonably sharp.",
        key="qr_uploader",
    )

    if uploaded_file is not None:
        img_col, status_col = st.columns([1, 2])

        with img_col:
            st.image(uploaded_file, caption="Uploaded screenshot", use_container_width=True)

        with status_col:
            st.markdown("#### Processing")
            with st.spinner("🔍 Scanning for QR code…"):
                uploaded_file.seek(0)
                decoded_url = decode_qr(uploaded_file)

            if not decoded_url:
                st.error(
                    "❌ No valid QR code detected. "
                    "Ensure the image is clear and contains the full code, "
                    "or switch to the **Paste Survey URL** tab."
                )
            else:
                st.success(f"✅ QR Decoded: `{decoded_url}`")
                result = run_pipeline(decoded_url, selected_persona)
                if result:
                    st.session_state.survey_data = result[0]
                    st.session_state.report      = result[1]
                    st.session_state.survey_url  = decoded_url

# ─────────────────────────────────────────
#  TAB 2 – Direct URL
# ─────────────────────────────────────────
with tab_url:
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        raw_url = st.text_input(
            "Survey URL",
            placeholder="https://forms.google.com/…  or  typeform.com/…",
            label_visibility="collapsed",
            key="url_input",
        )
    with col_btn:
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        run_btn = st.button("Audit →", use_container_width=True, type="primary", key="url_btn")

    if run_btn:
        if not raw_url:
            st.warning("Please enter a URL first.")
        else:
            validated = normalise_url(raw_url)
            if not validated:
                st.error(
                    "❌ That doesn't look like a valid URL. "
                    "Include the full address, e.g. https://example.com/survey"
                )
            else:
                st.success(f"✅ URL accepted: `{validated}`")
                result = run_pipeline(validated, selected_persona)
                if result:
                    st.session_state.survey_data = result[0]
                    st.session_state.report      = result[1]
                    st.session_state.survey_url  = validated


# ══════════════════════════════════════════════
#  OUTPUT AREA  (shared by both input paths)
# ══════════════════════════════════════════════

if st.session_state.report is not None:
    sd    = st.session_state.survey_data
    rpt   = st.session_state.report
    s_url = st.session_state.survey_url

    st.markdown("---")

    # ── Side-by-side layout ───────────────────────────────────
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        n_q_label = rpt.get("n_questions", len(sd.get("questions", [])))
        st.markdown(
            f"### 📋 Full Questionnaire"
            f"<span style='font-size:.8rem;color:#64748b;font-weight:400'>"
            f"  {n_q_label} question(s) · scroll to read all"
            f"</span>",
            unsafe_allow_html=True,
        )
        # ── THE SCROLLABLE PANEL ──────────────────────────────
        render_questionnaire_panel(sd)

        # Optional: raw Markdown toggle
        with st.expander("🔎 View raw scraped Markdown"):
            raw_preview = sd["raw"]
            if len(raw_preview) > 6000:
                raw_preview = raw_preview[:6000] + "\n\n…[truncated to 6 000 chars]"
            st.text_area(
                "raw",
                value=raw_preview,
                height=260,
                disabled=True,
                label_visibility="collapsed",
            )

    with right_col:
        render_report(rpt, selected_persona, s_url, sd["title"])

else:
    # Empty state
    st.markdown(
        """
        <div style="text-align:center; padding:3rem 0; color:#475569;">
          <div style="font-size:3.5rem">📤</div>
          <p style="font-size:1.1rem; margin-top:.6rem">
            Upload a QR-code screenshot or paste a survey URL above to begin.
          </p>
          <p style="font-size:.85rem; color:#334155">
            Supports Google Forms · Typeform · SurveyMonkey · Qualtrics · and more
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Disclaimer ────────────────────────────────────────────
st.markdown(
    "<div class='disclaimer'>"
    "🔒 <strong>Privacy Notice</strong>: This tool is for survey logic diagnosis only. "
    "No raw response data is stored. Scraped content is processed in-memory and "
    "discarded after the session ends."
    "</div>",
    unsafe_allow_html=True,
)