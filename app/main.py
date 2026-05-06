from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.core.exceptions import AppException
from app.storage.minio_client import init_buckets


# ─── Rate Limiter ────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)


def _swagger_ui_html(openapi_url: str) -> str:
        return f"""<!DOCTYPE html>
<html>
    <head>
        <meta charset=\"UTF-8\" />
        <title>Nobal EduConductor API - Swagger UI</title>
        <link rel=\"stylesheet\" type=\"text/css\" href=\"https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css\" />
        <link rel=\"icon\" type=\"image/png\" href=\"https://fastapi.tiangolo.com/img/favicon.png\" />
    </head>
    <body>
        <div id=\"swagger-ui\"></div>
        <script src=\"https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
        <script src=\"https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js\"></script>
        <script>
            window.onload = function () {{
                var ui;

                function normalizePayload(value) {{
                    if (!value) {{
                        return null;
                    }}
                    if (typeof value === "string") {{
                        try {{
                            return JSON.parse(value);
                        }} catch (err) {{
                            return null;
                        }}
                    }}
                    return value;
                }}

                function extractAccessToken(response) {{
                    var payload = null;
                    if (response && response.body) {{
                        payload = normalizePayload(response.body);
                    }} else if (response && response.data) {{
                        payload = normalizePayload(response.data);
                    }} else if (response && response.text) {{
                        payload = normalizePayload(response.text);
                    }}

                    if (payload && payload.data && payload.data.access_token) {{
                        return payload.data.access_token;
                    }}
                    if (payload && payload.access_token) {{
                        return payload.access_token;
                    }}
                    return null;
                }}

                ui = SwaggerUIBundle({{
                    url: \"{openapi_url}\",
                    dom_id: \"#swagger-ui\",
                    presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
                    layout: \"StandaloneLayout\",
                    persistAuthorization: true,
                    responseInterceptor: function (response) {{
                        try {{
                            if (
                                response &&
                                response.url &&
                                response.url.indexOf(\"/api/v1/auth/login\") !== -1
                            ) {{
                                var token = extractAccessToken(response);
                                if (token && ui && ui.preauthorizeApiKey) {{
                                    ui.preauthorizeApiKey(\"BearerAuth\", token);
                                }}
                            }}
                        }} catch (err) {{
                            console.warn(\"Swagger auth auto-set failed\", err);
                        }}
                        return response;
                    }},
                }});

                window.ui = ui;
            }};
        </script>
    </body>
</html>
"""


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise MinIO buckets
    await init_buckets()

    # Startup: create Redis connection pool
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    yield

    # Shutdown
    await app.state.redis.aclose()


# ─── App factory ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    application = FastAPI(
        title="Nobal EduConductor API",
        description="Student Admission Management Platform",
        version="1.0.0",
        docs_url=None,
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    @application.get("/api/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        return HTMLResponse(_swagger_ui_html(application.openapi_url))

    # Rate limiter
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.app_host,
            "http://localhost:3000",
            "http://localhost:8080",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Global exception handler
    @application.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    # Routers — imported here to avoid circular imports
    from app.routers import api_router
    application.include_router(api_router, prefix="/api/v1")

    return application


app = create_app()
