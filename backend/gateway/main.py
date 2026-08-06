import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Load variables from .env
load_dotenv()

SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")
PORT = int(os.getenv("PORT", 8000))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)

app = FastAPI(
    title=f"{SERVICE_NAME}", description="API Gateway for development to proxy requests to backend services"
)

# Allow CORS for local frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROUTES = {
    # authentication-service (7001)
    "/api/auth": "http://localhost:7001/auth",
    # profile-service (7002)
    "/api/user": "http://localhost:7002/user",
    "/api/admin": "http://localhost:7002/admin",
    "/uploads": "http://localhost:7002/uploads",
    # dashboard-service (7003)
    "/api/dashboard/admin": "http://localhost:7003/dashboard/admin",
    "/api/dashboard/expert": "http://localhost:7003/dashboard/expert",
    "/api/dashboard/customer-admin": "http://localhost:7003/dashboard/customer-admin",
    # framework-category-service (7004)
    "/api/framework-categories": "http://localhost:7004/framework-categories",
    "/api/framework-category-service/framework-access": "http://localhost:7004/framework-access",
    # framework-service (7005)
    "/api/framework": "http://localhost:7005/framework",
    "/api/framework-service/framework-access": "http://localhost:7005/framework-access",
    # deployment-framework-service (7006)
    "/api/assignment-frameworks": "http://localhost:7006/assignment-frameworks",
    "/api/deployment-frameworks": "http://localhost:7006/deployment-frameworks",
    # deployment-document-service (7007)
    "/api/deployment-documents": "http://localhost:7007/deployment-documents",
    # comparison-service (7008)
    "/api/comparison": "http://localhost:7008/api/comparison",
    # compliance-agent-service (7009)
    "/api/compliance-agent": "http://localhost:7009/api/compliance-agent",
    # deployment-gap-service (7010)
    "/api/deployment-gap": "http://localhost:7010/api/deployment-gap",
    # extract-controls-service (7011)
    "/api/extract": "http://localhost:7011/api/extract",
    # load-document-service (7012)
    "/api/load": "http://localhost:7012/api/load",
}

# Sort by length descending to match most specific prefix first
SORTED_ROUTES = sorted(ROUTES.items(), key=lambda x: len(x[0]), reverse=True)

client = httpx.AsyncClient(timeout=30.0)


async def proxy_request(request: Request, target_url: str):
    method = request.method
    headers = dict(request.headers)
    headers.pop("host", None)
    content = await request.body()

    req = client.build_request(method, target_url, headers=headers, content=content)

    try:
        httpx_response = await client.send(req)
        excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        response_headers = {
            k: v for k, v in httpx_response.headers.items() if k.lower() not in excluded_headers
        }

        return Response(
            content=httpx_response.content,
            status_code=httpx_response.status_code,
            headers=response_headers,
        )
    except httpx.RequestError as exc:
        logger.error(f"Error proxying request to {target_url}: {exc}")
        return Response(content="Gateway Timeout", status_code=504)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def gateway(path: str, request: Request):
    if path == "" or path == "/":
        return {
            "success": True,
            "message": "Welcome to the Local API Gateway. Use /api/... to reach backend services.",
        }
    if path == "health" or path == "/health":
        return {"success": True, "service": "api-gateway", "status": "healthy"}

    request_path = "/" + path if not path.startswith("/") else path

    matched_prefix = None
    target_base = None

    for prefix, target in SORTED_ROUTES:
        if request_path.startswith(prefix):
            # Ensure it's a full segment match (e.g., /api/user doesn't match /api/users)
            if len(request_path) == len(prefix) or request_path[len(prefix)] == "/":
                matched_prefix = prefix
                target_base = target
                break

    if not matched_prefix:
        return Response(content="Service Not Found", status_code=404)

    remaining_path = request_path[len(matched_prefix) :]
    target_url = target_base + remaining_path

    if request.url.query:
        target_url += f"?{request.url.query}"

    return await proxy_request(request, target_url)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="localhost", port=PORT, reload=True)
