import streamlit as st
import streamlit.components.v1 as components
import gspread
import pandas as pd
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import numpy as np

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#0F0F13"
CARD     = "#1A1A24"
BORDER   = "#2A2A38"
ACCENT   = "#7B6EF6"
POSITIVE = "#00E5A0"
NEGATIVE = "#FF5757"
PENDING  = "#FFB547"
TEXT     = "#F0EFF8"
MUTED    = "#6B6A80"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Job Hunt Dashboard",
    page_icon="💼",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ── Base ── */
  .stApp, [data-testid="stAppViewContainer"] {{
    background-color: {BG};
    color: {TEXT};
  }}
  [data-testid="stHeader"] {{
    background-color: {BG};
    border-bottom: 1px solid {BORDER};
  }}
  .block-container {{
    padding-top: 1.5rem;
    padding-bottom: 2rem;
  }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {{
    background-color: {CARD};
    border-right: 1px solid {BORDER};
  }}
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span {{
    color: {TEXT} !important;
  }}
  [data-testid="stSidebar"] h2 {{
    color: {TEXT};
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }}

  /* ── Metric cards ── */
  [data-testid="stMetric"] {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1rem 1.25rem !important;
  }}
  [data-testid="stMetricLabel"] p {{
    color: {MUTED} !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
  }}
  [data-testid="stMetricValue"] {{
    color: {TEXT} !important;
    font-size: 1.65rem !important;
    font-weight: 700 !important;
  }}
  [data-testid="stMetricDelta"] {{
    font-size: 0.78rem !important;
  }}

  /* ── Typography ── */
  h1 {{ color: {TEXT}; font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em; }}
  h2 {{ color: {TEXT}; font-size: 1rem; font-weight: 700; }}
  h3 {{ color: {MUTED}; font-size: 0.72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }}
  hr {{ border: none; border-top: 1px solid {BORDER}; }}

  /* ── Activity table ── */
  .activity-wrap {{
    overflow-x: auto;
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
  }}
  .activity-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }}
  .activity-table th {{
    background-color: {BG};
    color: {MUTED};
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    font-weight: 700;
    padding: 10px 16px;
    text-align: left;
    border-bottom: 1px solid {BORDER};
    white-space: nowrap;
  }}
  .activity-table td {{
    padding: 10px 16px;
    color: {TEXT};
    border-bottom: 1px solid {BORDER};
    white-space: nowrap;
  }}
  .activity-table tr:last-child td {{ border-bottom: none; }}
  .activity-table tr:hover td {{ background-color: rgba(123,110,246,0.05); }}

  /* ── Badges ── */
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.02em;
  }}
  .badge-interview {{ background: rgba(0,229,160,0.12);  color: {POSITIVE}; }}
  .badge-rejected  {{ background: rgba(255,87,87,0.12);  color: {NEGATIVE}; }}
  .badge-offer     {{ background: rgba(123,110,246,0.18); color: {ACCENT}; }}
  .badge-pending   {{ background: rgba(255,181,71,0.12); color: {PENDING}; }}

  /* ── Timestamp ── */
  .ts {{ color: {MUTED}; font-size: 0.73rem; margin: -0.25rem 0 1.25rem 0; }}

  /* ── Bordered container ── */
  [data-testid="stVerticalBlockBorderWrapper"] {{
    border-color: {BORDER} !important;
    border-radius: 12px !important;
    background-color: {CARD} !important;
  }}

  /* ── Plotly container tweaks ── */
  .js-plotly-plot .plotly .modebar {{
    background: transparent !important;
  }}

  /* ── Segmented controls ── */
  [data-testid="stBaseButton-segmented_control"] {{
    background-color: {CARD} !important;
    color: {MUTED} !important;
    border: 1px solid {BORDER} !important;
  }}
  [data-testid="stBaseButton-segmented_control"] p {{
    color: {MUTED} !important;
  }}
  [data-testid="stBaseButton-segmented_control"]:hover p {{
    color: {TEXT} !important;
  }}
  [data-testid="stBaseButton-segmented_control"][aria-pressed="true"],
  [data-testid="stBaseButton-segmented_control"][data-active="true"],
  [data-testid="stBaseButton-segmented_control"].active {{
    background-color: {ACCENT} !important;
    border-color: {ACCENT} !important;
  }}
  [data-testid="stBaseButton-segmented_control"][aria-pressed="true"] p,
  [data-testid="stBaseButton-segmented_control"][data-active="true"] p,
  [data-testid="stBaseButton-segmented_control"].active p {{
    color: {TEXT} !important;
    font-weight: 600 !important;
  }}

  /* ── Sliders ── */
  [data-testid="stSlider"] label {{ color: {TEXT} !important; }}
  [data-testid="stSlider"] [data-testid="stTickBarMin"],
  [data-testid="stSlider"] [data-testid="stTickBarMax"] {{
    color: {MUTED} !important;
  }}
