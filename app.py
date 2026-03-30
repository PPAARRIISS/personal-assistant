import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date, datetime, timedelta

import database as db
import auth
from templates import TEMPLATES
from config import get_week_start, get_week_end

st.set_page_config(
    page_title="Track-It",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; font-weight: 600; padding: 8px 0; }
    div[data-testid="metric-container"] { background: #F8F9FA; border-radius: 10px; padding: 12px 16px; }
    .section-title { font-size: 1.1rem; font-weight: 700; color: #1a1a2e; margin: 16px 0 8px 0; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
for key, val in {
    "logged_in": False,
    "username": None,
    "user_name": None,
    "onboarded": False,
    "page": "login",  # login | signup | onboard | app
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


def logout():
    for key in ["logged_in", "username", "user_name", "onboarded"]:
        st.session_state[key] = False if key == "logged_in" else None
    st.session_state.page = "login"
    st.rerun()


def format_time(minutes):
    if not minutes:
        return "0m"
    if minutes < 60:
        return f"{minutes}m"
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m}m" if m else f"{h}h"


def progress_bar_html(value, max_value, color):
    pct = min(int(value / max_value * 100), 100) if max_value else 0
    return f"""
    <div style="background:#e9ecef;border-radius:6px;height:10px;margin:4px 0 8px 0;">
        <div style="width:{pct}%;background:{color};height:10px;border-radius:6px;transition:width 0.4s;"></div>
    </div>
    <small style="color:#666;">{value} / {max_value or '∞'} min &nbsp;·&nbsp; {pct}%</small>
    """


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_login():
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("## 🎯 Track-It")
        st.markdown("#### Sign in to your account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            if submitted:
                ok, name, onboarded = auth.verify_login(username, password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.username = username.strip().lower()
                    st.session_state.user_name = name
                    st.session_state.onboarded = onboarded
                    st.session_state.page = "app" if onboarded else "onboard"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        st.divider()
        st.markdown("Don't have an account?")
        if st.button("Create one →", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SIGN UP PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_signup():
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("## 🎯 Track-It")
        st.markdown("#### Create your account")
        with st.form("signup_form"):
            name = st.text_input("Your name")
            username = st.text_input("Username (no spaces)")
            email = st.text_input("Email address")
            password = st.text_input("Password (min 6 characters)", type="password")
            password2 = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
            if submitted:
                if password != password2:
                    st.error("Passwords don't match.")
                else:
                    ok, err = auth.register_user(username, name, email, password)
                    if ok:
                        st.success("Account created! Signing you in...")
                        st.session_state.logged_in = True
                        st.session_state.username = username.strip().lower()
                        st.session_state.user_name = name
                        st.session_state.onboarded = False
                        st.session_state.page = "onboard"
                        st.rerun()
                    else:
                        st.error(err)
        st.divider()
        if st.button("← Back to sign in", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ONBOARDING PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_onboarding():
    st.markdown(f"## 👋 Welcome, {st.session_state.user_name}!")
    st.markdown("#### Let's set up your personal dashboard. Choose a template to get started:")

    cols = st.columns(3)
    template_keys = list(TEMPLATES.keys())

    for i, key in enumerate(template_keys):
        t = TEMPLATES[key]
        with cols[i % 3]:
            st.markdown(f"""
            <div style="border:2px solid #ddd;border-radius:12px;padding:16px;margin-bottom:12px;min-height:120px;">
                <div style="font-size:1.2rem;font-weight:700;">{t['label']}</div>
                <div style="color:#666;font-size:0.85rem;margin-top:6px;">{t['description']}</div>
                <div style="margin-top:8px;font-size:0.8rem;color:#888;">
                    {"  ".join([p['icon'] + ' ' + p['name'] for p in t['pillars']]) if t['pillars'] else "You'll create your own pillars"}
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Use this template", key=f"tmpl_{key}", use_container_width=True):
                if t["pillars"]:
                    db.seed_pillars(st.session_state.username, t["pillars"])
                auth.mark_onboarded(st.session_state.username)
                st.session_state.onboarded = True
                st.session_state.page = "app"
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PILLAR MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def show_pillar_manager(pillars):
    st.markdown("### ⚙️ Manage Your Pillars")

    # Add new pillar
    with st.expander("➕ Add New Pillar", expanded=len(pillars) == 0):
        with st.form("add_pillar_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            p_name = c1.text_input("Name *", placeholder="e.g. Health")
            p_icon = c2.text_input("Icon (emoji) *", placeholder="e.g. 🏃", value="📌")
            p_color = c3.color_picker("Color", value="#0078D4")
            c4, c5 = st.columns(2)
            p_daily = c4.number_input("Daily budget (min, 0 = unlimited)", min_value=0, value=0, step=15)
            p_weekly = c5.number_input("Weekly budget (min, 0 = unlimited)", min_value=0, value=0, step=30)

            def hex_to_light(hex_color):
                hex_color = hex_color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                return f"rgba({r},{g},{b},0.1)"

            if st.form_submit_button("Add Pillar ✅", use_container_width=True, type="primary"):
                if p_name.strip() and p_icon.strip():
                    bg = hex_to_light(p_color)
                    db.add_pillar(
                        st.session_state.username,
                        p_name.strip(), p_icon.strip(), p_color, bg,
                        p_daily if p_daily > 0 else None,
                        p_weekly if p_weekly > 0 else None
                    )
                    st.success(f"Pillar '{p_name}' added!")
                    st.rerun()
                else:
                    st.error("Name and icon are required.")

    # Edit / delete existing pillars
    if pillars:
        st.markdown("#### Your Pillars")
        for p in pillars:
            with st.expander(f"{p['icon']} {p['name']}"):
                with st.form(f"edit_pillar_{p['id']}"):
                    c1, c2, c3 = st.columns(3)
                    new_name = c1.text_input("Name", value=p["name"])
                    new_icon = c2.text_input("Icon", value=p["icon"])
                    new_color = c3.color_picker("Color", value=p["color"])
                    c4, c5 = st.columns(2)
                    new_daily = c4.number_input("Daily budget (0=unlimited)", min_value=0,
                                                value=p["daily_budget"] or 0, step=15)
                    new_weekly = c5.number_input("Weekly budget (0=unlimited)", min_value=0,
                                                 value=p["weekly_budget"] or 0, step=30)
                    s1, s2 = st.columns(2)
                    if s1.form_submit_button("Save changes", use_container_width=True, type="primary"):
                        def hex_to_light(hex_color):
                            hex_color = hex_color.lstrip('#')
                            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                            return f"rgba({r},{g},{b},0.1)"
                        db.update_pillar(p["id"], new_name, new_icon, new_color,
                                         hex_to_light(new_color),
                                         new_daily if new_daily > 0 else None,
                                         new_weekly if new_weekly > 0 else None)
                        st.success("Updated!")
                        st.rerun()
                    if s2.form_submit_button("🗑 Delete pillar", use_container_width=True):
                        db.delete_pillar(p["id"])
                        st.warning(f"Pillar '{p['name']}' deleted.")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
def show_app():
    username = st.session_state.username
    pillars = db.get_pillars(username)
    today = date.today()
    greeting_hour = datetime.now().hour
    greeting = "Good morning" if greeting_hour < 12 else ("Good afternoon" if greeting_hour < 17 else "Good evening")

    # Header
    col_title, col_btns = st.columns([4, 1])
    with col_title:
        st.markdown(f"## 🎯 {greeting}, {st.session_state.user_name}!")
        st.caption(f"{today.strftime('%A, %B %d, %Y')} · Week of {get_week_start().strftime('%b %d')}")
    with col_btns:
        st.write("")
        if st.button("Sign Out", use_container_width=True, type="secondary"):
            logout()

    st.divider()

    if not pillars:
        st.info("You have no pillars yet. Add your first one below!")
        show_pillar_manager(pillars)
        return

    tab_today, tab_week, tab_dashboard, tab_add, tab_pillars = st.tabs([
        "📅 Today", "📆 This Week", "🏆 Dashboard", "➕ Add Task", "⚙️ My Pillars"
    ])

    pillar_map = {p["id"]: p for p in pillars}

    # ── TAB 1: TODAY ──────────────────────────────────────────────────────────
    with tab_today:
        left, right = st.columns([3, 2], gap="large")

        with left:
            st.markdown('<div class="section-title">Today\'s Tasks</div>', unsafe_allow_html=True)
            tasks_today = db.get_tasks_for_date(today, username)
            time_today = db.get_time_for_date(today, username)

            if not tasks_today:
                st.info("No tasks for today yet. Use **Add Task** to get started.")

            for p in pillars:
                pid = p["id"]
                ptasks = [t for t in tasks_today if t["pillar_id"] == pid]
                logged = time_today.get(pid, 0)

                with st.expander(
                    f"{p['icon']} **{p['name']}** · {len(ptasks)} task(s) · {format_time(logged)} logged",
                    expanded=True
                ):
                    for task in ptasks:
                        c1, c2 = st.columns([6, 1])
                        with c1:
                            done = st.checkbox(task["title"], value=bool(task["is_completed"]),
                                               key=f"task_{task['id']}")
                        with c2:
                            if st.button("🗑", key=f"del_{task['id']}"):
                                db.delete_task(task["id"])
                                st.rerun()
                        if done and not task["is_completed"]:
                            db.complete_task(task["id"], task["est_minutes"])
                            st.rerun()
                        elif not done and task["is_completed"]:
                            db.uncomplete_task(task["id"])
                            st.rerun()

        with right:
            st.markdown('<div class="section-title">Today\'s Budget</div>', unsafe_allow_html=True)
            for p in pillars:
                logged = time_today.get(p["id"], 0)
                st.markdown(f"{p['icon']} **{p['name']}**")
                st.markdown(progress_bar_html(logged, p["daily_budget"], p["color"]),
                            unsafe_allow_html=True)

            st.markdown('<div class="section-title">Log Time</div>', unsafe_allow_html=True)
            with st.form("log_time_form", clear_on_submit=True):
                log_pillar = st.selectbox("Pillar", options=[p["id"] for p in pillars],
                                          format_func=lambda x: f"{pillar_map[x]['icon']} {pillar_map[x]['name']}")
                log_mins = st.number_input("Minutes spent", min_value=5, max_value=480, value=30, step=5)
                log_desc = st.text_input("What did you work on?", placeholder="Optional")
                if st.form_submit_button("Log Time ✅", use_container_width=True, type="primary"):
                    db.log_time(log_pillar, today, log_mins, log_desc, username)
                    st.success(f"Logged {log_mins} min to {pillar_map[log_pillar]['name']}!")
                    st.rerun()

    # ── TAB 2: THIS WEEK ──────────────────────────────────────────────────────
    with tab_week:
        week_start = get_week_start()
        tasks_week = db.get_tasks_for_week(week_start, username)
        time_week = db.get_time_for_week(week_start, username)

        st.markdown('<div class="section-title">Weekly Pillar Progress</div>', unsafe_allow_html=True)
        cols = st.columns(len(pillars))
        for i, p in enumerate(pillars):
            with cols[i]:
                logged = time_week.get(p["id"], 0)
                budget = p["weekly_budget"]
                pct = min(int(logged / budget * 100), 100) if budget else 0
                ptasks = [t for t in tasks_week if t["pillar_id"] == p["id"]]
                done = sum(1 for t in ptasks if t["is_completed"])
                st.markdown(
                    f'<div style="background:{p["bg"]};border-left:5px solid {p["color"]};'
                    f'border-radius:0 10px 10px 0;padding:16px;margin-bottom:8px;">'
                    f'<div style="font-size:1.4rem;">{p["icon"]}</div>'
                    f'<div style="font-weight:700;font-size:0.9rem;">{p["name"]}</div>'
                    f'<div style="font-size:1.6rem;font-weight:800;color:{p["color"]};">{format_time(logged)}</div>'
                    f'<div style="color:#666;font-size:0.8rem;">of {format_time(budget) if budget else "∞"} target</div>'
                    f'<div style="background:#e9ecef;border-radius:6px;height:8px;margin:8px 0;">'
                    f'<div style="width:{pct}%;background:{p["color"]};height:8px;border-radius:6px;"></div></div>'
                    f'<div style="font-size:0.8rem;color:#555;">{done}/{len(ptasks)} tasks done</div>'
                    f'</div>', unsafe_allow_html=True
                )

        days = [week_start + timedelta(days=i) for i in range(7)]
        st.markdown('<div class="section-title">Tasks This Week</div>', unsafe_allow_html=True)
        for d in days:
            day_tasks = [t for t in tasks_week if t["task_date"] == str(d)]
            is_today = d == today
            label = d.strftime("%A, %b %d") + (" ← Today" if is_today else "")
            done_count = sum(1 for t in day_tasks if t["is_completed"])
            with st.expander(f"{'📍 ' if is_today else ''}{label}  ({done_count}/{len(day_tasks)} done)", expanded=is_today):
                if not day_tasks:
                    st.caption("No tasks planned.")
                for task in day_tasks:
                    p = pillar_map.get(task["pillar_id"], {})
                    style = "line-through;color:#aaa" if task["is_completed"] else "color:#111"
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                        f'<span style="color:{p.get("color","#999")};font-size:1.1rem;">{p.get("icon","📌")}</span>'
                        f'<span style="text-decoration:{style};flex:1;">{task["title"]}</span>'
                        f'<span style="font-size:0.75rem;color:#999;">{format_time(task["est_minutes"])}</span>'
                        f'{"<span style=\'color:green;\'>✓</span>" if task["is_completed"] else ""}'
                        f'</div>', unsafe_allow_html=True
                    )

    # ── TAB 3: DASHBOARD ──────────────────────────────────────────────────────
    with tab_dashboard:
        week_start = get_week_start()
        time_week = db.get_time_for_week(week_start, username)
        stats = db.get_week_completion_stats(week_start, username)
        daily_data = db.get_daily_breakdown_for_week(week_start, username)

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

        with chart_left:
            st.markdown("#### Time by Pillar")
            labels, values, colors = [], [], []
            for p in pillars:
                mins = time_week.get(p["id"], 0)
                if mins > 0:
                    labels.append(f"{p['icon']} {p['name']}")
                    values.append(mins)
                    colors.append(p["color"])
            if values:
                fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.55,
                                       marker_colors=colors, textinfo="label+percent",
                                       hovertemplate="%{label}<br>%{value} min<extra></extra>"))
                fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=0, r=0), height=300,
                                  annotations=[dict(text=f"<b>{format_time(total_logged)}</b>",
                                                    x=0.5, y=0.5, font_size=18, showarrow=False)])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No time logged this week yet.")

        with chart_right:
            st.markdown("#### Daily Breakdown")
            if daily_data:
                df = pd.DataFrame(daily_data)
                df["log_date"] = pd.to_datetime(df["log_date"])
                df["day_label"] = df["log_date"].dt.strftime("%a %d")
                df["pillar_name"] = df["pillar_id"].map(lambda x: pillar_map.get(x, {}).get("name", "?"))
                df["hours"] = df["total_minutes"] / 60
                color_map = {p["name"]: p["color"] for p in pillars}
                fig2 = px.bar(df, x="day_label", y="hours", color="pillar_name",
                              color_discrete_map=color_map,
                              labels={"hours": "Hours", "day_label": "Day", "pillar_name": "Pillar"},
                              barmode="stack", height=300)
                fig2.update_layout(margin=dict(t=20, b=20, l=0, r=0),
                                   legend=dict(orientation="h", yanchor="bottom", y=-0.5))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No time logged this week yet.")

        st.markdown("#### Goal Achievement")
        gcols = st.columns(len(pillars))
        for i, p in enumerate(pillars):
            with gcols[i]:
                logged = time_week.get(p["id"], 0)
                budget = p["weekly_budget"]
                pct = min(int(logged / budget * 100), 100) if budget else 100
                s = stats.get(p["id"], {})
                done = s.get("completed", 0)
                total = s.get("total", 0)
                badge = "🏆" if pct >= 100 else ("✅" if pct >= 80 else ("⚡" if pct >= 50 else "💤"))
                st.markdown(
                    f'<div style="text-align:center;background:{p["bg"]};'
                    f'border:2px solid {p["color"] if pct >= 80 else "#ddd"};'
                    f'border-radius:12px;padding:16px;">'
                    f'<div style="font-size:2rem;">{badge}</div>'
                    f'<div style="font-weight:700;font-size:0.9rem;color:{p["color"]};">{p["icon"]} {p["name"]}</div>'
                    f'<div style="font-size:1.5rem;font-weight:800;">{pct}%</div>'
                    f'<div style="font-size:0.75rem;color:#666;">{format_time(logged)} of {format_time(budget) if budget else "∞"}</div>'
                    f'<div style="font-size:0.75rem;color:#888;margin-top:4px;">{done}/{total} tasks</div>'
                    f'</div>', unsafe_allow_html=True
                )

    # ── TAB 4: ADD TASK ───────────────────────────────────────────────────────
    with tab_add:
        st.markdown("### Add a New Task")
        with st.form("add_task_form", clear_on_submit=True):
            task_title = st.text_input("Task title *", placeholder="e.g. Update resume intro section")
            task_pillar = st.selectbox("Pillar *", options=[p["id"] for p in pillars],
                                       format_func=lambda x: f"{pillar_map[x]['icon']} {pillar_map[x]['name']}")
            task_date = st.date_input("Date *", value=today)
            task_est = st.number_input("Estimated time (minutes)", min_value=5, max_value=480, value=30, step=5)
            task_notes = st.text_area("Notes (optional)", height=80)
            if st.form_submit_button("Add Task ✅", use_container_width=True, type="primary"):
                if task_title.strip():
                    db.add_task(task_title.strip(), task_pillar, task_date, task_est, task_notes, username)
                    st.success(f"Task added to **{pillar_map[task_pillar]['name']}** on {task_date}!")
                else:
                    st.error("Please enter a task title.")

    # ── TAB 5: MY PILLARS ─────────────────────────────────────────────────────
    with tab_pillars:
        show_pillar_manager(pillars)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        show_signup()
    else:
        show_login()
elif not st.session_state.onboarded:
    show_onboarding()
else:
    show_app()
