from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.catalog import router as catalog_router
from app.api.routes.comparisons import router as comparisons_router
from app.api.routes.health import router as health_router
from app.api.routes.preferences import router as preferences_router

app = FastAPI(title="Nutrition Comparer API", version="1.0.0")
app.include_router(health_router)
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(preferences_router, prefix="/api/v1")
app.include_router(comparisons_router, prefix="/api/v1")


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = "not_found" if exc.status_code == 404 else "request_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": str(exc.detail)},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "location": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "The request contains invalid values.",
            "details": details,
        },
    )
