from mcp.server import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings
mcp = MCPServer("EventJolie")


@mcp.tool()
def hello_eventjolie(name: str) -> str:
    """Simple connectivity test for EventJolie."""
    return f"Hello {name}, EventJolie MCP is working."


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Dummy sample tool: adds two numbers together."""
    return a + b


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
