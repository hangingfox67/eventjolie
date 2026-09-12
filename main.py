import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from mcp.server import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings
mcp = MCPServer("EventJolie")

EVENTS_DIR = Path(__file__).parent / "data" / "events"


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
