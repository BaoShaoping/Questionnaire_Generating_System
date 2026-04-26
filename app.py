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
import time
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
import requests
import streamlit as st
from pyzbar import pyzbar
from PIL import Image

# PAGE CONFIG  (must be the very first st call)
st.set_page_config(
    page_title="AI问卷诊断",
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


#  CONSTANTS

PERSONAS = {
    "急躁型Z世代":
        "20 岁左右，超过 90 秒就容易放弃，讨厌大段文字，希望信息像短视频一样直给清晰。",
    "视力较弱的长者":
        "72 岁左右，有轻度老花，阅读速度较慢，不喜欢术语，也不太习惯用智能手机。",
    "严谨型专家":
        "博士或研究人员，会仔细检查每个模糊表述，能立刻发现诱导性问题，并期待平衡的量表设计。",
    "非英语母语用户":
        "母语为中文。遇到英语习语、缩写或强文化背景表达时，更容易产生理解障碍。",
    "仅使用手机的用户":
        "在 5 英寸左右的手机上单手填写问卷。长矩阵题和过小的点击区域会明显增加痛点。",
}

JINA_BASE = "https://r.jina.ai/"

# Mapping from internal type key to human-readable label + CSS class
Q_TYPE_META = {
    "single_choice":   ("单选题",   "q-type-sc"),
    "multiple_choice": ("多选题",   "q-type-mc"),
    "matrix":          ("矩阵题",   "q-type-mx"),
    "fill_in_blank":   ("填空题",   "q-type-fb"),
    "rating":          ("评分题",   "q-type-rt"),
    "open_text":       ("开放题",   "q-type-ot"),
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


def _split_pipe_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _is_pipe_divider_row(cells: list[str]) -> bool:
    return bool(cells) and all(
        not cell or re.fullmatch(r":?-{3,}:?", cell)
        for cell in cells
    )


def _is_matrix_header_row(cells: list[str], *, _numeric_re=re.compile(r"^\d+$")) -> bool:
    """Return True if *cells* looks like the column-header row of a matrix question.

    Handles:
    - Chinese Likert labels (非常同意 / 满意 / …)
    - Pure numeric scales (1 2 3 4 5, or 1~5, etc.)
    - Mixed short-label scales (e.g. "Very low | Low | Medium | High | Very high")
    """
    nonempty = [cell for cell in cells if cell]
    if len(nonempty) < 2:
        return False

    joined = "|".join(nonempty)

    # 1. Chinese Likert keywords
    chinese_header_tokens = (
        "非常不同意", "不同意", "一般", "同意", "非常同意",
        "非常不满意", "不满意", "满意", "非常满意",
        "完全不同意", "完全同意", "中立",
    )
    if any(token in joined for token in chinese_header_tokens):
        return True

    # 2. All non-empty cells are plain integers → numeric scale (1 2 3 4 5)
    if all(_numeric_re.fullmatch(cell) for cell in nonempty):
        return True

    # 3. Consecutive integer range written as a single token (e.g. "1~5", "1-5")
    if len(nonempty) == 1 and re.fullmatch(r"\d+[~\-]\d+", nonempty[0]):
        return True

    # 4. English / generic Likert-style short labels
    english_header_tokens = (
        "strongly disagree", "disagree", "neutral", "agree", "strongly agree",
        "very dissatisfied", "dissatisfied", "satisfied", "very satisfied",
        "never", "rarely", "sometimes", "often", "always",
        "not at all", "slightly", "moderately", "very much", "extremely",
    )
    joined_lower = joined.lower()
    if any(token in joined_lower for token in english_header_tokens):
        return True

    # 5. Heuristic: ≥3 cells, all short (≤6 chars), not all identical
    #    Catches unlabelled or custom-label scales without hard-coding every variant.
    if len(nonempty) >= 3 and all(len(cell) <= 6 for cell in nonempty):
        if len(set(nonempty)) > 1:
            return True

    return False

def _normalize_matrix_table(table_lines: list[str]) -> str:
    """Compress Jina's duplicated matrix table rows into a compact text block."""
    columns: list[str] = []
    rows: list[str] = []
    seen_rows: set[str] = set()

    for raw_line in table_lines:
        clean_line = re.sub(r"\[\]\(https?://[^)]+\)", "", raw_line).strip()
        cells = _split_pipe_cells(clean_line)
        if not cells or _is_pipe_divider_row(cells):
            continue

        if _is_matrix_header_row(cells):
            columns = [cell for cell in cells if cell]
            continue

        first = cells[0].strip() if cells else ""
        if not first:
            continue

        row_text = re.sub(r"\s+", " ", first).strip()
        if row_text and row_text not in seen_rows:
            seen_rows.add(row_text)
            rows.append(row_text)

    if not columns or not rows:
        return "\n".join(table_lines)

    normalized = [
        "[Matrix]",
        f"columns: {' | '.join(columns)}",
        "rows:",
        *[f"- {row}" for row in rows],
        "[/Matrix]",
    ]
    return "\n".join(normalized)


def normalize_jina_markdown(markdown_text: str) -> str:
    """
    Clean Jina markdown before LLM parsing.

    Focus on matrix blocks because Jina expands them into duplicated rows plus
    empty link placeholders, which wastes tokens and obscures the row structure.
    """
    text = markdown_text.replace("\r\n", "\n").replace("\ufeff", "")

    metadata_marker = "Markdown Content:"
    if metadata_marker in text:
        text = text.split(metadata_marker, 1)[1].lstrip("\n")

    lines = text.split("\n")
    normalized_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        cells = _split_pipe_cells(line)
        if cells and _is_matrix_header_row(cells):
            table_lines: list[str] = []
            while i < len(lines):
                current = lines[i].strip()
                if not current.startswith("|"):
                    break
                table_lines.append(lines[i])
                i += 1
            normalized_lines.append(_normalize_matrix_table(table_lines))
            continue

        normalized_lines.append(line)
        i += 1

    text = "\n".join(normalized_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_survey_title(raw_markdown: str, normalized_markdown: str) -> str:
    title_match = re.search(r"^Title:\s*(.+)$", raw_markdown, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()

    heading_match = re.search(r"^#{1,2}\s+(.+)$", normalized_markdown, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()

    return "未命名问卷"


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _extract_json_object_candidate(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return text.strip()

    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:].strip()


def _repair_json_with_llm(bad_json_text: str, expected_top_key: str) -> str:
    api_key = st.secrets["ZHIPU_API_KEY"]
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "GLM-4.5-air",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You repair malformed JSON. "
                    "Return ONLY one valid JSON object. "
                    f'The top-level object must still contain the key "{expected_top_key}". '
                    "Do not summarize, explain, or drop fields unless required to make the JSON valid."
                ),
            },
            {"role": "user", "content": bad_json_text[:20000]},
        ],
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    response = requests.post(url, headers=headers, json=data, timeout=120)
    result = response.json()
    print(f"{'=' * 10} using LLM to repair Json output {'=' * 10}\n {result}")
    repaired = result["choices"][0]["message"]["content"]
    return _strip_markdown_fences(repaired)


def _parse_llm_json_object(raw_text: str, expected_top_key: str) -> dict:
    text = _strip_markdown_fences(raw_text)
    candidate = _extract_json_object_candidate(text)

    attempts = [
        candidate,
        re.sub(r",(\s*[}\]])", r"\1", candidate),
    ]

    last_error = None
    for attempt in attempts:
        try:
            parsed = json.loads(attempt)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as exc:
            last_error = exc

    repaired = _repair_json_with_llm(candidate, expected_top_key)
    parsed = json.loads(_extract_json_object_candidate(repaired))
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON repair did not return an object")
    return parsed


def extract_matrix_blocks(normalized_markdown: str) -> list[dict]:
    """Extract matrix stems, columns, and rows from normalized markdown."""
    lines = normalized_markdown.splitlines()
    blocks: list[dict] = []

    i = 0
    while i < len(lines):
        if lines[i].strip() != "[Matrix]":
            i += 1
            continue

        stem = ""
        j = i - 1
        while j >= 0:
            candidate = lines[j].strip()
            if candidate and not candidate.startswith(("*", "[/", "[")):
                stem = candidate
                break
            j -= 1

        columns: list[str] = []
        rows: list[str] = []
        i += 1
        while i < len(lines) and lines[i].strip() != "[/Matrix]":
            current = lines[i].strip()
            if current.startswith("columns:"):
                columns = [part.strip() for part in current.split(":", 1)[1].split("|") if part.strip()]
            elif current.startswith("- "):
                rows.append(current[2:].strip())
            i += 1

        if stem or columns or rows:
            blocks.append({
                "question_text": stem,
                "options": columns,
                "matrix_rows": rows,
            })
        i += 1

    return blocks


def enrich_questions_with_matrix_rows(questions: list[dict], normalized_markdown: str) -> list[dict]:
    """Inject matrix row details deterministically from normalized markdown."""
    matrix_blocks = extract_matrix_blocks(normalized_markdown)
    if not matrix_blocks or not isinstance(questions, list):
        return questions

    next_block_idx = 0
    for question in questions:
        if not isinstance(question, dict):
            continue

        if question.get("question_type") != "matrix":
            continue

        matched_idx = None
        q_text = str(question.get("question_text", "")).strip()
        for block_idx in range(next_block_idx, len(matrix_blocks)):
            block = matrix_blocks[block_idx]
            stem = block.get("question_text", "")
            if stem and (stem in q_text or q_text in stem):
                matched_idx = block_idx
                break

        if matched_idx is None and next_block_idx < len(matrix_blocks):
            matched_idx = next_block_idx

        if matched_idx is None:
            continue

        block = matrix_blocks[matched_idx]
        next_block_idx = matched_idx + 1

        if block.get("question_text"):
            question["question_text"] = block["question_text"]
        if block.get("options"):
            question["options"] = block["options"]
        question["matrix_rows"] = block.get("matrix_rows", [])

    return questions


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
    # # Strip accidental markdown.txt fences the model might add
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
        "model": "GLM-4.5-air",
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
        parsed = _parse_llm_json_object(raw_json, "questions")
        _questions = parsed.get("questions", [])
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
  "matrix_rows"   : ["<row1>", "..."], // only for matrix questions, else omit
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
- Output ONLY the JSON object. No preamble, no markdown.txt fences, no explanation.
- If a question's type is ambiguous, choose the closest match.
- Ignore navigation text, progress bars, page titles, and form submit buttons.
- Preserve the original question wording exactly.
- If the input contains a [Matrix] ... [/Matrix] block, treat "columns:" as the shared scale options.
- For matrix questions, preserve every row item in matrix_rows and keep the stem in question_text.
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
      - matrix_rows (matrix only)
      - is_required
    """
    # Try real LLM first; fall back to mock on any error.
    try:
        questions = _llm_convert(markdown_text)
    except Exception:
        questions = _mock_convert(markdown_text)  # Missing key, network error, JSON parse error, etc.

    return enrich_questions_with_matrix_rows(questions, markdown_text)


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
        st.warning(f"AI 分析暂不可用（{e}）；已切换到规则兜底分析。")
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
      question_id, question_text, question_type, options, matrix_rows, is_required

OUTPUT: A single JSON object (no markdown.txt fences, no preamble) with exactly these keys:

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
- All natural-language output fields must be in Simplified Chinese.
- Output ONLY the JSON object. No explanation outside the JSON.
- In natural-language Chinese text fields, do not use double quotes inside strings.
  Use Chinese quotation marks or no quotes instead.
- Unescaped double quotes (") are forbidden inside all JSON strings.
Wrong example: "He said" hello ""
Correct example: "He says \\" Hello \\""
If you need a quotation, use the Chinese quotation mark "" or" "or single quotation mark instead, for example:
Correct demonstration: "He said 「你好」"
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
        "model": "GLM-4.5-air",
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

    parsed = _parse_llm_json_object(raw, "score")

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
    if "Z世代" in persona_name and n_q > 10:                       score -= 8
    if "长者" in persona_name and open_ratio > 0.2:                 score -= 10
    if "专家" in persona_name and n_q < 5:                         score -= 5
    if "非英语母语" in persona_name:                                  score -= 5
    if "手机" in persona_name and type_counts.get("matrix", 0) > 0: score -= 10
    score = max(10, min(99, score))
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"

    vague_terms = ["good", "bad", "often", "sometimes", "appropriate", "relevant", "suitable", "adequate", "generally"]
    friction: list[dict] = []
    for q in questions_json[:20]:
        issues, q_text, q_lower = [], q["question_text"], q["question_text"].lower()
        q_type, opts = q["question_type"], q["options"]
        if sum(q_lower.count(f" {w} ") for w in ["and", "or"]) >= 2:
            issues.append("可能是双重问题，用户一次被要求回答两个点")
        found_vague = [w for w in vague_terms if w in q_lower]
        if found_vague: issues.append(f"存在模糊词：{', '.join(found_vague)}")
        if len(q_text.split()) > 20: issues.append("题干超过 20 个词，建议进一步精简")
        if q_type == "single_choice" and len(opts) > 7: issues.append(f"选项达到 {len(opts)} 个，建议改为下拉框或拆分")
        if q_type == "matrix" and "手机" in persona_name: issues.append("矩阵题在小屏手机上可读性和可操作性较差")
        if q_type == "open_text" and "Z世代" in persona_name: issues.append("开放题更容易让 Z 世代用户中途放弃")
        if q_type in ("open_text", "fill_in_blank") and q.get("is_required"): issues.append(
            "必填自由输入题，流失风险最高")
        if issues: friction.append({"q_id": q["question_id"], "q": q_text, "issues": issues})

    ambiguities = [
        f"共识别到 {n_q} 题，其中必答 {n_required} 题。理想状态建议控制在 12 题以内，且必答占比不超过 80%。",
        f"题型分布：{', '.join(f'{v} 题 {Q_TYPE_META.get(k, (k,))[0]}' for k, v in type_counts.items())}。",
    ]
    improvements = [
        "增加进度条，让填写者始终知道还剩多少内容。",
        "在可行情况下，用结构化选项替代开放式输入框。",
        "把相关问题按主题分组，并增加清晰的小节标题。",
        "上线前务必做手机端测试，问卷访问中手机占比通常很高。",
    ]
    journey_map = {
        "急躁型Z世代": "**打开链接** -> 先扫一眼长度 -> 看到题目很多 -> *开始犹豫* -> 遇到开放题 -> **直接退出**。",
        "视力较弱的长者": "**在平板上打开** -> 字体偏小 -> 放大阅读 -> 布局开始变形 -> **最终只提交了部分内容**。",
        "严谨型专家": "**逐字阅读** -> 发现量表锚点定义不清 -> **立刻标记问题** -> 虽然填完，但 *不太愿意推荐这份问卷*。",
        "非英语母语用户": "**开始作答** -> 遇到带习语的表达 -> **产生困惑** -> 靠猜测继续 -> *数据质量下降*。",
        "仅使用手机的用户": "**在手机上打开** -> 矩阵题无法顺畅浏览 -> **开始随意作答** -> 返回时进度还可能丢失 -> *最终放弃*。",
    }
    return {
        "score": score,
        "grade": grade,
        "summary": f"从 *{persona_name}* 视角看，这份问卷得分为 {score}/100（等级 {grade}）。共识别出 {len(friction)} 处明显摩擦点。",
        "persona_journey": journey_map.get(persona_name, "当前角色暂无对应的体验路径描述。"),
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

    WHY components.v1.html instead of st.markdown.txt(unsafe_allow_html=True):
      Streamlit's markdown.txt renderer passes HTML through a sanitizer (DOMPurify)
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
            "未能从该问卷中提取到题目。"
            "该页面可能依赖 JavaScript 渲染，建议直接粘贴表单链接再试一次。"
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
        matrix_rows = q.get("matrix_rows", [])
        req = q.get("is_required", False)

        type_label, type_cls = Q_TYPE_META.get(q_type, (q_type, "q-type-ot"))
        req_html = '<span class="q-required">必答</span>' if req else ""

        opts_html = (
            "".join(f'<div class="q-opt">{_esc(o)}</div>' for o in opts)
            if opts
            else '<div class="q-no-opts">自由填写 / 量表作答</div>'
        )
        if q_type == "matrix" and matrix_rows:
            rows_html = "".join(f'<div class="q-opt">{_esc(row)}</div>' for row in matrix_rows)
            opts_html = (
                '<div class="q-no-opts">量表选项：</div>'
                + "".join(f'<div class="q-opt">{_esc(o)}</div>' for o in opts)
                + '<div class="q-no-opts" style="margin-top:.5rem">量表条目：</div>'
                + rows_html
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

    st.markdown("## 诊断报告")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("得分",     f"{report['score']}/100")
    c2.metric("等级",     report["grade"])
    c3.metric("题目数", report["n_questions"])
    c4.metric("必答题",  f"{report['n_required']}/{report['n_questions']}")

    # Type breakdown chips
    chips = ""
    for k, v in report["type_counts"].items():
        label, cls = Q_TYPE_META.get(k, (k, "q-type-ot"))
        chips += f'<span class="q-type {cls}" style="margin:3px 3px 0 0">{v} x {label}</span>'

    st.markdown(f"""
    <div class="step-card" style="margin-top:.8rem">
      <h4>诊断信息</h4>
      <p><strong>问卷：</strong> {report["survey_title"]}</p>
      <p><strong>角色：</strong> {persona_name}</p>
      <p><strong>链接：</strong> <code style="font-size:.76rem">{survey_url}</code></p>
      <p><strong>生成时间：</strong> {ts}</p>
      <p style="margin-top:.5rem">{chips}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(report["summary"])

    st.markdown("### 用户体验路径")
    st.info(report["persona_journey"])

    st.markdown("### 摩擦点")
    if report["friction_points"]:
        for fp in report["friction_points"]:
            label = f"{fp['q_id']}: {fp['q'][:72]}{'...' if len(fp['q'])>72 else ''}"
            with st.expander(label):
                for issue in fp["issues"]:
                    st.warning(f"- {issue}")
    else:
        st.success("暂未发现明显的关键摩擦点。")

    st.markdown("### 结构性问题")
    for amb in report["ambiguities"]:
        st.markdown(f"- {amb}")

    st.markdown("### 优化建议")
    for idx, imp in enumerate(report["improvements"], 1):
        st.markdown(f"**{idx}.** {imp}")

    # Download
    md = _build_markdown_report(report, persona_name, survey_url, ts)
    st.download_button(
        label="下载报告（.md）",
        data=md.encode("utf-8"),
        file_name=f"问卷诊断报告_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown.txt",
        use_container_width=True,
    )


def _build_markdown_report(report, persona, url, ts) -> str:
    lines = [
        "# 问卷诊断报告", "",
        "| 字段 | 内容 |", "|---|---|",
        f"| 问卷 | {report['survey_title']} |",
        f"| 链接 | {url} |",
        f"| 角色 | {persona} |",
        f"| 得分 | {report['score']}/100（等级 {report['grade']}） |",
        f"| 题目数 | {report['n_questions']}（必答 {report['n_required']}） |",
        f"| 生成时间 | {ts} |", "",
        "## 总结", "", report["summary"], "",
        "## 用户体验路径", "", report["persona_journey"], "",
        "## 摩擦点", "",
    ]
    if report["friction_points"]:
        for fp in report["friction_points"]:
            lines.append(f"**{fp['q_id']}:** {fp['q']}")
            lines += [f"- {i}" for i in fp["issues"]]
            lines.append("")
    else:
        lines += ["暂未发现明显的关键摩擦点。", ""]
    lines += [
        "## 结构性问题", "",
        *[f"- {a}" for a in report["ambiguities"]], "",
        "## 优化建议", "",
        *[f"{i+1}. {s}" for i, s in enumerate(report["improvements"])], "",
        "---", "*由 AI 问卷二维码诊断工具生成，仅供问卷体验诊断参考。*",
    ]
    return "\n".join(lines)


# SHARED PIPELINE

def run_pipeline(survey_url: str, selected_persona: str) -> Optional[tuple]:
    """
    Full pipeline:
      scrape_survey()             -> raw Markdown
      normalize_jina_markdown()  -> cleaned Markdown
      convert_to_json()          -> structured question list
      call_ai_agent()            -> report dict

    Returns (questions_json, raw_md, normalized_md, title, report) or None on error.
    """
    progress = st.progress(0, text="正在初始化...")

    # Step 1: scrape
    with st.spinner("正在通过 Jina AI Reader 抓取问卷内容..."):
        try:
            raw_md = scrape_survey(survey_url)
            progress.progress(30, text="步骤 1/3 - 已获取 Markdown")
        except requests.exceptions.RequestException as e:
            st.error(f"抓取问卷内容失败：{e}")
            progress.empty()
            return None

    # Step 2: Markdown -> JSON
    with st.spinner("正在把 Markdown 转换为结构化 JSON..."):
        normalized_md = normalize_jina_markdown(raw_md)
        questions_json = convert_to_json(normalized_md)
        n_q = len(questions_json)
        progress.progress(65, text="步骤 2/3 - 已构建 JSON 结构")

    title = extract_survey_title(raw_md, normalized_md)

    st.success(
        f"问卷解析完成：已提取 **{n_q} 道题目** 并转换为结构化 JSON"
    )

    # Step 3: analyse
    with st.spinner(f"正在以“{selected_persona}”视角进行分析..."):
        time.sleep(0.4)
        report = call_ai_agent(
            questions_json,
            title,
            selected_persona,
            PERSONAS[selected_persona],
        )
        progress.progress(100, text="步骤 3/3 - 分析完成")
        time.sleep(0.35)
        progress.empty()

    return questions_json, raw_md, normalized_md, title, report


# SIDEBAR

with st.sidebar:
    st.markdown("### 模拟用户画像")
    selected_persona = st.selectbox(
        "用户画像", options=list(PERSONAS.keys()), index=0,
        label_visibility="collapsed",
    )
    st.markdown(f"*{PERSONAS[selected_persona]}*")

    st.markdown("---")
    st.markdown("### 流程")
    for icon, label in [
        ("1", "上传二维码截图 或 粘贴问卷链接"),
        ("2", "Jina AI Reader -> Markdown"),
        ("3", "LLM 转换 -> 结构化 JSON"),
        ("4", "基于 JSON 数据 进行 AI 分析"),
        ("5", "展示可滚动问卷内容 + 诊断报告"),
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
        "不会存储任何问卷作答数据。<br>"
        "分析仅基于抓取到的公开问卷内容。"
        "</div>",
        unsafe_allow_html=True,
    )


# MAIN PAGE

st.markdown(
    """
    <div class="hero-banner">
      <div class="hero-badge">AI 驱动 | MVP v0.3</div>
      <h1>AI 问卷二维码即时诊断</h1>
      <p>上传问卷二维码截图 <em>或</em> 直接粘贴问卷链接。系统会先通过 Jina AI Reader 抓取页面内容，再由大模型转换为结构化 JSON，
      最后从你选择的用户画像视角识别问卷中的摩擦点、歧义和体验风险。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Session state
for key in ("questions_json", "raw_md", "normalized_md", "title", "report", "survey_url"):
    if key not in st.session_state:
        st.session_state[key] = None


# Dual input tabs
tab_qr, tab_url = st.tabs(["二维码截图", "粘贴问卷链接"])

# Tab 1: QR screenshot
with tab_qr:
    uploaded_file = st.file_uploader(
        "拖拽或上传包含问卷二维码的截图",
        type=["png", "jpg", "jpeg", "webp", "bmp"],
        key="qr_uploader",
    )
    if uploaded_file is not None:
        img_col, status_col = st.columns([1, 2])
        with img_col:
            st.image(uploaded_file, caption="已上传截图", use_container_width=True)
        with status_col:
            st.markdown("#### 处理中")
            with st.spinner("正在识别二维码..."):
                uploaded_file.seek(0)
                decoded_url = decode_qr(uploaded_file)
            if not decoded_url:
                st.error(
                    "未识别到有效二维码。请确认图片清晰，"
                    "或切换到 **粘贴问卷链接** 标签页。"
                )
            else:
                st.success(f"二维码识别成功：`{decoded_url}`")
                result = run_pipeline(decoded_url, selected_persona)
                if result:
                    st.session_state.questions_json = result[0]
                    st.session_state.raw_md         = result[1]
                    st.session_state.normalized_md  = result[2]
                    st.session_state.title          = result[3]
                    st.session_state.report         = result[4]
                    st.session_state.survey_url     = decoded_url

# Tab 2: Direct URL
with tab_url:
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        raw_url = st.text_input(
            "问卷链接",
            placeholder="例如：https://forms.google.com/... 或 typeform.com/...",
            label_visibility="collapsed",
            key="url_input",
        )
    with col_btn:
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        run_btn = st.button("开始诊断", use_container_width=True, type="primary", key="url_btn")

    if run_btn:
        if not raw_url:
            st.warning("请先输入问卷链接。")
        else:
            validated = normalise_url(raw_url)
            if not validated:
                st.error("链接格式无效，请输入完整地址，例如 https://example.com/survey")
            else:
                st.success(f"链接已接受：`{validated}`")
                result = run_pipeline(validated, selected_persona)
                if result:
                    st.session_state.questions_json = result[0]
                    st.session_state.raw_md         = result[1]
                    st.session_state.normalized_md  = result[2]
                    st.session_state.title          = result[3]
                    st.session_state.report         = result[4]
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
            f"### 问卷全文"
            f"<span style='font-size:.8rem;color:#64748b;font-weight:400'>"
            f"  共 {len(qj)} 题 | 可滚动查看全部内容"
            f"</span>",
            unsafe_allow_html=True,
        )
        render_questionnaire_panel(qj, title)

        # Debug / inspection expanders
        with st.expander("查看结构化 JSON（convert_to_json 输出）"):
            st.json(qj)

        with st.expander("查看抓取到的原始 Markdown"):
            raw_preview = st.session_state.raw_md or ""
            if len(raw_preview) > 6000:
                raw_preview = raw_preview[:6000] + "\n\n[内容已截断]"
            st.text_area("raw", value=raw_preview, height=260,
                         disabled=True, label_visibility="collapsed")

        with st.expander("查看规范化后的 Markdown"):
            normalized_preview = st.session_state.normalized_md or ""
            if len(normalized_preview) > 6000:
                normalized_preview = normalized_preview[:6000] + "\n\n[内容已截断]"
            st.text_area("normalized", value=normalized_preview, height=260,
                         disabled=True, label_visibility="collapsed")

    with right_col:
        render_report(rpt, selected_persona, s_url)

else:
    st.markdown(
        """
        <div style="text-align:center; padding:3rem 0; color:#475569;">
          <div style="font-size:3.5rem">QR</div>
          <p style="font-size:1.1rem; margin-top:.6rem">
            上传问卷二维码截图，或在上方粘贴问卷链接，即可开始诊断。
          </p>
          <p style="font-size:.85rem; color:#334155">
            支持 Google Forms、Typeform、SurveyMonkey、Qualtrics 等常见问卷平台
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Disclaimer
st.markdown(
    "<div class='disclaimer'>"
    "<strong>隐私说明</strong>：本工具仅用于问卷逻辑与体验诊断。"
    "不会存储原始作答数据，抓取到的内容仅在内存中处理，并会在会话结束后丢弃。"
    "</div>",
    unsafe_allow_html=True,
)


