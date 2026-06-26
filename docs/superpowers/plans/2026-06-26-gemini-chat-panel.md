# Gemini Chat Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Gemini-powered chat panel to the sidebar of the job-hunt Streamlit dashboard so the user can ask free-form questions ("What companies am I waiting to hear back from?") and get answers grounded in the actual application data.

**Architecture:** Everything lives inline in `job_dashboard.py`, in a new section after the existing sidebar filters/Refresh button. A `genai.Client` is created once at module load from `st.secrets["GEMINI_API_KEY"]`. On every question, a fresh system prompt (today's date + a CSV snapshot of the full, unfiltered `df` + answering guidance) is built and a new `chat` session is created with the running conversation as `history=`, so answers always reflect current data even mid-conversation.

**Tech Stack:** Streamlit, `google-genai` (current Gemini Python SDK — the older `google-generativeai` package is deprecated), pandas (already in use).

## Global Constraints

- Full source spec: `docs/superpowers/specs/2026-06-26-gemini-chat-design.md` — read it if anything below is ambiguous.
- Code stays inline in `job_dashboard.py` — no new module, per the approved spec.
- The chat always reasons over the full `df` (unfiltered), never the sidebar-filtered `filt`.
- No history capping/trimming — full conversation is replayed every turn.
- No function-calling/tool-use — the whole dataset snapshot is stuffed into the system prompt as CSV text.
- This repo has no automated test suite (`job_dashboard.py` is a single script that executes Streamlit/Google-Sheets calls at import time, so it can't be safely imported by pytest). Per the approved spec, verification for this feature is manual — every task below has explicit manual verification steps with exact commands and expected outcomes instead of automated tests.
- `.streamlit/secrets.toml` and `secrets/` are gitignored — never put a real API key in a file that gets committed, and never paste real secret values into plan/spec docs.

---

### Task 1: Add `google-genai` dependency and secrets scaffolding

**Files:**
- Modify: `requirements.txt`
- Modify: `.streamlit/secrets.toml` (local only — gitignored, not committed)

**Interfaces:**
- Produces: an installed `google-genai` package importable as `from google import genai`, and a `GEMINI_API_KEY` key available via `st.secrets` for Task 2 to consume.

- [ ] **Step 1: Add the dependency to requirements.txt**

In `requirements.txt`, add a new line after `numpy>=1.26.0`:

```
google-genai>=1.0.0
```

- [ ] **Step 2: Install it**

Run: `pip3 install -r requirements.txt`
Expected: installs successfully, no errors.

- [ ] **Step 3: Verify the import works**

Run: `python3 -c "from google import genai; from google.genai import types; print('ok')"`
Expected output: `ok` — no `ModuleNotFoundError`.

- [ ] **Step 4: Add the API key placeholder to local secrets**

Open `.streamlit/secrets.toml` and append a new top-level line (not nested under `[gcp_service_account]`):

```toml
GEMINI_API_KEY = "REPLACE_WITH_YOUR_AI_STUDIO_KEY"
```

Get a real key from https://aistudio.google.com/apikey and replace the placeholder value. (This file is gitignored — the real key never reaches git.)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "Add google-genai dependency for Gemini chat panel"
```

(Do not `git add .streamlit/secrets.toml` — it's gitignored and contains your real key.)

---

### Task 2: Gemini client, prompt-building helpers, and sidebar chat UI

**Files:**
- Modify: `job_dashboard.py`

**Interfaces:**
- Consumes: `df` (the full, unfiltered DataFrame already loaded at `job_dashboard.py:242`, columns include `Company`, `Location`, `Position`, `Date Applied`, `Response Date`, `Days in Between`, `Outcome`, `Offer?`); `GEMINI_API_KEY` from `st.secrets` (Task 1).
- Produces: `GEMINI_MODEL` (str constant), `gemini_client` (`genai.Client | None`), `build_data_snapshot(df_in: pd.DataFrame) -> str`, `build_system_prompt(df_in: pd.DataFrame) -> str`, `messages_to_history(messages: list) -> list`, `ask_gemini(question: str, df_in: pd.DataFrame) -> str`. Nothing later in the file depends on these — this is the last task.

- [ ] **Step 1: Add the new imports**

In `job_dashboard.py`, find:

```python
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
```

Replace with:

```python
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types
from datetime import datetime, timedelta
```

- [ ] **Step 2: Add the Gemini helpers section**

Find the end of the Header section and the start of the Sidebar filters section:

```python
# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 💼 Job Hunt Dashboard")
st.markdown(
    f'<p class="ts">Last refreshed: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>',
    unsafe_allow_html=True,
)


# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
```

Replace with (inserting a new section between them):

```python
# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 💼 Job Hunt Dashboard")
st.markdown(
    f'<p class="ts">Last refreshed: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>',
    unsafe_allow_html=True,
)


# ── Gemini chat helpers ───────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"

gemini_client = (
    genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    if "GEMINI_API_KEY" in st.secrets
    else None
)


def build_data_snapshot(df_in: pd.DataFrame) -> str:
    """CSV snapshot of every application, for the Gemini system prompt."""
    cols = [
        "Company", "Location", "Position", "Date Applied",
        "Response Date", "Days in Between", "Outcome", "Offer?",
    ]
    snap = df_in[cols].copy()
    snap["Date Applied"] = snap["Date Applied"].dt.strftime("%Y-%m-%d")
    snap["Response Date"] = snap["Response Date"].dt.strftime("%Y-%m-%d")
    return snap.to_csv(index=False)


def build_system_prompt(df_in: pd.DataFrame) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    return (
        "You are a helpful assistant answering questions about the user's "
        "job search, based only on the application data below. "
        f"Today's date is {today}.\n\n"
        "A blank or 'Pending' Outcome combined with an empty Response Date "
        "means the user has not heard back yet (i.e. they're waiting). "
        "If a question can't be answered from this data, say so explicitly "
        "instead of guessing.\n\n"
        f"Application data (CSV):\n{build_data_snapshot(df_in)}"
    )


def messages_to_history(messages: list) -> list:
    return [
        {"role": m["role"], "parts": [{"text": m["text"]}]}
        for m in messages
    ]


def ask_gemini(question: str, df_in: pd.DataFrame) -> str:
    chat = gemini_client.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(df_in)
        ),
        history=messages_to_history(st.session_state.gemini_messages),
    )
    response = chat.send_message(question)
    return response.text


# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
```

- [ ] **Step 3: Add the sidebar chat UI**

Find the end of the sidebar filters block:

```python
    st.markdown("---")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── Apply filters ─────────────────────────────────────────────────────────────
```

Replace with (appending the chat UI inside the same `with st.sidebar:` block):

```python
    st.markdown("---")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("## 💬 Ask the Data")

    if gemini_client is None:
        st.caption("Add `GEMINI_API_KEY` to `.streamlit/secrets.toml` to enable chat.")
    else:
        if "gemini_messages" not in st.session_state:
            st.session_state.gemini_messages = []

        if st.button("Clear chat", use_container_width=True):
            st.session_state.gemini_messages = []

        for msg in st.session_state.gemini_messages:
            role = "assistant" if msg["role"] == "model" else "user"
            with st.chat_message(role):
                st.markdown(msg["text"])

        question = st.chat_input("Ask about your applications…")
        if question:
            st.session_state.gemini_messages.append({"role": "user", "text": question})
            with st.chat_message("user"):
                st.markdown(question)

            try:
                answer = ask_gemini(question, df)
            except Exception as exc:
                answer = f"Sorry, I couldn't reach Gemini: {exc}"

            st.session_state.gemini_messages.append({"role": "model", "text": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)


# ── Apply filters ─────────────────────────────────────────────────────────────
```

- [ ] **Step 4: Verify the app still runs with no API key configured**

In `.streamlit/secrets.toml`, comment out the `GEMINI_API_KEY` line (prefix with `#`).
Run: `streamlit run job_dashboard.py`
Expected: the dashboard loads fully (scorecards, charts, tables all render as before). In the sidebar, below "🔄 Refresh", a "💬 Ask the Data" heading appears with the muted caption "Add `GEMINI_API_KEY` to `.streamlit/secrets.toml` to enable chat." No chat box, no crash.

Stop the app (Ctrl+C) before the next step.

- [ ] **Step 5: Verify a real question gets a grounded answer**

In `.streamlit/secrets.toml`, uncomment `GEMINI_API_KEY` and set it to your real AI Studio key (from Task 1, Step 4).
Run: `streamlit run job_dashboard.py`
In the sidebar chat box, type: `What companies am I waiting to hear back from?` and press Enter.
Expected: a response listing companies with no recorded `Response Date` and a non-"Interview" outcome, consistent with what you'd see by manually scanning the Recent Activity table for blank Response Date / Outcome rows. No stack trace, no crash.

Ask a follow-up in the same chat box, e.g. `Which of those have I been waiting on the longest?`
Expected: a coherent answer that uses the prior turn as context (proves `history=` is being threaded through correctly).

- [ ] **Step 6: Verify data refreshes mid-conversation**

With the app still running and the conversation from Step 5 still visible, click "🔄 Refresh" in the sidebar.
Expected: no crash, dashboard re-renders, and the chat history from Step 5 is still visible (it's `st.session_state`, which survives a rerun).
Ask another question.
Expected: a new answer is returned without error (proves the system prompt is rebuilt fresh from `df` on every question rather than going stale).

- [ ] **Step 7: Verify a Gemini failure shows as a chat bubble, not a crash**

Stop the app. In `.streamlit/secrets.toml`, temporarily set `GEMINI_API_KEY = "invalid-key-for-testing"`.
Run: `streamlit run job_dashboard.py`
Ask any question in the chat box.
Expected: an assistant chat bubble reading `Sorry, I couldn't reach Gemini: <error detail>` — the rest of the dashboard (charts, sidebar) stays intact, no Streamlit error page.

Stop the app and restore your real `GEMINI_API_KEY` value in `.streamlit/secrets.toml`.

- [ ] **Step 8: Commit**

```bash
git add job_dashboard.py
git commit -m "Add Gemini-powered chat panel to dashboard sidebar"
```
