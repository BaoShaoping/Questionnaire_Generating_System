"""
AI Survey QR Code Instant Audit Tool - v0.3
==============================================
Pipeline (new step 2b highlighted):
  1. Input        - QR screenshot upload OR paste a direct URL
  2. Scrape       - Jina AI Reader -> raw Markdown string
  2b. CONVERT     - convert_to_json() Markdown -> structured JSON list
  3. Analyse      - call_ai_agent() consumes JSON (not raw Markdown)
  4. Display      - scrollable questionnaire panel + diagnostic report

JSON schema per question
  {
    "question_id"   : "Q1",
    "question_text" : "How satisfied are you with our service?",
    "question_type" : "single_choice" | "multiple_choice" | "matrix"
                    | "fill_in_blank" | "rating" | "open_text",
    "options"       : ["Very satisfied", "Satisfied", ...],  # [] for open/blank
    "is_required"   : true | false
  }
==============================================
HOW TO RUN(cmd):
streamlit run app.py
"""

import json
import re
import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import requests
import streamlit as st
from pyzbar import pyzbar
from PIL import Image

# PAGE CONFIG  (must be the very first st call)
st.set_page_config(
    page_title="AI Survey QR Audit",
    page_icon="Q",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CUSTOM CSS
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    /* Hero */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0f4c81 100%);
        border-radius: 16px; padding: 2.4rem 2.8rem 2rem;
        margin-bottom: 1.8rem; border: 1px solid rgba(99,179,237,0.18);
        box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    }
    .hero-banner h1 { font-size:2.1rem; font-weight:600; color:#e2e8f0; margin:0 0 .45rem; letter-spacing:-0.5px; }
    .hero-banner p  { font-size:1.02rem; color:#94a3b8; margin:0; line-height:1.6; }
    .hero-badge {
        display:inline-block; background:rgba(56,189,248,0.15); color:#38bdf8;
        border:1px solid rgba(56,189,248,0.35); border-radius:20px;
        padding:2px 12px; font-size:.75rem; font-weight:500;
        letter-spacing:.5px; text-transform:uppercase; margin-bottom:.8rem;
    }

    /* Scrollable questionnaire panel */
    .q-panel {
        background:#0f172a; border:1px solid #1e3a5f; border-radius:12px;
        padding:1rem 1.2rem; height:480px;
        overflow-y:auto; overflow-x:hidden; margin-bottom:1rem;
    }
    .q-panel::-webkit-scrollbar       { width:6px; }
    .q-panel::-webkit-scrollbar-track { background:#0f172a; border-radius:4px; }
    .q-panel::-webkit-scrollbar-thumb { background:#334155; border-radius:4px; }
    .q-panel::-webkit-scrollbar-thumb:hover { background:#38bdf8; }

    .q-item { background:#1e293b; border-radius:10px; padding:.9rem 1.1rem; margin-bottom:.65rem; border-left:3px solid #38bdf8; }
    .q-meta { display:flex; gap:.5rem; align-items:center; margin-bottom:.35rem; flex-wrap:wrap; }
    .q-num  { font-family:'DM Mono',monospace; font-size:.68rem; color:#38bdf8; text-transform:uppercase; letter-spacing:.8px; }
    .q-type { font-size:.68rem; padding:2px 8px; border-radius:10px; font-weight:500; }
    .q-type-sc   { background:#0c2340; color:#60a5fa; border:1px solid #1e3a5f; }
    .q-type-mc   { background:#0d2b1d; color:#4ade80; border:1px solid #14532d; }
    .q-type-mx   { background:#2a1a0d; color:#fb923c; border:1px solid #7c2d12; }
    .q-type-fb   { background:#1a0a2e; color:#c084fc; border:1px solid #4a044e; }
    .q-type-rt   { background:#2d1a00; color:#fbbf24; border:1px solid #78350f; }
    .q-type-ot   { background:#1e1e1e; color:#94a3b8; border:1px solid #334155; }
    .q-required  { font-size:.68rem; color:#f87171; }
    .q-text { color:#e2e8f0; font-size:.93rem; line-height:1.55; margin-bottom:.45rem; }
    .q-opt  { color:#64748b; font-size:.81rem; margin:.12rem 0 .12rem 1rem; }
    .q-opt::before { content:"-"; color:#334155; }
    .q-no-opts { color:#334155; font-size:.78rem; font-style:italic; margin-left:1rem; }

    /* Step / info cards */
    .step-card { background:#1e293b; border-radius:12px; padding:1.1rem 1.3rem; border-left:3px solid #38bdf8; margin-bottom:.85rem; box-shadow:0 2px 10px rgba(0,0,0,0.2); }
    .step-card h4 { color:#cbd5e1; margin:0 0 .3rem; font-size:.93rem; }
    .step-card p  { color:#64748b; margin:0; font-size:.86rem; }

    /* Pipeline step indicator */
    .pipe-step { display:flex; align-items:flex-start; gap:.75rem; padding:.6rem 0; border-bottom:1px solid #1e293b; }
    .pipe-step:last-child { border-bottom:none; }
    .pipe-icon { font-size:1.1rem; margin-top:.05rem; flex-shrink:0; }
    .pipe-label { font-size:.85rem; color:#94a3b8; line-height:1.4; }
    .pipe-label strong { color:#e2e8f0; }

    /* JSON badge */
    .json-badge { display:inline-block; background:#0d2b1d; color:#4ade80; border:1px solid #14532d; border-radius:6px; padding:1px 8px; font-family:'DM Mono',monospace; font-size:.72rem; margin-left:.4rem; }

    /* Disclaimer */
    .disclaimer { background:#1e293b; border-radius:8px; padding:.75rem 1.2rem; margin-top:2.5rem; border:1px solid #334155; font-size:.78rem; color:#475569; text-align:center; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background:#0f172a !important; border-right:1px solid #1e293b; }
    section[data-testid="stSidebar"] * { color:#94a3b8 !important; }

    /* Progress bar */
    .stProgress > div > div > div { background-color:#38bdf8 !important; }

    img { border-radius:8px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap:6px; background:#1e293b; border-radius:10px; padding:4px; }
    .stTabs [data-baseweb="tab"]      { border-radius:8px; padding:6px 20px; color:#64748b; font-size:.9rem; }
    .stTabs [aria-selected="true"]    { background:#0f172a !important; color:#38bdf8 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


#  global answer of questionnaires

G_As = [
        {"id": 1, "type": "single_choice", "bili": [30, 70]},
        {"id": 2, "type": "single_choice", "bili": [20, 30, 30, 20]},
        {"id": 3, "type": "multiple_choice", "bili": [25, 25, 25, 25]},
        {"id": 9, "type": "fill_in_blank", "bili": [50, 50], "content": ["sample_a", "sample_b"]},
    ]



#  web

G_LATEST_QUESTIONS_JSON: list[dict] = []

from flask import Flask, jsonify

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
ANSWER_FIXTURE_PATH = BASE_DIR / "Web_AutoFill" / "answer_3.json"

def generate_answers():
    global G_As
    try:
        raw_answers = _llm_generate_answers(G_As, G_LATEST_QUESTIONS_JSON)
        normalized_answers = _normalize_answers_to_gas(raw_answers, G_As)
        if normalized_answers:
            G_As = normalized_answers
    except Exception as e:
        print(f"{'=' * 10} generate_answers fallback {'=' * 10}\n {e}")

    with ANSWER_FIXTURE_PATH.open("r", encoding="utf-8") as f:
        out = json.load(f)
    return  out#G_As


def _build_answer_system_prompt() -> str:
    return """
You are an assistant that generates survey answer distributions.
OUTPUT: a single JSON object with one key "answers".

Required output schema:
{
  "answers": [
    {
      "id": 1,
      "type": "<string>",
      "bili": [30, 70],
      "content": ["optional text answer", "optional text answer"]
    }
  ]
}

Rules:
- Output ONLY valid JSON. No markdown fences, no explanation.
- Keep every answer item compatible with the provided template shape.
- Keep "id" as integer.
- "bili" must be an integer array, each value in [0, 100].
- Include "content" only for text-style answers.
""".strip()


def _normalize_percentages(values: list[int], target_sum: int = 100) -> list[int]:
    if not values:
        return [100]
    safe = [max(0, int(v)) for v in values]
    total = sum(safe)
    if total <= 0:
        even = target_sum // len(safe)
        out = [even] * len(safe)
        out[0] += target_sum - sum(out)
        return out

    scaled = [int(v * target_sum / total) for v in safe]
    diff = target_sum - sum(scaled)
    scaled[0] += diff
    return [max(0, min(100, v)) for v in scaled]


def _normalize_answers_to_gas(raw_answers, fallback_answers: list[dict]) -> list[dict]:
    if not isinstance(raw_answers, list):
        return fallback_answers

    normalized: list[dict] = []
    for idx, item in enumerate(raw_answers):
        fallback_item = fallback_answers[idx] if idx < len(fallback_answers) else {}
        if not isinstance(item, dict):
            continue

        answer_id = item.get("id", fallback_item.get("id", idx + 1))
        try:
            answer_id = int(answer_id)
        except (TypeError, ValueError):
            answer_id = int(fallback_item.get("id", idx + 1))

        answer_type = str(item.get("type", fallback_item.get("type", "single_choice")))
        bili = item.get("bili", fallback_item.get("bili", [100]))
        if not isinstance(bili, list):
            bili = fallback_item.get("bili", [100])
        bili = _normalize_percentages([int(v) for v in bili if isinstance(v, (int, float))])

        normalized_item = {"id": answer_id, "type": answer_type, "bili": bili}

        content = item.get("content", fallback_item.get("content"))
        if content is not None:
            if isinstance(content, list):
                safe_content = [str(v) for v in content if str(v).strip()]
            else:
                safe_content = [str(content)] if str(content).strip() else []
            if safe_content:
                normalized_item["content"] = safe_content

        normalized.append(normalized_item)

    return normalized or fallback_answers


def _llm_generate_answers(template_answers: list[dict], questions_json: list[dict]) -> list[dict]:
    api_key = st.secrets["ZHIPU_API_KEY"]
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    user_payload = json.dumps({
        "template_answers": template_answers,
        "questions": questions_json or [],
        "instructions": (
            "Generate realistic answer distribution data. "
            "If questions are empty, keep the same number of answers as template_answers."
        ),
    }, ensure_ascii=False)

    data = {
        "model": "GLM-4.6V-Flash",
        "messages": [
            {"role": "system", "content": _build_answer_system_prompt()},
            {"role": "user", "content": user_payload},
        ],
        "stream": False,
        "thinking": {"type": "disabled"},
    }

    response = requests.post(url, headers=headers, json=data, timeout=120)
    result = response.json()
    print(f"{'=' * 10} step answers result from {url} {'=' * 10}\n {result}")

    raw_text = result["choices"][0]["message"]["content"]
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    parsed = json.loads(text.strip())
    return parsed.get("answers", [])

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route('/answers')
def answers():
    return jsonify(generate_answers())


def ensure_answer_api_running(port: int = 5000) -> None:
    """Start the local Flask answers API without blocking Streamlit."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return
    except OSError:
        pass

    def _run() -> None:
        app.run(port=port, debug=False, use_reloader=False)

    threading.Thread(target=_run, daemon=True).start()

#  CONSTANTS

PERSONAS = {
    "Impatient Gen Z":
        "A 20-year-old who abandons anything over 90 seconds, hates walls of text, "
        "and expects TikTok-length clarity.",
    "Elderly with Poor Vision":
        "A 72-year-old retiree with mild presbyopia who reads slowly, dislikes "
        "jargon, and rarely uses smartphones.",
    "Rigorous Expert":
        "A PhD researcher who scrutinises every ambiguous term, notices leading "
        "questions immediately, and expects balanced Likert scales.",
    "Non-Native English Speaker":
        "First language is Mandarin. Idioms, acronyms, and culturally-specific "
        "references create friction.",
    "Mobile-Only User":
        "Filling out the survey on a 5-inch screen with one thumb. Long matrices "
        "and tiny tap-targets are pain points.",
}

JINA_BASE = "https://r.jina.ai/"

# Mapping from internal type key to human-readable label + CSS class
Q_TYPE_META = {
    "single_choice":   ("Single Choice",   "q-type-sc"),
    "multiple_choice": ("Multiple Choice", "q-type-mc"),
    "matrix":          ("Matrix",          "q-type-mx"),
    "fill_in_blank":   ("Fill in Blank",   "q-type-fb"),
    "rating":          ("Rating Scale",    "q-type-rt"),
    "open_text":       ("Open Text",       "q-type-ot"),
}


# STEP 1a - QR Decode

def decode_qr(uploaded_file) -> Optional[str]:
    """
    Uploaded image -> NumPy BGR array -> pyzbar.
    Falls back to grayscale + sharpening for low-contrast screenshots.
    Returns first QR URL or None.
    """
    pil_img   = Image.open(uploaded_file).convert("RGB")
    cv_img    = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    for obj in pyzbar.decode(cv_img):
        if obj.type == "QRCODE":
            return obj.data.decode("utf-8")

    gray      = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    sharpened = cv2.filter2D(gray, -1, np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]]))
    for obj in pyzbar.decode(sharpened):
        if obj.type == "QRCODE":
            return obj.data.decode("utf-8")

    return None


# STEP 1b - URL Validation

def normalise_url(raw: str) -> Optional[str]:
    """Prepend https:// if missing; return None if not a plausible URL."""
    raw = raw.strip()
    if not raw:
        return None
    if not re.match(r'^https?://', raw, re.I):
        raw = "https://" + raw
    if re.match(r'^https?://[^/]+\.[^/]+', raw, re.I):
        return raw
    return None


# STEP 2 - Scrape via Jina AI Reader

def scrape_survey(url: str) -> str:
    """
    GET https://r.jina.ai/<url> -> raw Markdown string.

    Jina AI Reader strips JavaScript and returns clean, readable Markdown,
    which is ideal for LLM processing but must still be converted to
    structured JSON before analysis (see convert_to_json below).
    """
    resp = requests.get(
        f"{JINA_BASE}{url}",
        headers={
            "User-Agent": "Mozilla/5.0 (SurveyAuditBot/1.0)",
            "Accept":     "text/markdown, text/plain, */*",
        },
        timeout=25,
    )
    resp.raise_for_status()
    return resp.text  # raw Markdown, not yet structured


# STEP 2b - Markdown to structured JSON

# Helper: call a real LLM for Markdown -> JSON
def _llm_convert(markdown_text: str) -> list[dict]:
    """
    Real LLM integration point for Markdown -> JSON conversion.
    The model is prompted to output only schema-compliant JSON.
    """
    # Option A: OpenAI
    # from openai import OpenAI
    # client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     response_format={"type": "json_object"},
    #     messages=[
    #         {"role": "system", "content": _build_conversion_system_prompt()},
    #         {"role": "user",   "content": markdown_text[:12000]},
    #     ],
    # )
    # raw_json = response.choices[0].message.content
    # return json.loads(raw_json).get("questions", [])

    # Option B: Anthropic Claude
    # import anthropic
    # client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    # msg = client.messages.create(
    #     model="claude-opus-4-5",
    #     max_tokens=4096,
    #     system=_build_conversion_system_prompt(),
    #     messages=[{"role": "user", "content": markdown_text[:12000]}],
    # )
    # raw_json = msg.content[0].text
    # # Strip accidental markdown fences the model might add
    # raw_json = re.sub(r'^```json\s*|\s*```$', '', raw_json.strip())
    # return json.loads(raw_json).get("questions", [])

    # Option C: GLM
    import requests
    API_KEY = st.secrets["ZHIPU_API_KEY"]
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "GLM-4.6V-Flash",
        "messages": [
            {"role": "system", "content": _build_conversion_system_prompt()},
            {"role": "user",   "content": markdown_text},
        ],
        "stream": False,
        "thinking": {
            "type": "disabled"
        }
    }
    response = requests.post(url, headers=headers, json=data, timeout=120)
    result = response.json()

    print(f"{'='*10} step 2 result from {url} {'='*10}\n {result}")

    if 'error' in result:
        print(f"{'='*10} using test json {'='*10}\n")
        with open('test.json', 'r', encoding="utf-8") as f:
            raw_json = json.load(f)
            _questions = raw_json.get("questions", [])
    else:
        raw_json = result['choices'][0]['message']['content']
        text = raw_json.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]
        _questions = json.loads(text.strip()).get("questions", [])
    print(f"{'='*10} raw json {'='*10}\n {raw_json}")

    return _questions



def _build_conversion_system_prompt() -> str:
    """
    System prompt used when calling a real LLM for Markdown -> JSON conversion.
    Kept separate so it can be tuned without touching pipeline logic.
    """
    return """
You are a survey-parsing assistant.
INPUT:  Markdown text scraped from a survey web page.
OUTPUT: A single JSON object with one key "questions", containing an array.

Each element in the array MUST follow this exact schema:
{
  "question_id"   : "Q1",            // sequential, e.g. Q1 Q2 Q3
  "question_text" : "<full text>",
  "question_type" : "<type>",        // MUST be one of the six values below
  "options"       : ["<opt1>", "..."], // empty array [] for open/fill/rating
  "is_required"   : true | false     // true if the survey marks it required
}

Allowed question_type values (use exactly these strings):
  single_choice   - radio buttons, one answer allowed
  multiple_choice - checkboxes, multiple answers allowed
  matrix          - grid/table of sub-questions sharing the same scale
  fill_in_blank   - short free-text or number entry
  rating          - numeric scale (NPS, stars, Likert with no explicit options)
  open_text       - long free-text / essay box

Rules:
- Output ONLY the JSON object. No preamble, no markdown fences, no explanation.
- If a question's type is ambiguous, choose the closest match.
- Ignore navigation text, progress bars, page titles, and form submit buttons.
- Preserve the original question wording exactly.
""".strip()


# Helper: rule-based mock for Markdown -> JSON
def _mock_convert(markdown_text: str) -> list[dict]:
    """
    Mock implementation of the Markdown -> JSON conversion.

    INPUT  : raw Markdown string from Jina AI Reader
    OUTPUT : list of question dicts matching the schema

    This function uses regex heuristics to approximate what a real LLM
    would produce.  It is intentionally verbose so the logic is transparent.

    Replace the body of convert_to_json() with _llm_convert() once you have
    an API key configured.
    """

    # 1. Extract the title (first H1 or H2)
    # (used only for metadata, not per-question)

    # 2. Detect option-line pattern
    opt_re = re.compile(
        r'^\s*(?:[A-Ea-e][\.\)]\s+|[•○●□■✓✕⭐★]\s+|\(\w\)\s+)(.+)',
        re.MULTILINE,
    )

    # 3. Split document into question blocks
    # A "question block" is a sentence ending in "?" optionally preceded by
    # a list-item marker (1. / * / -).
    q_split_re = re.compile(
        r'(?:^|\n)((?:\d+[\.\)]\s+|\*\s+|-\s+)?[A-Z\(][^?\n]{4,140}\?)',
        re.MULTILINE,
    )

    matches  = list(q_split_re.finditer(markdown_text))
    segments = q_split_re.split(markdown_text)
    # split() with a capturing group -> [pre, q1, text_after_q1, q2, text_after_q2, ...]
    # Indices: q_text at odd positions (1, 3, 5, ...), trailing text at even (2, 4, 6, ...)

    questions_raw: list[tuple[str, str]] = []  # (question_text, following_text)
    for i in range(1, len(segments) - 1, 2):
        q_text    = segments[i].strip()
        following = segments[i + 1] if i + 1 < len(segments) else ""
        questions_raw.append((q_text, following))

    # Deduplicate while preserving order
    seen, unique_pairs = set(), []
    for pair in questions_raw:
        if pair[0] not in seen:
            seen.add(pair[0])
            unique_pairs.append(pair)

    # 4. Build structured question objects
    questions: list[dict] = []
    for idx, (q_text, following) in enumerate(unique_pairs, start=1):

        # Extract options from the text that immediately follows the question
        opts = [m.group(1).strip() for m in opt_re.finditer(following)]
        # Cap at first 12 options (avoids capturing next question's options)
        opts = opts[:12]

        # Type inference
        q_lower = q_text.lower()

        if opts:
            # If we found option lines, decide single vs multiple
            if re.search(
                r'select all|check all|choose all|multiple|all that apply',
                q_lower,
            ):
                q_type = "multiple_choice"
            else:
                q_type = "single_choice"
        elif re.search(
            r'\brate\b|\brating\b|\bscale\b|\bscore\b|how likely|nps|stars?\b|'
            r'\b\d\s*[-–]\s*\d\b',        # "1 - 5" pattern
            q_lower,
        ):
            q_type = "rating"
            opts   = []  # rating scales don't have discrete option items
        elif re.search(
            r'please (list|describe|explain|tell us|write|share)|'
            r'in your own words|comment|suggest|elaborate',
            q_lower,
        ):
            q_type = "open_text"
        elif re.search(
            r'fill in|blank|enter your|type your|your name|your email|'
            r'your age|number of|how many|what is your',
            q_lower,
        ):
            q_type = "fill_in_blank"
        elif re.search(
            r'\beach\b|\bfor each\b|\bfollowing (aspects|items|dimensions)\b|'
            r'matrix|grid',
            q_lower,
        ):
            q_type = "matrix"
        else:
            # Default: if options present -> single_choice, else open_text
            q_type = "single_choice" if opts else "open_text"

        # Required inference
        # Some platforms mark required fields with * or (required)
        is_required = bool(re.search(r'\*|required|mandatory', q_lower))

        questions.append({
            "question_id":   f"Q{idx}",
            "question_text": q_text,
            "question_type": q_type,
            "options":       opts,
            "is_required":   is_required,
        })

    return questions


# Public entry point
def convert_to_json(markdown_text: str) -> list[dict]:
    """
    Step 2b: Convert raw Markdown from Jina AI Reader into structured JSON.

    Returns a list of question dictionaries with:
      - question_id
      - question_text
      - question_type
      - options
      - is_required
    """
    # Try real LLM first; fall back to mock on any error.
    try:
        return _llm_convert(markdown_text)
    except Exception:
        pass  # Missing key, network error, JSON parse error, etc.

    # Mock fallback
    return _mock_convert(markdown_text)


# STEP 3 - AI Analysis
# Now driven entirely by JSON data.

def call_ai_agent(
        questions_json: list[dict],
        survey_title: str,
        persona_name: str,
        persona_desc: str,
) -> dict:
    """
    Step 3: Analyse the structured survey JSON.
    INPUT  : questions_json - output of convert_to_json()
    OUTPUT : report dict consumed by render_report()
    Calls GLM API (_llm_analyse); falls back to rule-based mock on any error.
    """
    # Pre-compute summary stats to pass into the prompt and for fallback use
    n_q = len(questions_json)
    n_required = sum(1 for q in questions_json if q.get("is_required"))
    type_counts: dict[str, int] = {}
    for q in questions_json:
        t = q.get("question_type", "open_text")
        type_counts[t] = type_counts.get(t, 0) + 1

    try:
        return _llm_analyse(
            questions_json, survey_title, persona_name, persona_desc,
            n_q, n_required, type_counts,
        )
    except Exception as e:
        st.warning(f"AI analysis unavailable ({e}); using rule-based fallback.")
        return _mock_analyse(
            questions_json, survey_title, persona_name, persona_desc,
            n_q, n_required, type_counts,
        )


def _build_analysis_system_prompt() -> str:
    """
    System prompt for the analysis LLM call.
    Instructs the model to return a single strict JSON object.
    """
    return """
You are an expert survey UX auditor.
INPUT:  A JSON object containing:
  - "survey_title": string
  - "persona_name": string  (the simulated respondent type)
  - "persona_desc": string  (description of the persona)
  - "questions": array of question objects, each with:
      question_id, question_text, question_type, options, is_required

OUTPUT: A single JSON object (no markdown fences, no preamble) with exactly these keys:

{
  "score": <integer 0-100>,
  "grade": <"A"|"B"|"C"|"D">,
  "summary": <string: 2-3 sentence overall verdict from the persona's perspective>,
  "persona_journey": <string: step-by-step narrative of how this persona experiences the survey, using ASCII arrows like ->>,
  "friction_points": [
    {
      "q_id": <question_id string>,
      "q": <question_text string>,
      "issues": [<issue string>, ...]
    }
  ],
  "ambiguities": [<string>, ...],
  "improvements": [<string>, ...]
}

Scoring guide:
  90-100 = Excellent, minimal friction
  75-89  = Good, minor issues
  55-74  = Fair, noticeable problems
  below 55 = Poor, high drop-off risk

Rules:
- Evaluate strictly from the given persona's perspective.
- friction_points: only include questions that have real problems; omit clean ones.
- ambiguities: structural issues (scale labels, question order, logical gaps).
- improvements: 3-6 concrete, actionable suggestions prioritised for this persona.
- persona_journey: make it specific to the actual questions in the survey, not generic.
- Output ONLY the JSON object. No explanation outside the JSON.
""".strip()


def _llm_analyse(
        questions_json: list[dict],
        survey_title: str,
        persona_name: str,
        persona_desc: str,
        n_q: int,
        n_required: int,
        type_counts: dict,
) -> dict:
    """
    Call GLM API with the structured questions JSON and return a parsed report dict.
    Input:  questions_json (list of question dicts from convert_to_json)
    Output: report dict consumed by render_report()
    """
    API_KEY = st.secrets["ZHIPU_API_KEY"]
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    # Build the user message: give the model the full structured data
    user_payload = json.dumps({
        "survey_title": survey_title,
        "persona_name": persona_name,
        "persona_desc": persona_desc,
        "questions": questions_json,
    }, ensure_ascii=False)

    data = {
        "model": "GLM-4.6V-Flash",
        "messages": [
            {"role": "system", "content": _build_analysis_system_prompt()},
            {"role": "user", "content": user_payload},
        ],
        "stream": False,
        "thinking": {"type": "disabled"},
    }

    response = requests.post(url, headers=headers, json=data, timeout=120)
    result = response.json()

    print(f"{'=' * 10} step 3 result from {url} {'=' * 10}\n {result}")

    raw = result["choices"][0]["message"]["content"]

    # Strip accidental markdown fences
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    parsed = json.loads(text.strip())

    # Normalise: ensure all required keys exist and types match what render_report expects
    return {
        "score": int(parsed.get("score", 60)),
        "grade": parsed.get("grade", "C"),
        "summary": parsed.get("summary", ""),
        "persona_journey": parsed.get("persona_journey", ""),
        "friction_points": parsed.get("friction_points", []),
        "ambiguities": parsed.get("ambiguities", []),
        "improvements": parsed.get("improvements", []),
        "n_questions": n_q,
        "n_required": n_required,
        "type_counts": type_counts,
        "survey_title": survey_title,
    }


def _mock_analyse(
        questions_json: list[dict],
        survey_title: str,
        persona_name: str,
        persona_desc: str,
        n_q: int,
        n_required: int,
        type_counts: dict,
) -> dict:
    """
    Rule-based fallback used when the GLM API is unavailable.
    Mirrors the same output schema as _llm_analyse().
    """
    open_ratio = type_counts.get("open_text", 0) / max(n_q, 1)
    req_ratio = n_required / max(n_q, 1)

    score = 78
    if n_q > 20:
        score -= 15
    elif n_q > 12:
        score -= 7
    if open_ratio > 0.4: score -= 8
    if req_ratio > 0.8: score -= 6
    if type_counts.get("matrix", 0) > 3: score -= 7
    if "Gen Z" in persona_name and n_q > 10:                    score -= 8
    if "Elderly" in persona_name and open_ratio > 0.2:            score -= 10
    if "Expert" in persona_name and n_q < 5:                     score -= 5
    if "Non-Native" in persona_name:                                 score -= 5
    if "Mobile" in persona_name and type_counts.get("matrix", 0) > 0: score -= 10
    score = max(10, min(99, score))
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"

    vague_terms = ["good", "bad", "often", "sometimes", "appropriate", "relevant", "suitable", "adequate", "generally"]
    friction: list[dict] = []
    for q in questions_json[:20]:
        issues, q_text, q_lower = [], q["question_text"], q["question_text"].lower()
        q_type, opts = q["question_type"], q["options"]
        if sum(q_lower.count(f" {w} ") for w in ["and", "or"]) >= 2:
            issues.append("Possible double-barrelled question")
        found_vague = [w for w in vague_terms if w in q_lower]
        if found_vague: issues.append(f"Vague term(s): {', '.join(found_vague)}")
        if len(q_text.split()) > 20: issues.append("Question exceeds 20 words - consider simplifying")
        if q_type == "single_choice" and len(opts) > 7: issues.append(f"{len(opts)} options - consider a dropdown")
        if q_type == "matrix" and "Mobile" in persona_name: issues.append("Matrix renders poorly on small screens")
        if q_type == "open_text" and "Gen Z" in persona_name: issues.append("Open-text likely causes Gen Z abandonment")
        if q_type in ("open_text", "fill_in_blank") and q.get("is_required"): issues.append(
            "Required free-text - highest drop-off risk")
        if issues: friction.append({"q_id": q["question_id"], "q": q_text, "issues": issues})

    ambiguities = [
        f"{n_q} question(s) found ({n_required} required). Ideal: under 12, <=80% required.",
        f"Question types: {', '.join(f'{v}x {Q_TYPE_META.get(k, (k,))[0]}' for k, v in type_counts.items())}.",
    ]
    improvements = [
        "Add a progress bar so respondents know how far through they are.",
        "Replace open-ended boxes with structured options where possible.",
        "Group related questions into labelled sections.",
        "Test on mobile before launch - 60%+ of surveys are on phones.",
    ]
    journey_map = {
        "Impatient Gen Z": "**Opens link** -> scrolls to gauge length -> sees many questions -> *hesitates* -> hits open-text box -> **abandons**.",
        "Elderly with Poor Vision": "**Opens on tablet** -> text is small -> pinch-zooms -> layout breaks -> **submits partial response**.",
        "Rigorous Expert": "**Reads every word** -> spots undefined scale anchor -> **flags it** -> completes but *unlikely to recommend*.",
        "Non-Native English Speaker": "**Starts survey** -> hits idiomatic phrase -> **confusion** -> guesses -> *lower data quality*.",
        "Mobile-Only User": "**Opens on phone** -> matrix does not scroll -> **answers randomly** -> back button loses progress -> *abandons*.",
    }
    return {
        "score": score,
        "grade": grade,
        "summary": f"This survey scores {score}/100 (Grade {grade}) from a *{persona_name}* perspective. {len(friction)} friction point(s) found.",
        "persona_journey": journey_map.get(persona_name, "No journey map available."),
        "friction_points": friction,
        "ambiguities": ambiguities,
        "improvements": improvements,
        "n_questions": n_q,
        "n_required": n_required,
        "type_counts": type_counts,
        "survey_title": survey_title,
    }


#  SCROLLABLE QUESTIONNAIRE PANEL
#  (now renders from JSON, not from raw text)
def render_questionnaire_panel(questions_json: list[dict], title: str):
    """
    Render a fixed-height scrollable card panel inside a sandboxed iframe
    via st.components.v1.html().

    WHY components.v1.html instead of st.markdown(unsafe_allow_html=True):
      Streamlit's markdown renderer passes HTML through a sanitizer (DOMPurify)
      that silently truncates or drops content when the blob is large or contains
      non-ASCII characters (e.g. Chinese/Japanese/Korean text).  Using
      st.components.v1.html() bypasses the sanitizer entirely by rendering the
      HTML in an isolated iframe - every card is guaranteed to appear regardless
      of question count or character set.

    INPUT: questions_json - output of convert_to_json()
    """
    import streamlit.components.v1 as components

    n_q = len(questions_json)

    if n_q == 0:
        st.warning(
            "No questions extracted from this survey. "
            "The page may require JavaScript rendering - try pasting the direct form URL."
        )
        return

    # Build one card string per question.
    # Each piece of user-supplied text is HTML-escaped before insertion so
    # special characters (< > & " ') and CJK text are all safe.
    def _esc(s: str) -> str:
        return (s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    cards_html = ""
    for q in questions_json:
        q_id = _esc(q.get("question_id", "x"))
        q_text = _esc(q.get("question_text", ""))
        q_type = q.get("question_type", "open_text")
        opts = q.get("options", [])
        req = q.get("is_required", False)

        type_label, type_cls = Q_TYPE_META.get(q_type, (q_type, "q-type-ot"))
        req_html = '<span class="q-required">Required</span>' if req else ""

        opts_html = (
            "".join(f'<div class="q-opt">{_esc(o)}</div>' for o in opts)
            if opts
            else '<div class="q-no-opts">Free-text / scale response</div>'
        )

        cards_html += f"""
        <div class="q-item">
          <div class="q-meta">
            <span class="q-num">{q_id}</span>
            <span class="q-type {type_cls}">{type_label}</span>
            {req_html}
          </div>
          <div class="q-text">{q_text}</div>
          {opts_html}
        </div>"""

    # Full self-contained HTML document for the iframe.
    # The iframe has no access to the parent page's CSS, so all styles must be
    # redeclared inline here.  The outer <div id="panel"> acts as the
    # scrollable container (overflow-y: auto).  Height is set on the component
    # call below; the inner div fills 100% of that.
    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: #0f172a;
    font-family: 'DM Sans', sans-serif;
    padding: 0;
    margin: 0;
  }}

  #panel {{
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    padding: .8rem 1rem;
    background: #0f172a;
  }}

  /* Custom scrollbar */
  #panel::-webkit-scrollbar       {{ width: 6px; }}
  #panel::-webkit-scrollbar-track {{ background: #0f172a; border-radius: 4px; }}
  #panel::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
  #panel::-webkit-scrollbar-thumb:hover {{ background: #38bdf8; }}

  .q-item {{
    background: #1e293b;
    border-radius: 10px;
    padding: .85rem 1.05rem;
    margin-bottom: .6rem;
    border-left: 3px solid #38bdf8;
  }}

  .q-meta {{
    display: flex;
    align-items: center;
    gap: .45rem;
    flex-wrap: wrap;
    margin-bottom: .35rem;
  }}

  .q-num {{
    font-family: 'DM Mono', monospace;
    font-size: .68rem;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: .8px;
  }}

  .q-type {{
    font-size: .68rem;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 500;
  }}
  .q-type-sc  {{ background:#0c2340; color:#60a5fa; border:1px solid #1e3a5f; }}
  .q-type-mc  {{ background:#0d2b1d; color:#4ade80; border:1px solid #14532d; }}
  .q-type-mx  {{ background:#2a1a0d; color:#fb923c; border:1px solid #7c2d12; }}
  .q-type-fb  {{ background:#1a0a2e; color:#c084fc; border:1px solid #4a044e; }}
  .q-type-rt  {{ background:#2d1a00; color:#fbbf24; border:1px solid #78350f; }}
  .q-type-ot  {{ background:#1e1e1e; color:#94a3b8; border:1px solid #334155; }}

  .q-required {{
    font-size: .68rem;
    color: #f87171;
  }}

  .q-text {{
    color: #e2e8f0;
    font-size: .92rem;
    line-height: 1.55;
    margin-bottom: .4rem;
    word-break: break-word;
  }}

  .q-opt {{
    color: #64748b;
    font-size: .81rem;
    margin: .1rem 0 .1rem 1rem;
    word-break: break-word;
  }}
  .q-opt::before {{ content: "-"; color: #334155; }}

  .q-no-opts {{
    color: #334155;
    font-size: .78rem;
    font-style: italic;
    margin-left: 1rem;
  }}
</style>
</head>
<body>
<div id="panel">
{cards_html}
</div>
</body>
</html>"""

    # Fixed height - content overflows and the iframe scrollbar takes over.
    panel_height = 500

    components.html(full_html, height=panel_height, scrolling=True)



# STEP 4 - Render Report

def render_report(report: dict, persona_name: str, survey_url: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    st.markdown("## Diagnostic Report")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score",     f"{report['score']}/100")
    c2.metric("Grade",     report["grade"])
    c3.metric("Questions", report["n_questions"])
    c4.metric("Required",  f"{report['n_required']}/{report['n_questions']}")

    # Type breakdown chips
    chips = ""
    for k, v in report["type_counts"].items():
        label, cls = Q_TYPE_META.get(k, (k, "q-type-ot"))
        chips += f'<span class="q-type {cls}" style="margin:3px 3px 0 0">{v} x {label}</span>'

    st.markdown(f"""
    <div class="step-card" style="margin-top:.8rem">
      <h4>Audit Meta</h4>
      <p><strong>Survey:</strong> {report["survey_title"]}</p>
      <p><strong>Persona:</strong> {persona_name}</p>
      <p><strong>URL:</strong> <code style="font-size:.76rem">{survey_url}</code></p>
      <p><strong>Generated:</strong> {ts}</p>
      <p style="margin-top:.5rem">{chips}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(report["summary"])

    st.markdown("### Persona Journey")
    st.info(report["persona_journey"])

    st.markdown("### Friction Points")
    if report["friction_points"]:
        for fp in report["friction_points"]:
            label = f"{fp['q_id']}: {fp['q'][:72]}{'...' if len(fp['q'])>72 else ''}"
            with st.expander(label):
                for issue in fp["issues"]:
                    st.warning(f"- {issue}")
    else:
        st.success("No major friction points detected.")

    st.markdown("### Structural Concerns")
    for amb in report["ambiguities"]:
        st.markdown(f"- {amb}")

    st.markdown("### Improvements")
    for idx, imp in enumerate(report["improvements"], 1):
        st.markdown(f"**{idx}.** {imp}")

    # Download
    md = _build_markdown_report(report, persona_name, survey_url, ts)
    st.download_button(
        label="Download Report (.md)",
        data=md.encode("utf-8"),
        file_name=f"survey_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True,
    )


def _build_markdown_report(report, persona, url, ts) -> str:
    lines = [
        "# Survey Diagnostic Report", "",
        "| Field | Value |", "|---|---|",
        f"| Survey | {report['survey_title']} |",
        f"| URL | {url} |",
        f"| Persona | {persona} |",
        f"| Score | {report['score']}/100 (Grade {report['grade']}) |",
        f"| Questions | {report['n_questions']} ({report['n_required']} required) |",
        f"| Generated | {ts} |", "",
        "## Summary", "", report["summary"], "",
        "## Persona Journey Map", "", report["persona_journey"], "",
        "## Friction Points", "",
    ]
    if report["friction_points"]:
        for fp in report["friction_points"]:
            lines.append(f"**{fp['q_id']}:** {fp['q']}")
            lines += [f"- {i}" for i in fp["issues"]]
            lines.append("")
    else:
        lines += ["No major friction points detected.", ""]
    lines += [
        "## Structural Concerns", "",
        *[f"- {a}" for a in report["ambiguities"]], "",
        "## Improvements", "",
        *[f"{i+1}. {s}" for i, s in enumerate(report["improvements"])], "",
        "---", "*Generated by AI Survey QR Audit Tool - diagnostic purposes only.*",
    ]
    return "\n".join(lines)


# SHARED PIPELINE

def run_pipeline(survey_url: str, selected_persona: str) -> Optional[tuple]:
    """
    Full pipeline:
      scrape_survey()   -> raw Markdown
      convert_to_json() -> structured question list
      call_ai_agent()   -> report dict

    Returns (questions_json, raw_md, title, report) or None on error.
    """
    progress = st.progress(0, text="Initialising...")

    # Step 1: scrape
    with st.spinner("Fetching survey content via Jina AI Reader..."):
        try:
            raw_md = scrape_survey(survey_url)
            progress.progress(30, text="Step 1/3 - Markdown fetched")
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch survey content: {e}")
            progress.empty()
            return None

    # Step 2: Markdown -> JSON
    with st.spinner("Converting Markdown to structured JSON..."):
        questions_json = convert_to_json(raw_md)
        global G_LATEST_QUESTIONS_JSON
        G_LATEST_QUESTIONS_JSON = questions_json
        n_q = len(questions_json)
        progress.progress(65, text="Step 2/3 - JSON structure built")

    # Extract title from raw Markdown (for display)
    title_m = re.search(r'^#{1,2}\s+(.+)', raw_md, re.MULTILINE)
    title   = title_m.group(1).strip() if title_m else "Untitled Survey"

    st.success(
        f"Survey parsed: **{n_q} question(s)** extracted as structured JSON"
    )

    # Step 3: analyse
    with st.spinner(f"Analysing with persona '{selected_persona}'..."):
        time.sleep(0.4)
        report = call_ai_agent(
            questions_json,
            title,
            selected_persona,
            PERSONAS[selected_persona],
        )
        progress.progress(100, text="Step 3/3 - Analysis complete")
        time.sleep(0.35)
        progress.empty()

    return questions_json, raw_md, title, report


# SIDEBAR

with st.sidebar:
    st.markdown("### Simulated Persona")
    selected_persona = st.selectbox(
        "Persona", options=list(PERSONAS.keys()), index=0,
        label_visibility="collapsed",
    )
    st.markdown(f"*{PERSONAS[selected_persona]}*")

    st.markdown("---")
    st.markdown("### Pipeline")
    for icon, label in [
        ("1", "QR screenshot **or** URL input"),
        ("2", "Jina AI Reader -> **Markdown**"),
        ("3", "LLM conversion -> **structured JSON**"),
        ("4", "AI analysis on **JSON data**"),
        ("5", "Scrollable questionnaire + report"),
    ]:
        st.markdown(
            f'<div class="pipe-step">'
            f'<span class="pipe-icon">{icon}</span>'
            f'<span class="pipe-label">{label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        "<div class='disclaimer' style='text-align:left;margin-top:0'>"
        "No survey response data is stored.<br>"
        "Analysis runs on scraped public content only."
        "</div>",
        unsafe_allow_html=True,
    )


# MAIN PAGE

st.markdown(
    """
    <div class="hero-banner">
      <div class="hero-badge">AI-Powered | MVP v0.3</div>
      <h1>AI Survey QR Code Instant Audit</h1>
      <p>Upload a QR-code screenshot <em>or</em> paste a direct survey URL. Jina AI Reader scrapes the content, an LLM converts it to structured JSON,
      then the AI diagnoses friction and ambiguity through the eyes of your
      chosen respondent persona.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Session state
for key in ("questions_json", "raw_md", "title", "report", "survey_url"):
    if key not in st.session_state:
        st.session_state[key] = None

if "answers_api_started" not in st.session_state:
    ensure_answer_api_running()
    st.session_state.answers_api_started = True

# Dual input tabs
tab_qr, tab_url = st.tabs(["QR Code Screenshot", "Paste Survey URL"])

# Tab 1: QR screenshot
with tab_qr:
    uploaded_file = st.file_uploader(
        "Drag & drop a screenshot containing a survey QR code",
        type=["png", "jpg", "jpeg", "webp", "bmp"],
        key="qr_uploader",
    )
    if uploaded_file is not None:
        img_col, status_col = st.columns([1, 2])
        with img_col:
            st.image(uploaded_file, caption="Uploaded screenshot", use_container_width=True)
        with status_col:
            st.markdown("#### Processing")
            with st.spinner("Scanning for QR code..."):
                uploaded_file.seek(0)
                decoded_url = decode_qr(uploaded_file)
            if not decoded_url:
                st.error(
                    "No valid QR code detected. Ensure the image is clear, "
                    "or switch to the **Paste Survey URL** tab."
                )
            else:
                st.success(f"QR Decoded: `{decoded_url}`")
                result = run_pipeline(decoded_url, selected_persona)
                if result:
                    st.session_state.questions_json = result[0]
                    st.session_state.raw_md         = result[1]
                    st.session_state.title          = result[2]
                    st.session_state.report         = result[3]
                    st.session_state.survey_url     = decoded_url

# Tab 2: Direct URL
with tab_url:
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        raw_url = st.text_input(
            "Survey URL",
            placeholder="https://forms.google.com/... or typeform.com/...",
            label_visibility="collapsed",
            key="url_input",
        )
    with col_btn:
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        run_btn = st.button("Audit", use_container_width=True, type="primary", key="url_btn")

    if run_btn:
        if not raw_url:
            st.warning("Please enter a URL first.")
        else:
            validated = normalise_url(raw_url)
            if not validated:
                st.error("Not a valid URL - include the full address, e.g. https://example.com/survey")
            else:
                st.success(f"URL accepted: `{validated}`")
                result = run_pipeline(validated, selected_persona)
                if result:
                    st.session_state.questions_json = result[0]
                    st.session_state.raw_md         = result[1]
                    st.session_state.title          = result[2]
                    st.session_state.report         = result[3]
                    st.session_state.survey_url     = validated


# OUTPUT AREA

if st.session_state.report is not None:
    qj    = st.session_state.questions_json
    rpt   = st.session_state.report
    s_url = st.session_state.survey_url
    title = st.session_state.title

    st.markdown("---")
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        st.markdown(
            f"### Full Questionnaire"
            f"<span style='font-size:.8rem;color:#64748b;font-weight:400'>"
            f"  {len(qj)} question(s) | scroll to read all"
            f"</span>",
            unsafe_allow_html=True,
        )
        render_questionnaire_panel(qj, title)

        # Debug / inspection expanders
        with st.expander("View structured JSON (convert_to_json output)"):
            st.json(qj)

        with st.expander("View raw scraped Markdown"):
            raw_preview = st.session_state.raw_md or ""
            if len(raw_preview) > 6000:
                raw_preview = raw_preview[:6000] + "\n\n[truncated]"
            st.text_area("raw", value=raw_preview, height=260,
                         disabled=True, label_visibility="collapsed")

    with right_col:
        render_report(rpt, selected_persona, s_url)

else:
    st.markdown(
        """
        <div style="text-align:center; padding:3rem 0; color:#475569;">
          <div style="font-size:3.5rem">QR</div>
          <p style="font-size:1.1rem; margin-top:.6rem">
            Upload a QR-code screenshot or paste a survey URL above to begin.
          </p>
          <p style="font-size:.85rem; color:#334155">
            Supports Google Forms | Typeform | SurveyMonkey | Qualtrics | and more
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Disclaimer
st.markdown(
    "<div class='disclaimer'>"
    "<strong>Privacy Notice</strong>: This tool is for survey logic diagnosis only. "
    "No raw response data is stored. Scraped content is processed in-memory and "
    "discarded after the session ends."
    "</div>",
    unsafe_allow_html=True,
)


