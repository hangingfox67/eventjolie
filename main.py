import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mcp.server import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings


DB_PATH = os.environ.get("EVENTJOLIE_DB_PATH", "/srv/eventjolie/data/eventjolie.db")

mcp = MCPServer("EventJolie")

EVENTS_DIR = Path(__file__).parent / "data" / "events"


def get_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            linkedin_url TEXT,
            looking_for_today TEXT NOT NULL,
            can_offer TEXT NOT NULL,
            icebreaker TEXT,
            appearance_description TEXT,
            discoverable INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


@mcp.tool()
def hello_eventjolie(name: str) -> str:
    """Simple connectivity test for EventJolie."""
    return f"Hello {name}, EventJolie MCP is working."


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Dummy sample tool: adds two numbers together."""
    return a + b


@mcp.tool()
def store_event(title: str, name: str, date: str, location: str) -> str:
    """Stores event info (title, name, date, location) as a JSON file under data/events."""
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    event_id = uuid.uuid4().hex[:8]
    event = {
        "id": event_id,
        "title": title,
        "name": name,
        "date": date,
        "location": location,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    file_path = EVENTS_DIR / f"{event_id}.json"
    file_path.write_text(json.dumps(event, indent=2), encoding="utf-8")
    return f"Stored event '{title}' as {file_path.name}"


@mcp.tool()
def start_registration() -> str:
    """
    Start the EventJolie attendee registration interview.

    Call this when the user asks to register, join, check in,
    or add somebody to the current event.
    """
    return """
You are registering a person for EventJolie at today's event.

Conduct a short, friendly interview. Ask ONE question at a time.

Collect:

1. Their full name.
2. Their LinkedIn profile URL, if available.
3. Ask: "What are you looking for at today's event?"
4. Ask: "What can you offer other people here?"
5. Create three short, funny, harmless icebreaker statements based on
   what you learned. Ask them to choose one, or provide their own.
6. Ask them to take/upload a current photo so people can recognize them.
   From the image, produce a short factual appearance description
   focused on clothing and obvious accessories.
   If they do not want a photo, ask what they are wearing.
7. Confirm they are happy to be discoverable by other attendees
   during this event.

Do not ask for information already supplied.

If an answer is vague, ask at most one useful follow-up question.

Keep the process fast: ideally about 60-90 seconds.

When all required information has been collected, call
submit_registration with the completed information.
"""


@mcp.tool()
def submit_registration(
    name: str,
    looking_for_today: str,
    can_offer: str,
    linkedin_url: str = "",
    icebreaker: str = "",
    appearance_description: str = "",
    discoverable: bool = True,
) -> dict:
    """
    Register an attendee after completing the EventJolie interview.
    """

    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()

    existing = None

    if linkedin_url:
        existing = conn.execute(
            "SELECT id FROM attendees WHERE linkedin_url = ?",
            (linkedin_url,),
        ).fetchone()

    if existing:
        attendee_id = existing["id"]

        conn.execute("""
            UPDATE attendees
            SET
                name = ?,
                looking_for_today = ?,
                can_offer = ?,
                icebreaker = ?,
                appearance_description = ?,
                discoverable = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            name,
            looking_for_today,
            can_offer,
            icebreaker,
            appearance_description,
            1 if discoverable else 0,
            now,
            attendee_id,
        ))

        action = "updated"

    else:
        cursor = conn.execute("""
            INSERT INTO attendees (
                name,
                linkedin_url,
                looking_for_today,
                can_offer,
                icebreaker,
                appearance_description,
                discoverable,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            linkedin_url,
            looking_for_today,
            can_offer,
            icebreaker,
            appearance_description,
            1 if discoverable else 0,
            now,
            now,
        ))

        attendee_id = cursor.lastrowid
        action = "created"

    conn.commit()
    conn.close()

    return {
        "success": True,
        "action": action,
        "attendee_id": attendee_id,
        "name": name,
        "message": f"{name} has been successfully registered with EventJolie."
    }


@mcp.tool()
def list_attendees() -> list:
    """List currently discoverable EventJolie attendees."""

    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            name,
            linkedin_url,
            looking_for_today,
            can_offer,
            icebreaker,
            appearance_description
        FROM attendees
        WHERE discoverable = 1
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request):
    return JSONResponse({"status": "ok", "service": "eventjolie"})


security = TransportSecuritySettings(
    allowed_hosts=[
        "eventjolie.com",
        "eventjolie.com:*",
        "www.eventjolie.com",
        "www.eventjolie.com:*",
        # local dev only, remove before deploying
        "127.0.0.1:*",
        "localhost:*",
    ],
    allowed_origins=[
        "https://eventjolie.com",
        "https://www.eventjolie.com",
        # local dev only, remove before deploying
        "http://127.0.0.1:*",
        "http://localhost:*",
    ],
)

app = mcp.streamable_http_app(
    stateless_http=True,
    transport_security=security,
)
