from fastapi import FastAPI
from db.models import init_db
from mcp_server.router import router
from middlewares.cors_middleware import setup_cors
app = FastAPI(
    title="MCP Monitoring System"
)
setup_cors(app)
init_db()

app.include_router(router)


@app.get("/")
def home():

    return {
        "message": "MCP Monitoring System Running"
    }