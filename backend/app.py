from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.routers.ai import router

app = FastAPI(title="AZPU AI Assessment")
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def invalid_input(_request: Request, _error: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": "invalid_input", "message": "Check request fields and requirement IDs"})
