from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from agents import function_tool
import os

# ---------------- Configuration ----------------
SERVICE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'service_account.json')
CALENDAR_ID = os.environ.get('CALENDAR_ID')
if not CALENDAR_ID:
    raise ValueError("CALENDAR_ID environment variable must be set")

# ---------------- Google Calendar Setup ----------------
creds = service_account.Credentials.from_service_account_file(
    SERVICE_FILE,
    scopes=['https://www.googleapis.com/auth/calendar']
)
service = build('calendar', 'v3', credentials=creds)

app = Flask(__name__)

# ---------------- MCP Tool Metadata ----------------
TOOLS = [
    {
        "name": "list_events",
        "description": "Fetch upcoming events from Google Calendar",
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "default": 5}
            }
        }
    },
    {
        "name": "create_event",
        "description": "Create a Google Calendar event",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "start": {"type": "string", "description": "ISO 8601 start time"},
                "end": {"type": "string", "description": "ISO 8601 end time"}
            },
            "required": ["name", "start", "end"]
        }
    }
]

# ---------------- Tool Handler Functions ----------------
def list_events(args: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    List events from Google Calendar within a 2-week window (±2 weeks from now).

    Args:
        args: Dictionary containing optional max_results parameter

    Returns:
        List of events with summary, start, and end times
    """
    now = datetime.now(timezone.utc)
    start = (now - timedelta(weeks=2)).isoformat()
    end = (now + timedelta(weeks=2)).isoformat()

    events = service.events().list(
        timeMin=start,
        timeMax=end,
        calendarId=CALENDAR_ID,
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])

    return [{
        "summary": e.get('summary'),
        "start": e['start'].get('dateTime', e['start'].get('date')),
        "end": e["end"].get("dateTime", e["end"].get("date"))
    } for e in events]


def create_event(args: Dict[str, Any]) -> Dict[str, str]:
    """
    Create a new event in Google Calendar.

    Args:
        args: Dictionary containing:
            - name: Event title (required)
            - start: ISO 8601 start time (required)
            - end: ISO 8601 end time (required)
            - description: Event description (optional)

    Returns:
        Dictionary with created event id and summary
    """
    name = args["name"]
    start = args["start"]
    end = args["end"]
    description = args.get("description", "")

    event_body = {
        "summary": name,
        "description": description,
        "start": {"dateTime": start, "timeZone": "UTC"},
        "end": {"dateTime": end, "timeZone": "UTC"}
    }

    event = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event_body
    ).execute()

    return {
        "id": event["id"],
        "summary": event["summary"]
    }


# ---------------- Tool Dispatcher ----------------
TOOL_HANDLERS = {
    "list_events": list_events,
    "create_event": create_event,
}


# ---------------- OpenAI Function Tools ----------------
@function_tool
def list_calendar_events() -> List[Dict[str, str]]:
    """List events from Google Calendar within a 2-week window (±2 weeks from now)."""
    return list_events({})


@function_tool
def create_calendar_event(name: str, start: str, end: str, description: str = "") -> Dict[str, str]:
    """Create a new event in Google Calendar."""
    return create_event({
        "name": name,
        "start": start,
        "end": end,
        "description": description
    })


# OpenAI function schemas for use with OpenAI API
OPENAI_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_calendar_events",
            "description": "List events from Google Calendar within a 2-week window (±2 weeks from now)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a new event in Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The title of the event"
                    },
                    "start": {
                        "type": "string",
                        "description": "ISO 8601 start time (e.g., '2024-01-15T10:00:00Z')"
                    },
                    "end": {
                        "type": "string",
                        "description": "ISO 8601 end time (e.g., '2024-01-15T11:00:00Z')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the event"
                    }
                },
                "required": ["name", "start", "end"]
            }
        }
    }
]

# Function dispatcher for OpenAI function calling
OPENAI_FUNCTION_MAP = {
    "list_calendar_events": list_calendar_events,
    "create_calendar_event": create_calendar_event,
}


# ---------------- MCP Endpoints ----------------
@app.route("/mcp/tools", methods=["GET"])
def mcp_tools():
    """Return available MCP tools metadata."""
    return jsonify({"tools": TOOLS})


@app.route("/mcp/call", methods=["POST"])
def mcp_call():
    """
    Execute an MCP tool call.

    Expects JSON body with:
        - name: Tool name to execute
        - arguments: Dictionary of arguments for the tool
    """
    data = request.json
    name = data.get("name")
    args = data.get("arguments", {})

    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return jsonify({"error": f"Unknown tool: {name}"}), 400

    try:
        result = handler(args)
        return jsonify(result)
    except KeyError as e:
        return jsonify({"error": f"Missing required parameter: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error executing tool: {str(e)}"}), 500


# ---------------- Server Entry Point ----------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)