</style>
""", unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    # Use Streamlit secrets in Cloud; fall back to local JSON file for dev
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
    else:
        creds = Credentials.from_service_account_file(
            "secrets/service_account.json", scopes=scopes
        )
    gc = gspread.authorize(creds)
    try:
        ws = gc.open("Job Hunt 2024-26").sheet1
    except gspread.SpreadsheetNotFound:
        available = [s.title for s in gc.openall()]
        if available:
            raise ValueError(
                f"Sheet named 'Job Hunt 2024-26' not found. "
                f"Sheets visible to this service account: {available}"
            )
        else:
            raise ValueError(
                "No sheets are shared with this service account. "
                "Share your Google Sheet with the client_email in your service_account.json."
            )
    expected = [
        "Company", "Location", "Position", "Link",
        "Applied?", "Date Applied", "Response Date",
        "Days in Between", "Outcome", "Offer?",
    ]
    records = ws.get_all_records(head=4, expected_headers=expected)
    df = pd.DataFrame(records)

    df["Date Applied"]    = pd.to_datetime(df["Date Applied"],    errors="coerce")
    df["Response Date"]   = pd.to_datetime(df["Response Date"],   errors="coerce")
    df["Days in Between"] = pd.to_numeric(df["Days in Between"],  errors="coerce")
    df["Outcome"]         = df["Outcome"].fillna("Pending").str.strip()
    df["Company"]         = df["Company"].fillna("").str.strip()
    df["Position"]        = df["Position"].fillna("").str.strip()
    df = df[df["Applied?"].str.strip().str.lower() == "yes"].reset_index(drop=True)
    return df


# ── Load data ─────────────────────────────────────────────────────────────────
try:
    df = load_data()
except Exception as exc:
    st.error(f"Could not load Google Sheet: {exc}")
    st.info("Make sure `secrets/service_account.json` exists and the sheet is shared with your service account.")
    st.stop()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 💼 Job Hunt Dashboard")
st.markdown(
    f'<p class="ts">Last refreshed: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>',
    unsafe_allow_html=True,
)


# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Filters")
    st.markdown("---")

    valid_dates = df["Date Applied"].dropna()
    min_date = valid_dates.min().date() if len(valid_dates) else (datetime.now() - timedelta(days=365)).date()
    max_date = valid_dates.max().date() if len(valid_dates) else datetime.now().date()

    date_range = st.date_input(
        "Date Applied",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    all_outcomes = sorted(df["Outcome"].dropna().unique().tolist())
    all_companies = sorted(
        df["Company"].replace("", pd.NA).dropna().unique().tolist()
    )

    sel_outcomes  = st.multiselect("Outcome",  all_outcomes,  default=all_outcomes)
    sel_companies = st.multiselect("Company",  all_companies, default=all_companies)

    st.markdown("---")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── Apply filters ─────────────────────────────────────────────────────────────
filt = df.copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    s, e = date_range
    filt = filt[
        (filt["Date Applied"].dt.date >= s) &
        (filt["Date Applied"].dt.date <= e)
    ]

# Empty multiselect = show all (common dashboard UX convention)
if sel_outcomes:
    filt = filt[filt["Outcome"].isin(sel_outcomes)]
if sel_companies:
    filt = filt[filt["Company"].isin(sel_companies)]


# ── Month helpers ─────────────────────────────────────────────────────────────
now = datetime.now()
cur_month_start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
prev_month_end   = cur_month_start
prev_month_start = (cur_month_start - timedelta(days=1)).replace(day=1)


def month_slice(df_in: pd.DataFrame, col: str, start, end) -> pd.DataFrame:
    return df_in[
        (df_in[col] >= pd.Timestamp(start)) &
        (df_in[col] <  pd.Timestamp(end))
    ]


cur  = month_slice(filt, "Date Applied", cur_month_start, now + timedelta(days=1))
prev = month_slice(filt, "Date Applied", prev_month_start, prev_month_end)


# ── Scorecard values ──────────────────────────────────────────────────────────
def interview_rate(df_in: pd.DataFrame) -> float:
    total = len(df_in)
    if total == 0:
        return 0.0
    return round((df_in["Outcome"].str.lower() == "interview").sum() / total * 100, 1)


cur_total      = len(cur)
cur_rejections = int((cur["Outcome"].str.lower() == "rejected").sum())
cur_interviews = int((cur["Outcome"].str.lower() == "interview").sum())
cur_avg_days   = cur["Days in Between"].mean()
cur_ir         = interview_rate(cur)

prev_total      = len(prev)
prev_rejections = int((prev["Outcome"].str.lower() == "rejected").sum())
prev_interviews = int((prev["Outcome"].str.lower() == "interview").sum())
prev_avg_days   = prev["Days in Between"].mean()
prev_ir         = interview_rate(prev)


def safe_delta(cur_val, prev_val):
    """Return int delta if prev exists, else None."""
    if prev_total == 0:
        return None
    return int(cur_val - prev_val)


def safe_delta_f(cur_val, prev_val, suffix=""):
    if prev_total == 0 or np.isnan(cur_val) or np.isnan(prev_val):
        return None
    delta = round(cur_val - prev_val, 1)
    return f"{delta:+.1f}{suffix}"


# ── Scorecards row ────────────────────────────────────────────────────────────
view = st.segmented_control(
    "Scorecard view",
    options=["This Month", "All Time", "Selected Range"],
    default="This Month",
    label_visibility="collapsed",
)

# Pick the base dataset and whether to show deltas
if view == "This Month":
    sc = cur
    show_delta = True
elif view == "Selected Range":
    sc = filt
    show_delta = False
else:  # All Time — only outcome/company filters, no date filter
    all_time = df.copy()
    if sel_outcomes:
        all_time = all_time[all_time["Outcome"].isin(sel_outcomes)]
    if sel_companies:
        all_time = all_time[all_time["Company"].isin(sel_companies)]
    sc = all_time
    show_delta = False

sc_total      = len(sc)
sc_rejections = int((sc["Outcome"].str.lower().isin(["rejected", "rejection"])).sum())
sc_interviews = int((sc["Outcome"].str.lower() == "interview").sum())
sc_avg_days   = sc["Days in Between"].mean()
sc_ir         = interview_rate(sc)

# Dead pipeline: no response, not an interview, applied 30+ days ago
dead_pipeline = filt[
    filt["Response Date"].isna() &
    (filt["Outcome"].str.lower() != "interview") &
    (filt["Date Applied"] <= pd.Timestamp(now - timedelta(days=30)))
]
dead_count = len(dead_pipeline)
cur_dead  = len(month_slice(dead_pipeline, "Date Applied", cur_month_start, now + timedelta(days=1)))
prev_dead = len(month_slice(dead_pipeline, "Date Applied", prev_month_start, prev_month_end))

st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.metric(
        "Total Applications",
        sc_total,
        delta=safe_delta(cur_total, prev_total) if show_delta else None,
    )
with c2:
    st.metric(
        "Rejections",
        sc_rejections,
        delta=safe_delta(cur_rejections, prev_rejections) if show_delta else None,
        delta_color="inverse",
    )
with c3:
    st.metric(
        "Interviews",
        sc_interviews,
        delta=safe_delta(cur_interviews, prev_interviews) if show_delta else None,
    )
with c4:
    avg_display = f"{sc_avg_days:.1f}d" if not np.isnan(sc_avg_days) else "—"
    st.metric(
        "Avg. Days to Response",
        avg_display,
        delta=safe_delta_f(cur_avg_days, prev_avg_days, "d") if show_delta else None,
        delta_color="inverse",
        help="Lower is faster",
    )
with c5:
    st.metric(
        "Interview Rate",
        f"{sc_ir}%",
        delta=safe_delta_f(cur_ir, prev_ir, "%") if show_delta else None,
    )
with c6:
    sc_dead = dead_count if view != "This Month" else cur_dead
    st.metric(
        "Dead Pipeline",
        sc_dead,
        delta=safe_delta(cur_dead, prev_dead) if show_delta else None,
        delta_color="inverse",
        help="No response after 30+ days — safe to move on",
    )

st.markdown("<br>", unsafe_allow_html=True)


# ── Chart utilities ───────────────────────────────────────────────────────────
def dark_layout(**overrides) -> dict:
    base = dict(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(color=TEXT, family="Inter, -apple-system, sans-serif", size=12),
        xaxis=dict(
            gridcolor=BORDER,
            linecolor=BORDER,
            tickfont=dict(color=MUTED, size=11),
            showgrid=False,
        ),
        yaxis=dict(
            gridcolor=BORDER,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(color=MUTED, size=11),
            showgrid=True,
        ),
        margin=dict(l=48, r=16, t=44, b=40),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=BORDER,
            font=dict(color=TEXT, size=11),
        ),
        hoverlabel=dict(
            bgcolor=BG,
            bordercolor=BORDER,
            font=dict(color=TEXT, size=12),
        ),
    )
    base.update(overrides)
    return base


def last_12_months() -> list[tuple[int, int]]:
    months = []
    y, m = now.year, now.month
    for _ in range(12):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def month_label(year: int, month: int) -> str:
    return datetime(year, month, 1).strftime("%b %Y")


def months_for_window(window: str) -> list:
    """Return (year, month) tuples for the selected window."""
    if window == "Last 12 Months":
        return last_12_months()
    elif window == "All Time":
        min_date = filt["Date Applied"].min()
        if pd.isna(min_date):
            return last_12_months()
        months = []
        y, m = min_date.year, min_date.month
        while (y, m) <= (now.year, now.month):
            months.append((y, m))
            m += 1
            if m > 12:
                m = 1
                y += 1
        return months
    else:
        # Specific year e.g. "2024"
        yr = int(window)
        end_m = now.month if yr == now.year else 12
        return [(yr, m) for m in range(1, end_m + 1)]

available_years = sorted(filt["Date Applied"].dropna().dt.year.unique().astype(int).tolist())


def count_by_month(df_in: pd.DataFrame, date_col: str, outcome_filter=None) -> list:
    """Count rows per month, optionally filtered to a specific Outcome value."""
    counts = []
    for y, m in months_12:
        mask = (df_in[date_col].dt.year == y) & (df_in[date_col].dt.month == m)
        sub  = df_in[mask]
        if outcome_filter:
            sub = sub[sub["Outcome"].str.lower() == outcome_filter.lower()]
        counts.append(len(sub))
    return counts


# ── Response time: Rejection vs Interview ────────────────────────────────────
st.markdown("### Response Time — Rejection vs. Interview Request")

rejection_days = (
    filt[
        (filt["Outcome"].str.lower() == "rejection") &
        (filt["Offer?"].str.strip().str.lower() == "no") &
        filt["Days in Between"].notna()
    ]["Days in Between"]
)

total_interviews = int((filt["Outcome"].str.lower() == "interview").sum())
interview_days = (
    filt[
        (filt["Outcome"].str.lower() == "interview") &
        filt["Days in Between"].notna()
    ]["Days in Between"]
)

def days_val(series, fn):
    return f"{int(round(fn(series)))}d" if len(series) else "—"

col_r1, col_r2, col_i1, col_i2 = st.columns(4)
with col_r1:
    st.metric("Avg. days to rejection",  days_val(rejection_days, np.mean),   help=f"Based on {len(rejection_days)} rejections")
with col_r2:
    st.metric("Median days to rejection", days_val(rejection_days, np.median), help="Half of rejections arrive before this day")
with col_i1:
    missing = total_interviews - len(interview_days)
    help_txt = f"{len(interview_days)} of {total_interviews} interviews have dates filled in — {missing} have no Response Date in the sheet"
    st.metric("Avg. days to interview",  days_val(interview_days, np.mean),   help=help_txt)
with col_i2:
    st.metric("Median days to interview", days_val(interview_days, np.median), help=f"{len(interview_days)} of {total_interviews} interviews have dates filled in")

st.markdown("<br>", unsafe_allow_html=True)


# ── Monthly charts ────────────────────────────────────────────────────────────
with st.container(border=True):
  st.markdown("### Monthly Trends")
  chart_window = st.segmented_control(
      "Chart window",
      options=["Last 12 Months"] + [str(y) for y in available_years] + ["All Time"],
      default="Last 12 Months",
      label_visibility="collapsed",
      key="chart_window",
  )
  months_12 = months_for_window(chart_window)
  labels_12 = [month_label(y, m) for y, m in months_12]

  # ── Row 1: Interviews bar + Interview rate line ─────────────────────────────
  col_left, col_right = st.columns(2)

  with col_left:
      st.markdown("##### Interviews")
      interview_counts = count_by_month(filt, "Response Date", "interview")
      fig1 = go.Figure()
      fig1.add_trace(go.Bar(
          x=labels_12,
          y=interview_counts,
          marker_color=POSITIVE,
          marker_line_width=0,
          marker_opacity=0.9,
          text=[str(v) if v > 0 else "" for v in interview_counts],
          textposition="outside",
          textfont=dict(color=TEXT, size=11),
          hovertemplate="<b>%{x}</b><br>Interviews: %{y}<extra></extra>",
          name="Interviews",
      ))
      fig1.update_layout(dark_layout(
          title=dict(text="Interviews by Response Month", font=dict(color=TEXT, size=13, weight=600), x=0, xanchor="left", pad=dict(l=0)),
          showlegend=False, height=320, bargap=0.35,
          margin=dict(l=48, r=16, t=44, b=40, pad=4),
          yaxis=dict(gridcolor=BORDER, linecolor="rgba(0,0,0,0)", tickfont=dict(color=MUTED, size=11), showgrid=True,
                     range=[0, max(interview_counts) * 1.25 if max(interview_counts) > 0 else 1]),
      ))
      st.plotly_chart(fig1, use_container_width=True)

  with col_right:
      st.markdown("##### Interview Rate %")
      apps_by_applied  = count_by_month(filt, "Date Applied")
      intv_by_applied  = count_by_month(filt, "Date Applied", "interview")
      ir_by_month      = [round(i / a * 100, 1) if a > 0 else 0.0 for i, a in zip(intv_by_applied, apps_by_applied)]
      fig2 = go.Figure()
      fig2.add_trace(go.Scatter(
          x=labels_12, y=ir_by_month, mode="lines+markers+text",
          line=dict(color=ACCENT, width=2.5),
          marker=dict(color=ACCENT, size=6, line=dict(color=BG, width=1.5)),
          fill="tozeroy", fillcolor="rgba(123,110,246,0.10)",
          text=[f"{v}%" if v > 0 else "" for v in ir_by_month],
          textposition="top center", textfont=dict(color=TEXT, size=11),
          hovertemplate="<b>%{x}</b><br>Interview rate: %{y}%<extra></extra>",
          name="Interview Rate",
      ))
      fig2.update_layout(dark_layout(
          title=dict(text="Interview Rate by Application Month", font=dict(color=TEXT, size=13, weight=600), x=0, xanchor="left", pad=dict(l=0)),
          yaxis=dict(gridcolor=BORDER, linecolor="rgba(0,0,0,0)", tickfont=dict(color=MUTED, size=11),
                     ticksuffix="%", showgrid=True, range=[0, max(ir_by_month) * 1.3 if max(ir_by_month) > 0 else 1]),
          showlegend=False, height=320,
      ))
      st.plotly_chart(fig2, use_container_width=True)

  # ── Row 2: Applications per month ───────────────────────────────────────────
  st.markdown("##### Applications Over Time")
  app_counts = count_by_month(filt, "Date Applied")
  fig3 = go.Figure()
  fig3.add_trace(go.Scatter(
      x=labels_12, y=app_counts, mode="lines+markers+text",
      line=dict(color=PENDING, width=2.5),
      marker=dict(color=PENDING, size=6, line=dict(color=BG, width=1.5)),
      fill="tozeroy", fillcolor="rgba(255,181,71,0.10)",
      text=[str(v) if v > 0 else "" for v in app_counts],
      textposition="top center", textfont=dict(color=TEXT, size=11),
      hovertemplate="<b>%{x}</b><br>Applications: %{y}<extra></extra>",
      name="Applications",
  ))
  fig3.update_layout(dark_layout(
      title=dict(text="Applications per Month", font=dict(color=TEXT, size=13, weight=600), x=0, xanchor="left", pad=dict(l=0)),
      showlegend=False, height=280,
      yaxis=dict(gridcolor=BORDER, linecolor="rgba(0,0,0,0)", tickfont=dict(color=MUTED, size=11),
                 showgrid=True, range=[0, max(app_counts) * 1.25 if max(app_counts) > 0 else 1]),
  ))
  st.plotly_chart(fig3, use_container_width=True)


# ── Funnel ────────────────────────────────────────────────────────────────────
st.markdown("### Application Funnel")

funnel_total     = len(filt)
funnel_responded = int(filt["Response Date"].notna().sum())
funnel_interview = int((filt["Outcome"].str.lower() == "interview").sum())

funnel_labels = ["Applied", "Responded", "Interviewed"]
funnel_values = [funnel_total, funnel_responded, funnel_interview]
funnel_colors = [ACCENT, PENDING, POSITIVE]
funnel_pcts   = [
    "100%",
    f"{funnel_responded/funnel_total*100:.1f}% of applied" if funnel_total else "—",
    f"{funnel_interview/funnel_responded*100:.1f}% of responded" if funnel_responded else "—",
]

fig_funnel = go.Figure(go.Funnel(
    y=funnel_labels,
    x=funnel_values,
    textinfo="value+percent previous",
    marker=dict(color=funnel_colors, line=dict(width=0)),
    textfont=dict(color=TEXT, size=13),
    hovertemplate="<b>%{y}</b><br>Count: %{x}<br>%{percentPrevious} of previous stage<extra></extra>",
))
fig_funnel.update_layout(dark_layout(
    height=280,
    margin=dict(l=120, r=40, t=20, b=20),
    showlegend=False,
    yaxis=dict(showgrid=False, linecolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT, size=13, weight=600)),
    xaxis=dict(showgrid=False, linecolor="rgba(0,0,0,0)", visible=False),
))
st.plotly_chart(fig_funnel, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Ghosting trend + Seasonality ──────────────────────────────────────────────
col_ghost, col_season = st.columns(2)

with col_ghost:
    st.markdown("### Rejection vs. Ghosting Over Time")

    ghost_rejection_pct, ghost_unresponsive_pct = [], []
    for y, m in months_12:
        mask = (filt["Date Applied"].dt.year == y) & (filt["Date Applied"].dt.month == m)
        grp  = filt[mask]
        total = len(grp)
        if total == 0:
            ghost_rejection_pct.append(0)
            ghost_unresponsive_pct.append(0)
        else:
            ghost_rejection_pct.append(round((grp["Outcome"].str.lower() == "rejection").sum() / total * 100, 1))
            ghost_unresponsive_pct.append(round((grp["Outcome"].str.lower() == "unresponsive").sum() / total * 100, 1))

    fig_ghost = go.Figure()
    fig_ghost.add_trace(go.Scatter(
        x=labels_12, y=ghost_rejection_pct,
        mode="lines+markers",
        name="Rejection %",
        line=dict(color=NEGATIVE, width=2.5),
        marker=dict(color=NEGATIVE, size=5),
        hovertemplate="<b>%{x}</b><br>Rejection: %{y}%<extra></extra>",
    ))
    fig_ghost.add_trace(go.Scatter(
        x=labels_12, y=ghost_unresponsive_pct,
        mode="lines+markers",
        name="Ghosted %",
        line=dict(color=MUTED, width=2.5, dash="dot"),
        marker=dict(color=MUTED, size=5),
        hovertemplate="<b>%{x}</b><br>Ghosted: %{y}%<extra></extra>",
    ))
    fig_ghost.update_layout(dark_layout(
        yaxis=dict(
            gridcolor=BORDER, linecolor="rgba(0,0,0,0)",
            tickfont=dict(color=MUTED, size=11), ticksuffix="%", showgrid=True,
            range=[0, max(max(ghost_rejection_pct), max(ghost_unresponsive_pct)) * 1.3 if ghost_rejection_pct else 1],
        ),
        showlegend=True,
        height=320,
    ))
    st.plotly_chart(fig_ghost, use_container_width=True)

with col_season:
    st.markdown("### Interview Rate by Month of Year")

    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    season_rates, season_apps = [], []
    for m in range(1, 13):
        grp = filt[filt["Date Applied"].dt.month == m]
        apps = len(grp)
        interviews = (grp["Outcome"].str.lower() == "interview").sum()
        season_apps.append(apps)
        season_rates.append(round(interviews / apps * 100, 1) if apps > 0 else 0)

    best_m = season_rates.index(max(season_rates))
    season_colors = [POSITIVE if i == best_m else "rgba(0,229,160,0.3)" for i in range(12)]

    fig_season = go.Figure()
    fig_season.add_trace(go.Bar(
        x=month_names, y=season_rates,
        marker_color=season_colors,
        marker_line_width=0,
        text=[f"{r}%" if r > 0 else "" for r in season_rates],
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        customdata=season_apps,
        hovertemplate="<b>%{x}</b><br>Interview rate: %{y}%<br>Apps: %{customdata}<extra></extra>",
    ))
    fig_season.update_layout(dark_layout(
        title=dict(
            text=f"Best month: {month_names[best_m]} ({season_rates[best_m]}%)",
            font=dict(color=POSITIVE, size=13, weight=600),
            x=0, xanchor="left", pad=dict(l=0),
        ),
        yaxis=dict(
            gridcolor=BORDER, linecolor="rgba(0,0,0,0)",
            tickfont=dict(color=MUTED, size=11), ticksuffix="%", showgrid=True,
            range=[0, max(season_rates) * 1.3 if max(season_rates) > 0 else 1],
        ),
        showlegend=False,
        height=320,
        bargap=0.3,
    ))
    st.plotly_chart(fig_season, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Day of week + Role type ───────────────────────────────────────────────────
col_dow, col_role = st.columns(2)

with col_dow:
    st.markdown("### Applications by Day of Week")

    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_short  = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    filt_dow = filt.dropna(subset=["Date Applied"]).copy()
    filt_dow["dow"] = filt_dow["Date Applied"].dt.day_name()

    dow_apps = [len(filt_dow[filt_dow["dow"] == day]) for day in dow_order]

    busiest_idx = dow_apps.index(max(dow_apps))
    bar_colors = [ACCENT if i == busiest_idx else "rgba(123,110,246,0.35)" for i in range(7)]

    fig_dow = go.Figure()
    fig_dow.add_trace(go.Bar(
        x=dow_short,
        y=dow_apps,
        marker_color=bar_colors,
        marker_line_width=0,
        text=[str(v) for v in dow_apps],
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="<b>%{x}</b><br>Applications: %{y}<extra></extra>",
    ))
    fig_dow.update_layout(dark_layout(
        title=dict(
            text=f"Most active: {dow_order[busiest_idx]} ({dow_apps[busiest_idx]} apps)",
            font=dict(color=POSITIVE, size=13, weight=600),
            x=0, xanchor="left", pad=dict(l=0),
        ),
        yaxis=dict(
            gridcolor=BORDER,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(color=MUTED, size=11),
            showgrid=True,
            range=[0, max(dow_apps) * 1.25 if max(dow_apps) > 0 else 1],
        ),
        showlegend=False,
        height=320,
        bargap=0.3,
    ))
    st.plotly_chart(fig_dow, use_container_width=True)

with col_role:
    st.markdown("### Interview Rate by Role Type")

    role_sort = st.segmented_control(
        "Sort by",
        options=["Interview Rate", "Total Interviews"],
        default="Interview Rate",
        label_visibility="collapsed",
        key="role_sort",
    )

    # Priority-ordered categories — first match wins per role title
    # Handles Sr./Sr → Senior normalization before matching
    ROLE_CATEGORIES = [
        ("Developer Relations", [
            "devrel", "developer relations", "developer community",
            "dev community", "developer evangelist", "developer social",
        ]),
        ("Community",           ["community"]),
        ("Customer Success",    ["customer success", "client success"]),
        ("Growth",              ["growth manager", "growth associate", "growth lead",
                                 "growth operations", "growth partner"]),
        ("Partnerships",        ["partner manager", "partnerships manager",
                                 "partner program", "partnership manager"]),
        ("Startup / Ecosystem", ["startup", "venture capital", "ecosystem manager",
                                 "ecosystem lead", "accelerator manager"]),
        ("Content",             ["content manager", "content strategist",
                                 "content lead", "content marketing"]),
        ("Marketing",           ["marketing manager", "marketing associate",
                                 "product marketing", "marketing specialist"]),
        ("Operations",          ["operations manager", "operations associate",
                                 "operations coordinator", "business operations",
                                 "ops manager", "operations specialist"]),
        ("Program Manager",     ["program manager", "program lead",
                                 "program director", "program coordinator"]),
        ("Strategy",            ["chief of staff", "strategy & operations",
                                 "strategic operations", "strategy and operations"]),
    ]

    def normalize(title: str) -> str:
        return (
            title.lower()
            .replace("sr.", "senior")
            .replace("sr ", "senior ")
        )

    def categorize(title: str) -> str:
        t = normalize(str(title))
        for label, patterns in ROLE_CATEGORIES:
            if any(p in t for p in patterns):
                return label
        return "Other"

    role_col = filt["Position"].apply(categorize)
    role_data = []
    for cat in [c for c, _ in ROLE_CATEGORIES] + ["Other"]:
        mask = role_col == cat
        apps = int(mask.sum())
        if apps < 5:
            continue
        interviews = int((filt[mask]["Outcome"].str.lower() == "interview").sum())
        rate = round(interviews / apps * 100, 1)
        role_data.append({"Role": cat, "Apps": apps, "Interviews": interviews, "Rate": rate})

    sort_col = "Interviews" if role_sort == "Total Interviews" else "Rate"
    role_df = pd.DataFrame(role_data).sort_values(sort_col, ascending=True)

    if role_sort == "Total Interviews":
        x_vals      = role_df["Interviews"]
        bar_colors_role = [POSITIVE if v == x_vals.max() else "rgba(0,229,160,0.35)" for v in x_vals]
        bar_text    = [f"{i}  ({r}% rate)" for i, r in zip(role_df["Interviews"], role_df["Rate"])]
        x_suffix    = ""
        x_range     = [0, x_vals.max() * 1.6 if len(role_df) else 1]
        hover_tmpl  = "<b>%{y}</b><br>Interviews: %{x}<br>Apps: %{customdata[0]}<br>Rate: %{customdata[1]}%<extra></extra>"
    else:
        x_vals      = role_df["Rate"]
        bar_colors_role = [
            POSITIVE if r == role_df["Rate"].max() else
            NEGATIVE if r == role_df["Rate"].min() else
            "rgba(123,110,246,0.4)"
            for r in role_df["Rate"]
        ]
        bar_text    = [f"{r}%  ({a} apps)" for r, a in zip(role_df["Rate"], role_df["Apps"])]
        x_suffix    = "%"
        x_range     = [0, role_df["Rate"].max() * 1.6 if len(role_df) else 1]
        hover_tmpl  = "<b>%{y}</b><br>Interview rate: %{x}%<br>Apps: %{customdata[0]}<br>Interviews: %{customdata[1]}<extra></extra>"

    fig_role = go.Figure()
    fig_role.add_trace(go.Bar(
        x=x_vals,
        y=role_df["Role"],
        orientation="h",
        marker_color=bar_colors_role,
        marker_line_width=0,
        text=bar_text,
        textposition="outside",
        textfont=dict(color=TEXT, size=11),
        customdata=list(zip(role_df["Apps"], role_df["Interviews"])),
        hovertemplate=hover_tmpl,
    ))
    fig_role.update_layout(dark_layout(
        title=dict(
            text="Each role assigned to one primary category (first match)",
            font=dict(color=MUTED, size=11),
            x=0, xanchor="left", pad=dict(l=0),
        ),
        xaxis=dict(
            gridcolor=BORDER,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(color=MUTED, size=11),
            ticksuffix=x_suffix,
            showgrid=True,
            range=x_range,
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(color=TEXT, size=12),
            showgrid=False,
        ),
        showlegend=False,
        height=max(320, len(role_df) * 42 + 80),
        bargap=0.3,
        margin=dict(l=140, r=100, t=44, b=40),
    ))
    st.plotly_chart(fig_role, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── Bottom row: Top Companies + Recent Activity ───────────────────────────────
# ── Top Companies card ────────────────────────────────────────────────────────
if True:
    st.markdown("### Top Companies")

    co_sort = st.segmented_control(
        "Sort companies by",
        options=["Most Applied", "Most Responsive", "Least Responsive"],
        default="Most Applied",
        label_visibility="collapsed",
    )

    co_df = filt[filt["Company"] != ""].copy()
    co_df["_responded"] = co_df["Response Date"].notna()

    top_companies = (
        co_df
        .groupby("Company")
        .agg(
            Applications=("Company", "count"),
            Last_Applied=("Date Applied", "max"),
            Responses=("_responded", "sum"),
        )
        .reset_index()
    )
    top_companies["Response_Rate"] = (
        top_companies["Responses"] / top_companies["Applications"] * 100
    ).round(0).astype(int)

    if co_sort in ("Most Responsive", "Least Responsive"):
        max_apps = int(top_companies["Applications"].max())
        min_apps = st.slider(
            "Min. applications (for reliable sample)",
            min_value=1,
            max_value=max(max_apps, 2),
            value=min(2, max_apps),
            step=1,
        )
        top_companies = top_companies[top_companies["Applications"] >= min_apps]
        ascending = co_sort == "Least Responsive"
        top_companies = top_companies.sort_values("Response_Rate", ascending=ascending).head(15)
    else:
        top_companies = top_companies.sort_values("Applications", ascending=False).head(15)

    co_rows = ""
    for rank, (_, row) in enumerate(top_companies.iterrows(), 1):
        last_date = row["Last_Applied"].strftime("%b %d, %Y") if not pd.isna(row["Last_Applied"]) else "—"
        rr = int(row["Response_Rate"])
        if rr >= 67:
            rr_color = POSITIVE
            rr_bg = "rgba(0,229,160,0.12)"
        elif rr >= 34:
            rr_color = PENDING
            rr_bg = "rgba(255,181,71,0.12)"
        else:
            rr_color = NEGATIVE
            rr_bg = "rgba(255,87,87,0.12)"
        co_rows += f"""
        <tr>
          <td class="rank">#{rank}</td>
          <td class="company">{row['Company']}</td>
          <td class="count">{int(row['Applications'])}</td>
          <td class="date">{last_date}</td>
          <td><span style="background:{rr_bg};color:{rr_color};padding:3px 8px;border-radius:99px;font-size:0.72rem;font-weight:700">{rr}%</span></td>
        </tr>"""

    companies_html = f"""
    <div class="wrap">
      <table class="tbl">
        <thead>
          <tr>
            <th></th>
            <th>Company</th>
            <th>Apps</th>
            <th>Last Applied</th>
            <th>Response</th>
          </tr>
        </thead>
        <tbody>
          {co_rows if co_rows else f'<tr><td colspan="4" class="empty">No data</td></tr>'}
        </tbody>
      </table>
    </div>"""

    components.html(f"""
    <!DOCTYPE html><html><head>
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: transparent; font-family: Inter, -apple-system, sans-serif; }}
      .wrap {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 12px;
        overflow: hidden;
      }}
      .tbl {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
      .tbl th {{
        background: {BG};
        color: {MUTED};
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        font-weight: 700;
        padding: 10px 14px;
        text-align: left;
        border-bottom: 1px solid {BORDER};
      }}
      .tbl td {{ padding: 9px 14px; border-bottom: 1px solid {BORDER}; }}
      .tbl tr:last-child td {{ border-bottom: none; }}
      .tbl tr:hover td {{ background: rgba(123,110,246,0.05); }}
      .rank {{ color: {MUTED}; font-size: 0.72rem; font-weight: 700; width: 28px; }}
      .company {{ color: {TEXT}; font-weight: 600; }}
      .count {{
        color: {ACCENT};
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        text-align: center;
        width: 44px;
      }}
      .date {{ color: {MUTED}; font-size: 0.8rem; white-space: nowrap; }}
      .empty {{ color: {MUTED}; text-align: center; padding: 2rem; }}
    </style>
    </head><body>
    {companies_html}
    </body></html>
    """, height=min(56 + len(top_companies) * 41, 680), scrolling=False)

# ── Company response times ────────────────────────────────────────────────────
st.markdown("### Average Response Time by Company")

co_resp_sort = st.segmented_control(
    "Sort by",
    options=["Fastest Overall", "Slowest Overall", "Most Responses"],
    default="Fastest Overall",
    label_visibility="collapsed",
    key="co_resp_sort",
)

responded = filt[filt["Days in Between"].notna() & (filt["Company"] != "")].copy()

co_resp = (
    responded
    .groupby("Company")
    .agg(
        Total_Apps=("Company", "count"),
        Avg_Days=("Days in Between", "mean"),
    )
    .reset_index()
)
co_resp["Avg_Days"] = co_resp["Avg_Days"].round(1)

# Rejection avg per company
rej_avg = (
    responded[responded["Outcome"].str.lower().isin(["rejection", "rejected"])]
    .groupby("Company")["Days in Between"]
    .mean()
    .round(1)
    .rename("Rej_Avg")
)

# Interview avg per company
int_avg = (
    responded[responded["Outcome"].str.lower() == "interview"]
    .groupby("Company")["Days in Between"]
    .mean()
    .round(1)
    .rename("Int_Avg")
)

co_resp = co_resp.join(rej_avg, on="Company").join(int_avg, on="Company")

max_resp = int(co_resp["Total_Apps"].max()) if len(co_resp) else 2
min_resp_threshold = st.slider(
    "Min. responses (for reliable sample)",
    min_value=1,
    max_value=max(max_resp, 2),
    value=min(2, max_resp),
    step=1,
    key="co_resp_min",
)
co_resp = co_resp[co_resp["Total_Apps"] >= min_resp_threshold]

if co_resp_sort == "Slowest Overall":
    co_resp = co_resp.sort_values("Avg_Days", ascending=False)
elif co_resp_sort == "Most Responses":
    co_resp = co_resp.sort_values("Total_Apps", ascending=False)
else:
    co_resp = co_resp.sort_values("Avg_Days", ascending=True)

co_resp = co_resp.head(25)

def fmt_days_val(val):
    if pd.isna(val):
        return f'<span style="color:{MUTED}">—</span>'
    return f"{val:.0f}d"

def speed_color(val, col_min, col_max):
    """Green = fast, red = slow."""
    if pd.isna(val) or col_max == col_min:
        return MUTED
    ratio = (val - col_min) / (col_max - col_min)
    if ratio < 0.33:
        return POSITIVE
    if ratio < 0.66:
        return PENDING
    return NEGATIVE

col_min = co_resp["Avg_Days"].min()
col_max = co_resp["Avg_Days"].max()

resp_rows = ""
for _, row in co_resp.iterrows():
    color = speed_color(row["Avg_Days"], col_min, col_max)
    resp_rows += f"""
    <tr>
      <td class="company">{row['Company']}</td>
      <td class="num">{int(row['Total_Apps'])}</td>
      <td><span style="color:{color};font-weight:700">{fmt_days_val(row['Avg_Days'])}</span></td>
      <td class="num">{fmt_days_val(row['Rej_Avg'])}</td>
      <td class="num" style="color:{POSITIVE if not pd.isna(row['Int_Avg']) else MUTED};font-weight:{'700' if not pd.isna(row['Int_Avg']) else '400'}">{fmt_days_val(row['Int_Avg'])}</td>
    </tr>"""

components.html(f"""
<!DOCTYPE html><html><head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; font-family: Inter, -apple-system, sans-serif; }}
  .wrap {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
  th {{
    background: {BG}; color: {MUTED}; font-size: 0.68rem;
    text-transform: uppercase; letter-spacing: 0.09em; font-weight: 700;
    padding: 10px 16px; text-align: left; border-bottom: 1px solid {BORDER};
    white-space: nowrap;
  }}
  td {{ padding: 9px 16px; color: {TEXT}; border-bottom: 1px solid {BORDER}; white-space: nowrap; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(123,110,246,0.05); }}
  .company {{ font-weight: 600; min-width: 200px; }}
  .num {{ color: {MUTED}; font-variant-numeric: tabular-nums; }}
</style>
</head><body>
<div class="wrap">
  <table>
    <thead>
      <tr>
        <th>Company</th>
        <th>Responses</th>
        <th>Avg. Days (Overall)</th>
        <th>Avg. Days to Rejection</th>
        <th>Avg. Days to Interview</th>
      </tr>
    </thead>
    <tbody>
      {resp_rows if resp_rows else f'<tr><td colspan="5" style="text-align:center;color:{MUTED};padding:2rem">No data</td></tr>'}
    </tbody>
  </table>
</div>
</body></html>
""", height=min(56 + len(co_resp) * 41, 900), scrolling=False)

st.markdown("<br>", unsafe_allow_html=True)


# ── Recent Activity ───────────────────────────────────────────────────────────
if True:
    st.markdown("### Recent Activity")

    recent_cols = ["Company", "Position", "Date Applied", "Response Date", "Days in Between", "Outcome"]
    recent = (
        filt
        .sort_values("Date Applied", ascending=False)
        .head(20)[recent_cols]
    )

    def outcome_badge(val: str) -> str:
        v = str(val).strip().lower()
        if v == "interview":
            return f'<span class="badge badge-interview">{val}</span>'
        if v in ("rejected", "rejection"):
            return f'<span class="badge badge-rejected">{val}</span>'
        if v == "offer":
            return f'<span class="badge badge-offer">{val}</span>'
        return f'<span class="badge badge-pending">{val}</span>'

    def fmt_date(val) -> str:
        if pd.isna(val):
            return '<span style="color:' + MUTED + '">—</span>'
        return val.strftime("%b %d, %Y")

    def fmt_days(val) -> str:
        if pd.isna(val):
            return '<span style="color:' + MUTED + '">—</span>'
        return f"{int(val)}d"

    rows_html = ""
    for _, row in recent.iterrows():
        rows_html += f"""
        <tr>
          <td><strong style="color:{TEXT}">{row['Company'] or '—'}</strong></td>
          <td style="color:{MUTED}">{row['Position'] or '—'}</td>
          <td>{fmt_date(row['Date Applied'])}</td>
          <td>{fmt_date(row['Response Date'])}</td>
          <td style="font-variant-numeric:tabular-nums">{fmt_days(row['Days in Between'])}</td>
          <td>{outcome_badge(row['Outcome'])}</td>
        </tr>"""

    table_html = f"""
    <div class="activity-wrap">
      <table class="activity-table">
        <thead>
          <tr>
            <th>Company</th>
            <th>Position</th>
            <th>Date Applied</th>
            <th>Response Date</th>
            <th>Days</th>
            <th>Outcome</th>
          </tr>
        </thead>
        <tbody>
          {rows_html if rows_html else f'<tr><td colspan="6" style="text-align:center;color:{MUTED};padding:2rem">No results match the current filters.</td></tr>'}
        </tbody>
      </table>
    </div>
    """

    components.html(f"""
    <!DOCTYPE html><html><head>
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: transparent; font-family: Inter, -apple-system, sans-serif; }}
      .activity-wrap {{
        overflow-x: auto;
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 12px;
      }}
      .activity-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
      }}
      .activity-table th {{
        background-color: {BG};
        color: {MUTED};
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        font-weight: 700;
        padding: 10px 16px;
        text-align: left;
        border-bottom: 1px solid {BORDER};
        white-space: nowrap;
      }}
      .activity-table td {{
        padding: 10px 16px;
        color: {TEXT};
        border-bottom: 1px solid {BORDER};
        white-space: nowrap;
      }}
      .activity-table tr:last-child td {{ border-bottom: none; }}
      .activity-table tr:hover td {{ background-color: rgba(123,110,246,0.05); }}
      .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 99px;
        font-size: 0.72rem;
        font-weight: 700;
      }}
      .badge-interview {{ background: rgba(0,229,160,0.12);  color: {POSITIVE}; }}
      .badge-rejected  {{ background: rgba(255,87,87,0.12);  color: {NEGATIVE}; }}
      .badge-offer     {{ background: rgba(123,110,246,0.18); color: {ACCENT}; }}
      .badge-pending   {{ background: rgba(255,181,71,0.12); color: {PENDING}; }}
    </style>
    </head><body>
    {table_html}
    </body></html>
    """, height=min(80 + len(recent) * 41, 860), scrolling=False)
