from datetime import date, timedelta

# Azure App Registration
CLIENT_ID = "b5242bd4-9a4a-4012-b6d1-9efc03dd5f90"
TENANT_ID = "consumers"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read", "Calendars.Read"]

# Work hours (24h format)
WORK_START_HOUR = 8
WORK_END_HOUR = 18

# 4 Pillars definition
PILLARS = {
    1: {
        "name": "Microsoft Work",
        "short": "MS Work",
        "color": "#0078D4",
        "bg": "#EBF3FB",
        "icon": "💼",
        "daily_budget_min": None,       # fills remaining time
        "weekly_budget_min": None,
        "description": "Daily job, meetings, decks, agendas"
    },
    2: {
        "name": "Career External",
        "short": "Career Ext",
        "color": "#FF6B35",
        "bg": "#FFF0EB",
        "icon": "🚀",
        "daily_budget_min": 60,         # 1 hour/day
        "weekly_budget_min": 300,       # 5 days × 60 min
        "description": "Resume, LinkedIn, PM upskilling, audio/speech learning, side business"
    },
    3: {
        "name": "Career Internal (AI)",
        "short": "AI Growth",
        "color": "#00A86B",
        "bg": "#EBFAF3",
        "icon": "🤖",
        "daily_budget_min": 36,         # ~3 hrs / 5 days
        "weekly_budget_min": 180,       # max 3 hours/week
        "description": "AI tools, learning sessions, showing AI to leadership"
    },
    4: {
        "name": "Personal To-Do's",
        "short": "Personal",
        "color": "#9B59B6",
        "bg": "#F5EEF8",
        "icon": "🏠",
        "daily_budget_min": 30,         # 30 min/day
        "weekly_budget_min": 150,       # 5 days × 30 min
        "description": "Personal errands, health, life admin"
    }
}

# Suggested default tasks per pillar (user can add their own)
DEFAULT_TASKS = {
    1: [
        "Review and respond to emails",
        "Prepare meeting agenda",
        "Update project status deck",
        "Sync with team",
        "Review PRD / specs",
    ],
    2: [
        "Update resume section",
        "Send LinkedIn connection requests (5)",
        "Read PM article / book chapter",
        "Learn about audio/speech tech",
        "Work on side business idea",
        "Build something with Claude AI",
    ],
    3: [
        "Explore a new AI tool",
        "Attend AI learning session",
        "Apply AI to a work task",
        "Demo AI capability to team",
        "Complete AI course module",
    ],
    4: [
        "Personal admin / errands",
        "Health / wellness",
        "Personal finance review",
        "Family / social",
        "Home tasks",
    ]
}


def get_week_start(for_date=None):
    """Return Monday of the current week."""
    d = for_date or date.today()
    return d - timedelta(days=d.weekday())


def get_week_end(for_date=None):
    """Return Friday of the current week."""
    return get_week_start(for_date) + timedelta(days=4)
