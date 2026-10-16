
import hashlib
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

EMAIL = "24f2008072@ds.study.iitm.ac.in"
PROTOCOL_VERSION = "2025-03-26"


def rpc_result(request_id, result):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None,
             "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )

    method = body.get("method")
    request_id = body.get("id")
    params = body.get("params") or {}

    # MCP notifications do not receive JSON-RPC responses.
    if method == "notifications/initialized":
        return Response(status_code=202)

    if method == "initialize":
        version = params.get("protocolVersion", PROTOCOL_VERSION)
        return JSONResponse(rpc_result(request_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "exam-challenge-server",
                "version": "1.0.0",
            },
        }))

    if method == "ping":
        return JSONResponse(rpc_result(request_id, {}))

    if method == "tools/list":
        return JSONResponse(rpc_result(request_id, {
            "tools": [{
                "name": "solve_challenge",
                "description": "Solve the current exam challenge from HTTP headers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            }]
        }))

    if method == "tools/call":
        name = params.get("name")

        if name != "solve_challenge":
            return JSONResponse(rpc_result(request_id, {
                "content": [{"type": "text", "text": "Unknown tool"}],
                "isError": True,
            }))

        # Read the fresh challenge from THIS HTTP request's headers.
        challenge = request.headers.get("x-exam-challenge")

        if challenge is None:
            return JSONResponse(rpc_result(request_id, {
                "content": [{
                    "type": "text",
                    "text": "Missing X-Exam-Challenge header",
                }],
                "isError": True,
            }))

        normalized_email = EMAIL.strip().lower()
        message = f"{challenge}:{normalized_email}"
        answer = hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]

        return JSONResponse(rpc_result(request_id, {
        "content": [{"type": "text", "text": answer}],
        }))

    if request_id is None:
        return Response(status_code=202)

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "Method not found"},
    }, status_code=200)


@app.get("/")
async def health():
    return {"status": "ok", "endpoint": "/mcp"}
        