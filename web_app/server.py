from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from application import audit, policy
from application.gateway import ApplicationGateway, build_application_gateway
from web_app import mcp_bridge


ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = Path(__file__).resolve().parent / "static"


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    profile: Literal["support", "commercial"]

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value.strip()


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    profile: Literal["developer"]
    limit: int = Field(default=3, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Search query must not be blank")
        return value.strip()


class DatabaseQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    profile: Literal["support", "commercial"]

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value.strip()


class SchemaRequest(BaseModel):
    profile: Literal["commercial", "developer"]


Profil = Literal["support", "commercial", "developer"]


class McpCatalogueRequest(BaseModel):
    profile: Profil


class McpCallRequest(BaseModel):
    profile: Profil
    tool: str = Field(min_length=1, max_length=64)
    arguments: dict[str, str] = Field(default_factory=dict)

    @field_validator("tool")
    @classmethod
    def tool_appartient_au_catalogue(cls, value: str) -> str:
        """L'allowlist vient de la politique, pas d'une liste recopiée ici."""
        if value not in policy.all_tools():
            raise ValueError("Unknown tool")
        return value

    @field_validator("arguments")
    @classmethod
    def arguments_restent_courts(cls, value: dict[str, str]) -> dict[str, str]:
        if any(len(v) > 2_000 for v in value.values()):
            raise ValueError("Argument too long")
        return value


@lru_cache(maxsize=1)
def get_gateway() -> ApplicationGateway:
    return build_application_gateway(ROOT)


app = FastAPI(title="Sorabel Data Assistant", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


@app.exception_handler(RequestValidationError)
async def invalid_request_handler(_request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "status": "invalid_request",
            "payload": {},
            "message": "Invalid question or profile.",
        },
    )


@app.get("/", response_class=FileResponse)
def browser_application() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


@app.post("/api/answer")
def answer_question(
    request: QuestionRequest,
    gateway: Annotated[ApplicationGateway, Depends(get_gateway)],
) -> dict:
    return gateway.answer_question(request.question, request.profile)


@app.post("/api/search")
def search_documents(
    request: SearchRequest,
    gateway: Annotated[ApplicationGateway, Depends(get_gateway)],
) -> dict:
    return gateway.search_docs(request.query, request.profile, request.limit)


@app.post("/api/database")
def ask_database(
    request: DatabaseQuestionRequest,
    gateway: Annotated[ApplicationGateway, Depends(get_gateway)],
) -> dict:
    return gateway.ask_database(request.question, request.profile)


@app.post("/api/schema")
def get_schema(
    request: SchemaRequest,
    gateway: Annotated[ApplicationGateway, Depends(get_gateway)],
) -> dict:
    return gateway.get_schema(request.profile)


@app.post("/api/mcp/catalogue")
async def mcp_catalogue(request: McpCatalogueRequest) -> dict:
    """`tools/list` réel, sur un serveur MCP lancé au profil demandé."""
    return await mcp_bridge.catalogue(request.profile)


@app.post("/api/mcp/call")
async def mcp_call(request: McpCallRequest) -> dict:
    """`tools/call` réel. L'enveloppe renvoyée est celle du serveur MCP."""
    return await mcp_bridge.appeler(request.profile, request.tool, request.arguments)


@app.get("/api/mcp/journal")
def mcp_journal(limit: int = 12) -> dict:
    """Les dernières lignes du journal partagé — canal `web` et canal `mcp`."""
    entrees = audit.read_entries()[-max(1, min(limit, 100)):]
    return {"status": "ok", "payload": {"entrees": entrees, "total": len(entrees)}, "message": ""}
