import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from agents import Agent, Runner
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from yoga.corepower_tools import get_yoga_reservations, get_yoga_classes, make_yoga_reservation, reload_cognito_jwt, delete_yoga_reservation
from gcalendar.gcalender_mcp_server import list_calendar_events, create_calendar_event, delete_calendar_event
from utils import send_email

load_dotenv()


# Create the yoga scheduling agent
yoga_agent = Agent(
    name="Assistant",
    instructions="You're speaking to a human, so be polite and concise. Speak in english.",
    model="gpt-5-mini",
    tools=[get_yoga_classes, get_yoga_reservations, make_yoga_reservation, delete_yoga_reservation, list_calendar_events, create_calendar_event, delete_calendar_event],
)


async def schedule_yoga_class():
    """
    Schedule yoga classes for the week based on calendar availability and preferences.

    This function:
    - Reloads the CorePower JWT token
    - Schedules yoga classes for the next 7 days
    - Ensures no consecutive days of yoga
    - Ensures 30 minutes of free time after each class
    - Avoids overlaps with other calendar events
    - Sends a confirmation email with the scheduled classes
    """
    # Reload JWT token
    reload_cognito_jwt()

    # Time range to schedule
    schedule_start = datetime.now(timezone.utc) + timedelta(hours=5)
    schedule_end = schedule_start + timedelta(days=7)

    prompt = f"""
    You are a calendar scheduling assistant. Follow the steps exactly and do not skip any step.

    Goal:
    Schedule Yoga classes over the date range {schedule_start.isoformat()} to {schedule_end.isoformat()}
    such that:
    - The user never attends Yoga twice within 24 hours.
    - Each scheduled Yoga class has at least 30 minutes of free time immediately after it ends and 15 minutes before it begins.
    - No scheduled event overlaps with any other calendar event.

    Step 0 — Clean overlapping events:
    If any Yoga classes scheduled between {schedule_start.isoformat()} and {schedule_end.isoformat()} overlap with any other calendar event 
    Delete those classes from the reservations and calendar
    with delete_yoga_reservation and delete_calendar_event tools. Remember that the calendar events and reservations
    should always be in sync.

    Step 1 — Fetch existing Yoga events:
    Fetch all remaining Yoga events on the user's calendar between
    {schedule_start.isoformat()} and {schedule_end.isoformat()}.
    These events count toward spacing constraints.

    Step 2 — Fetch candidate classes:
    Fetch all available Yoga classes between {schedule_start.isoformat()} and {schedule_end.isoformat()}.

    Step 3 — Filter candidates:
    From the fetched classes, keep only those that:
    - Do not overlap with any remaining calendar events.
    - Ensure nothing is on the calendar from 15 min before the class to 30 min after the class ends. 

    Step 4 — Construct a weekly schedule:
    Consider already existing classes as well to construct a class
    - Schedule 2 Yoga Sculpt Classes during the week (monday - Friday) at least one day apart.
    - Prefer classes with Julia, Sophie, Alisa, Brent, Isabel, Courtney!
    - Schedule a third class if it is CSX - CorePower Strength X
    
    Step 5 — Validation:
    If it is impossible to construct a schedule that satisfies all constraints:
    - Do NOT schedule anything.
    - Respond with a confirmation that no valid schedule exists.

    Step 6 — Scheduling:
    Schedule all new Yoga classes into the user's calendar with create_calendar_event and make all the reservations with tool call to make_yoga_reservation

    Output rules:
    - Only respond with tool calls and confirmation message with all the yoga classes scheduled from {schedule_start.isoformat()} to {schedule_end.isoformat()}.
    - Respond with times in PST colloquially.
    - Do not invent classes or events.
    """

    result = await Runner.run(
        yoga_agent,
        input=prompt
    )
    print(result.final_output)

    sender_email = os.environ.get("SENDER_EMAIL")
    if not sender_email:
        raise ValueError("SENDER_EMAIL environment variable is not set")

    await send_email(
        subject="Your Weekly CorePower Reservations",
        body=f"Hello! Here are your workouts for the week\n\n{result.final_output}",
        sender_email=sender_email,
        receiver_email=sender_email
    )


if __name__ == "__main__":
    asyncio.run(schedule_yoga_class())
