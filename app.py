import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date, datetime, timedelta

import database as db
import calendar_reader as cal
from config import PILLARS, DEFAULT_TASKS, get_week_start, get_week_end

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="My Productivity Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* Hide default Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Global font */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 600;
        padding: 8px 0;
    }

    /* Pillar colour strips */
    .p1 { border-left: 5px solid #0078D4; padding-left: 12px; border-radius: 0 6px 6px 0; background:#EBF3FB; padding: 10px 14px; margin-bottom:6px; }
    .p2 { border-left: 5px solid #FF6B35; padding-left: 12px; border-radius: 0 6px 6px 0; background:#FFF0EB; padding: 10px 14px; margin-bottom:6px; }
    .p3 { border-left: 5px solid #00A86B; padding-left: 12px; border-radius: 0 6px 6px 0; background:#EBFAF3; padding: 10px 14px; margin-bottom:6px; }
    .p4 { border-left: 5px solid #9B59B6; padding-left: 12px; border-radius: 0 6px 6px 0; background:#F5EEF8; padding: 10px 14px; margin-bottom:6px; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #F8F9FA;
        border-radius: 10px;
        padding: 12px 16px;
    }

    /* Section headers */
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 16px 0 8px 0;
    }

    /* Task complete style */
    .task-done { text-decoration: line-through; color: #999; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "calendar_loaded" not in st.session_state:
    st.session_state.calendar_loaded = False
if "week_events" not in st.session_state:
    st.session_state.week_events = {}
if "free_slots_today" not in st.session_state:
    st.session_state.free_slots_today = []
if "user_name" not in st.session_state:
    st.session_state.user_name = "Parisa"


# ── Helper functions ──────────────────────────────────────────────────────────
def pillar_css_class(pid):
    return f"p{pid}"


def load_calendar():
    with st.spinner("Connecting to Outlook..."):
        try:
            info = cal.get_user_info()
            st.session_state.user_name = info.get("givenName", "Parisa")
            week_start = get_week_start()
            st.session_state.week_events = cal.get_week_events(week_start)
            today = date.today()
            st.session_state.free_slots_today = cal.get_free_slots(today)
            st.session_state.calendar_loaded = True
            return True
        except Exception as e:
            st.error(f"Could not load calendar: {e}")
            return False


def progress_bar_html(value, max_value, color):
    if max_value and max_value > 0:
        pct = min(int(value / max_value * 100), 100)
    else:
        pct = 0
    return f"""
    <div style="background:#e9ecef; border-radius:6px; height:10px; margin:4px 0 8px 0;">
        <div style="width:{pct}%; background:{color}; height:10px; border-radius:6px; transition:width 0.4s;"></div>
    </div>
    <small style="color:#666;">{value} / {max_value or '∞'} min &nbsp;·&nbsp; {pct}%</small>
    """


def format_time(minutes):
    if minutes < 60:
        return f"{minutes}m"
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m}m" if m else f"{h}h"


# ── Header ────────────────────────────────────────────────────────────────────
today = date.today()
greeting_hour = datetime.now().hour
greeting = "Good morning" if greeting_hour < 12 else ("Good afternoon" if greeting_hour < 17 else "Good evening")

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.markdown(f"## 🎯 {greeting}, {st.session_state.user_name}!")
    st.caption(f"{today.strftime('%A, %B %d, %Y')} · Week of {get_week_start().strftime('%b %d')}")

with col_btn:
    st.write("")
    if st.button("🔄 Sync Outlook", use_container_width=True, type="secondary", help="Sign in with your personal Microsoft account"):
        success = load_calendar()
        if success:
            event_count = sum(len(v) for v in st.session_state.week_events.values())
            st.success(f"Outlook connected! Found {event_count} event(s) this week.", icon="✅")
        else:
            st.warning("Outlook sync unavailable. Use the app manually — all task & time tracking works without it.", icon="ℹ️")

st.divider()

# Don't auto-load calendar — let user trigger it manually


# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_today, tab_week, tab_dashboard, tab_add = st.tabs([
    "📅 Today's Plan",
    "📆 This Week",
    "🏆 Weekly Dashboard",
    "➕ Add Task",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 – TODAY'S PLAN
# ════════════════════════════════════════════════════════════════════════════════
with tab_today:
    left, right = st.columns([3, 2], gap="large")

    # ── Left: tasks per pillar ────────────────────────────────────────────────
    with left:
        st.markdown('<div class="section-title">Today\'s Tasks</div>', unsafe_allow_html=True)

        tasks_today = db.get_tasks_for_date(today)
        time_today = db.get_time_for_date(today)

        if not tasks_today:
            st.info("No tasks for today yet. Use **Add Task** tab or click a suggestion below to get started.")

        for pid, pillar in PILLARS.items():
            ptasks = [t for t in tasks_today if t["pillar_id"] == pid]
            logged = time_today.get(pid, 0)
            budget = pillar["daily_budget_min"]

            with st.expander(
                f"{pillar['icon']} **{pillar['name']}** · {len(ptasks)} task(s) · {format_time(logged)} logged",
                expanded=True
            ):
                for task in ptasks:
                    c1, c2 = st.columns([6, 1])
                    with c1:
                        done = st.checkbox(
                            task["title"],
                            value=bool(task["is_completed"]),
                            key=f"task_{task['id']}",
                        )
                    with c2:
                        if st.button("🗑", key=f"del_{task['id']}", help="Delete task"):
                            db.delete_task(task["id"])
                            st.rerun()

                    if done and not task["is_completed"]:
                        db.complete_task(task["id"], task["est_minutes"])
                        st.rerun()
                    elif not done and task["is_completed"]:
                        db.uncomplete_task(task["id"])
                        st.rerun()

                # Quick add from defaults
                st.markdown("**Quick add:**")
                cols = st.columns(2)
                for i, suggestion in enumerate(DEFAULT_TASKS[pid][:4]):
                    if cols[i % 2].button(f"+ {suggestion}", key=f"sug_{pid}_{i}", use_container_width=True):
                        db.add_task(suggestion, pid, today)
                        st.rerun()

    # ── Right: free slots + pillar budgets ────────────────────────────────────
    with right:
        # Pillar budget overview
        st.markdown('<div class="section-title">Today\'s Budget</div>', unsafe_allow_html=True)
        for pid, pillar in PILLARS.items():
            logged = time_today.get(pid, 0)
            budget = pillar["daily_budget_min"]
            st.markdown(f"{pillar['icon']} **{pillar['short']}**")
            st.markdown(
                progress_bar_html(logged, budget, pillar["color"]),
                unsafe_allow_html=True
            )

        # Log time form
        st.markdown('<div class="section-title">Log Time</div>', unsafe_allow_html=True)
        with st.form("log_time_form", clear_on_submit=True):
            log_pillar = st.selectbox(
                "Pillar",
                options=list(PILLARS.keys()),
                format_func=lambda x: f"{PILLARS[x]['icon']} {PILLARS[x]['name']}",
            )
            log_mins = st.number_input("Minutes spent", min_value=5, max_value=480, value=30, step=5)
            log_desc = st.text_input("What did you work on?", placeholder="Optional")
            if st.form_submit_button("Log Time ✅", use_container_width=True, type="primary"):
                db.log_time(log_pillar, today, log_mins, log_desc)
                st.success(f"Logged {log_mins} min to {PILLARS[log_pillar]['name']}!")
                st.rerun()

        # Free slots from Outlook
        if st.session_state.calendar_loaded and st.session_state.free_slots_today:
            st.markdown('<div class="section-title">Free Slots Today</div>', unsafe_allow_html=True)
            for slot in st.session_state.free_slots_today:
                s = slot["start"].strftime("%I:%M %p")
                e = slot["end"].strftime("%I:%M %p")
                d = format_time(slot["duration_minutes"])
                st.markdown(
                    f'<div style="background:#F0F7FF; border-radius:6px; padding:8px 12px; margin:4px 0;">'
                    f'🕐 {s} – {e} <span style="color:#0078D4; font-weight:600;">({d} free)</span></div>',
                    unsafe_allow_html=True
                )
        elif st.session_state.calendar_loaded:
            st.caption("No free slots found today — you're fully booked!")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 – THIS WEEK
# ════════════════════════════════════════════════════════════════════════════════
with tab_week:
    week_start = get_week_start()
    tasks_week = db.get_tasks_for_week(week_start)
    time_week = db.get_time_for_week(week_start)

    # Weekly pillar summary
    st.markdown('<div class="section-title">Weekly Pillar Progress</div>', unsafe_allow_html=True)

    cols = st.columns(4)
    for i, (pid, pillar) in enumerate(PILLARS.items()):
        with cols[i]:
            logged = time_week.get(pid, 0)
            budget = pillar["weekly_budget_min"]
            pct = min(int(logged / budget * 100), 100) if budget else 0
            ptasks = [t for t in tasks_week if t["pillar_id"] == pid]
            done = sum(1 for t in ptasks if t["is_completed"])

            st.markdown(
                f'<div style="background:{pillar["bg"]}; border-left:5px solid {pillar["color"]}; '
                f'border-radius:0 10px 10px 0; padding:16px; margin-bottom:8px;">'
                f'<div style="font-size:1.4rem;">{pillar["icon"]}</div>'
                f'<div style="font-weight:700; font-size:0.95rem;">{pillar["name"]}</div>'
                f'<div style="font-size:1.6rem; font-weight:800; color:{pillar["color"]};">{format_time(logged)}</div>'
                f'<div style="color:#666; font-size:0.8rem;">of {format_time(budget) if budget else "∞"} target</div>'
                f'<div style="background:#e9ecef; border-radius:6px; height:8px; margin:8px 0;">'
                f'<div style="width:{pct}%; background:{pillar["color"]}; height:8px; border-radius:6px;"></div></div>'
                f'<div style="font-size:0.8rem; color:#555;">{done}/{len(ptasks)} tasks done</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    # Day-by-day task list
    st.markdown('<div class="section-title">Tasks This Week</div>', unsafe_allow_html=True)
    days = [week_start + timedelta(days=i) for i in range(5)]  # Mon–Fri

    for d in days:
        day_tasks = [t for t in tasks_week if t["task_date"] == str(d)]
        is_today = d == today
        label = d.strftime("%A, %b %d") + (" ← Today" if is_today else "")
        done_count = sum(1 for t in day_tasks if t["is_completed"])

        with st.expander(f"{'📍 ' if is_today else ''}{label}  ({done_count}/{len(day_tasks)} done)", expanded=is_today):
            if not day_tasks:
                st.caption("No tasks planned.")
            for task in day_tasks:
                pid = task["pillar_id"]
                icon = PILLARS[pid]["icon"]
                color = PILLARS[pid]["color"]
                style = "line-through; color:#aaa" if task["is_completed"] else f"color:#111"
                est = format_time(task["est_minutes"])
                st.markdown(
                    f'<div style="display:flex; align-items:center; gap:8px; padding:4px 0;">'
                    f'<span style="color:{color}; font-size:1.1rem;">{icon}</span>'
                    f'<span style="text-decoration:{style}; flex:1;">{task["title"]}</span>'
                    f'<span style="font-size:0.75rem; color:#999;">{est}</span>'
                    f'{"<span style=\"color:green;\">✓</span>" if task["is_completed"] else ""}'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # Outlook calendar events this week
    if st.session_state.calendar_loaded and st.session_state.week_events:
        st.markdown('<div class="section-title">Outlook Calendar This Week</div>', unsafe_allow_html=True)
        for d in days:
            date_str = str(d)
            events = st.session_state.week_events.get(date_str, [])
            if events:
                day_label = d.strftime("%A %b %d")
                with st.expander(f"📅 {day_label} — {len(events)} meeting(s)"):
                    for ev in events:
                        s_raw = ev["start"]["dateTime"][:16].replace("T", " ")
                        e_raw = ev["end"]["dateTime"][:16].replace("T", " ")
                        show_as = ev.get("showAs", "")
                        badge = "🔴" if show_as == "busy" else "🟡"
                        st.markdown(f"{badge} **{ev['subject']}** &nbsp; `{s_raw} → {e_raw}`")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 – WEEKLY DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    week_start = get_week_start()
    time_week = db.get_time_for_week(week_start)
    stats = db.get_week_completion_stats(week_start)
    daily_data = db.get_daily_breakdown_for_week(week_start)

    # Top-level metrics
    total_logged = sum(time_week.values())
    total_tasks = sum(s["total"] for s in stats.values())
    total_done = sum(s["completed"] for s in stats.values())
    completion_pct = int(total_done / total_tasks * 100) if total_tasks else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Hours This Week", f"{total_logged // 60}h {total_logged % 60}m")
    m2.metric("Tasks Completed", f"{total_done} / {total_tasks}")
    m3.metric("Completion Rate", f"{completion_pct}%")
    m4.metric("Week of", week_start.strftime("%b %d"))

    st.divider()

    chart_left, chart_right = st.columns(2)

    # ── Donut chart: time per pillar ──────────────────────────────────────────
    with chart_left:
        st.markdown("#### Time Distribution by Pillar")
        labels = []
        values = []
        colors = []
        for pid, pillar in PILLARS.items():
            mins = time_week.get(pid, 0)
            if mins > 0:
                labels.append(f"{pillar['icon']} {pillar['name']}")
                values.append(mins)
                colors.append(pillar["color"])

        if values:
            fig = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker_colors=colors,
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value} min<extra></extra>",
            ))
            fig.update_layout(
                showlegend=False,
                margin=dict(t=20, b=20, l=0, r=0),
                height=320,
                annotations=[dict(
                    text=f"<b>{format_time(total_logged)}</b>",
                    x=0.5, y=0.5,
                    font_size=18, showarrow=False
                )]
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No time logged this week yet. Use the Log Time widget on the Today tab.")

    # ── Bar chart: daily breakdown ────────────────────────────────────────────
    with chart_right:
        st.markdown("#### Daily Hours by Pillar")
        days_of_week = [get_week_start() + timedelta(days=i) for i in range(5)]
        day_labels = [d.strftime("%a %d") for d in days_of_week]

        if daily_data:
            df = pd.DataFrame(daily_data)
            df["log_date"] = pd.to_datetime(df["log_date"])
            df["day_label"] = df["log_date"].dt.strftime("%a %d")
            df["pillar_name"] = df["pillar_id"].map(lambda x: PILLARS[x]["name"])
            df["hours"] = df["total_minutes"] / 60

            fig2 = px.bar(
                df,
                x="day_label",
                y="hours",
                color="pillar_name",
                color_discrete_map={PILLARS[p]["name"]: PILLARS[p]["color"] for p in PILLARS},
                labels={"hours": "Hours", "day_label": "Day", "pillar_name": "Pillar"},
                barmode="stack",
                height=320,
            )
            fig2.update_layout(
                margin=dict(t=20, b=20, l=0, r=0),
                legend=dict(orientation="h", yanchor="bottom", y=-0.4),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No time logged this week yet.")

    # ── Goal achievement cards ────────────────────────────────────────────────
    st.markdown("#### Goal Achievement")
    gcols = st.columns(4)
    for i, (pid, pillar) in enumerate(PILLARS.items()):
        with gcols[i]:
            logged = time_week.get(pid, 0)
            budget = pillar["weekly_budget_min"]
            pct = min(int(logged / budget * 100), 100) if budget else 100
            achieved = pct >= 80
            s = stats.get(pid, {})
            done = s.get("completed", 0)
            total = s.get("total", 0)

            badge = "🏆" if pct >= 100 else ("✅" if pct >= 80 else ("⚡" if pct >= 50 else "💤"))
            st.markdown(
                f'<div style="text-align:center; background:{pillar["bg"]}; '
                f'border:2px solid {pillar["color"] if achieved else "#ddd"}; '
                f'border-radius:12px; padding:16px;">'
                f'<div style="font-size:2rem;">{badge}</div>'
                f'<div style="font-weight:700; font-size:0.9rem; color:{pillar["color"]};">{pillar["icon"]} {pillar["short"]}</div>'
                f'<div style="font-size:1.5rem; font-weight:800;">{pct}%</div>'
                f'<div style="font-size:0.75rem; color:#666;">{format_time(logged)} of {format_time(budget) if budget else "∞"}</div>'
                f'<div style="font-size:0.75rem; color:#888; margin-top:4px;">{done}/{total} tasks</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    # ── Week selector ─────────────────────────────────────────────────────────
    st.divider()
    st.caption("💡 Dashboard shows the current week. Historical weeks coming soon.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 – ADD TASK
# ════════════════════════════════════════════════════════════════════════════════
with tab_add:
    st.markdown("### Add a New Task")
    col1, col2 = st.columns(2)

    with col1:
        with st.form("add_task_form", clear_on_submit=True):
            task_title = st.text_input("Task title *", placeholder="e.g. Update resume intro section")
            task_pillar = st.selectbox(
                "Pillar *",
                options=list(PILLARS.keys()),
                format_func=lambda x: f"{PILLARS[x]['icon']} {PILLARS[x]['name']}",
            )
            task_date = st.date_input("Date *", value=today)
            task_est = st.number_input("Estimated time (minutes)", min_value=5, max_value=480, value=30, step=5)
            task_notes = st.text_area("Notes (optional)", height=80)

            submitted = st.form_submit_button("Add Task ✅", use_container_width=True, type="primary")
            if submitted:
                if task_title.strip():
                    db.add_task(task_title.strip(), task_pillar, task_date, task_est, task_notes)
                    st.success(f"Task added to **{PILLARS[task_pillar]['name']}** on {task_date}!")
                else:
                    st.error("Please enter a task title.")

    with col2:
        st.markdown("#### Quick suggestions")
        st.caption("Click any suggestion to add it to today's list instantly.")
        for pid, pillar in PILLARS.items():
            st.markdown(f"**{pillar['icon']} {pillar['name']}**")
            scols = st.columns(2)
            for j, sug in enumerate(DEFAULT_TASKS[pid]):
                if scols[j % 2].button(sug, key=f"qadd_{pid}_{j}", use_container_width=True):
                    db.add_task(sug, pid, today)
                    st.success(f"Added: {sug}")
                    st.rerun()
            st.write("")
