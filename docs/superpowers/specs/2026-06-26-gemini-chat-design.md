# Gemini-powered chat panel for the Job Hunt Dashboard

## Problem

The dashboard (`job_dashboard.py`) shows charts and tables derived from the
"Job Hunt 2024-26" Google Sheet, but answering an ad-hoc question like
*"What companies am I waiting to hear back from?"* currently means manually
scanning the Recent Activity table or squinting at the sidebar filters.
We want a chat panel, backed by Gemini, that can answer free-form questions
against the underlying application data.

## Goals

- Ask natural-language questions about job applications and get answers
  grounded in the actual sheet data (not hallucinated).
- Keep the implementation proportional to a personal, single-user dashboard
  — no new infrastructure, no multi-page app, no agent framework.
- Don't break the dashboard if the feature isn't configured (no API key) or
  a Gemini call fails.

## Non-goals

- Function-calling / tool-use into pandas, or any agent loop. The data is
  small enough that stuffing it into the prompt context is simpler and
  sufficiently accurate. Worth revisiting only if the sheet grows into the
  thousands of rows.
- Capping/trimming conversation history. Out of scope for now — the sheet
  and conversations are small enough that token cost isn't a concern.
- Multi-user auth, rate limiting, or persisting chat history across browser
  sessions/server restarts. `st.session_state` (in-memory, per session) is
  enough.

## Architecture

Everything lives inline in `job_dashboard.py`, in a new section added after
the existing sidebar filters/Refresh button — consistent with how the rest
of the file is structured (one script, comment-banner sections).

New dependency: `google-genai` (the current Google Gen AI Python SDK; the
older `google-generativeai` package is deprecated). Add to
`requirements.txt`.

New secret: `GEMINI_API_KEY`, a flat string key added to
`.streamlit/secrets.toml` for local dev and to the Streamlit Cloud app's
secrets for production — same mechanism already used for
`gcp_service_account`, just without a local-file fallback since it's a
single string rather than a JSON credential file.

```python
from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-2.5-flash"

gemini_client = (
    genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    if "GEMINI_API_KEY" in st.secrets
    else None
)
```

`gemini_client` is created once at module load (no network call at
creation time). If the key is absent, `gemini_client` stays `None` and the
sidebar shows a muted hint instead of a chat box.

## Data flow

On every question sent, the code builds a fresh system instruction string:

1. Today's date, so relative reasoning ("how long have I been waiting")
   works.
2. A CSV snapshot of the **full** `df` (the already-loaded, "Applied? ==
   yes" dataset — not the sidebar-filtered `filt`), restricted to the
   columns that matter for Q&A: `Company`, `Location`, `Position`,
   `Date Applied`, `Response Date`, `Days in Between`, `Outcome`, `Offer?`.
   `Link` is dropped — it's noise for this purpose.
3. Short guidance text: a blank/"Pending" `Outcome` combined with an empty
   `Response Date` means no response yet (i.e. "waiting to hear back");
   answer only from the given data; say so explicitly if something isn't
   answerable from it.

Rebuilding this snapshot on every question (rather than once per session)
keeps answers correct even if the user clicks "🔄 Refresh" mid-conversation.

Conversation turns are kept as a plain list of `{"role": "user"|"model",
"text": ...}` dicts in `st.session_state.gemini_messages`, using Gemini's
own role names directly (`"user"` / `"model"`) so the list can be fed back
into `history=` with no translation. The UI layer maps `"model"` ->
`st.chat_message("assistant")` purely for the display icon — the stored
role string itself is never `"assistant"`. On each new question:

```python
history = [
    {"role": m["role"], "parts": [{"text": m["text"]}]}
    for m in st.session_state.gemini_messages
]
chat = gemini_client.chats.create(
    model=GEMINI_MODEL,
    config=types.GenerateContentConfig(system_instruction=system_prompt),
    history=history,
)
response = chat.send_message(user_question)
```

The user's question and `response.text` are appended to
`st.session_state.gemini_messages` and the sidebar re-renders.

## UI

A new "💬 Ask the Data" section in the sidebar, below the existing filters
and Refresh button:

- If `gemini_client is None` (no API key configured): render a small muted
  caption — `Add GEMINI_API_KEY to .streamlit/secrets.toml to enable chat.`
  — and nothing else. The rest of the dashboard is unaffected.
- Otherwise: render existing turns via `st.chat_message("user")` /
  `st.chat_message("assistant")`, then `st.chat_input(...)` docked at the
  bottom of the sidebar for the next question.
- A small "Clear chat" button resets `st.session_state.gemini_messages` to
  `[]`.

## Error handling

A Gemini call can fail (network blip, rate limit, invalid key, etc.). Wrap
the `chat.send_message(...)` call in `try/except Exception`; on failure,
append an assistant turn with a friendly message (`"Sorry, I couldn't reach
Gemini: <short error>"`) instead of letting the exception propagate and
crash the whole Streamlit page.

## Testing

No automated test suite exists for this dashboard today (it's a Streamlit
script, not a library), so verification is manual:

- Launch the app locally with `GEMINI_API_KEY` unset → confirm the rest of
  the dashboard renders normally and the sidebar shows the muted hint.
- Set `GEMINI_API_KEY` → ask "What companies am I waiting to hear back
  from?" and a couple of follow-ups, confirm answers match what the Recent
  Activity / Top Companies tables show.
- Click "🔄 Refresh" mid-conversation, ask another question, confirm the
  answer reflects any data changes.
- Temporarily point `GEMINI_API_KEY` at an invalid value → confirm the
  error is shown as a chat bubble, not a crash.
