"""BFHL API - production-ready single-file FastAPI app (minimal comments)"""

import os
import re
import logging
import sys
from datetime import datetime
from typing import Any, List, Tuple

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator

# ---------- Configuration (override via env) ----------
FULL_NAME = os.getenv("FULL_NAME", "Abhishek Patil")
EMAIL = os.getenv("EMAIL", "112216001@ece.iiitp.ac.in")
ROLL_NUMBER = os.getenv("ROLL_NUMBER", "112216001")
DEBUG = os.getenv("DEBUG", "0") == "1"
# -----------------------------------------------------

# ---------- Logging ----------
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bfhl")
# -----------------------------

# ---------- FastAPI app ----------
app = FastAPI(title="BFHL API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------

# ---------- Regex patterns ----------
INTEGER_RE = re.compile(r"^-?\d+$")
ALPHA_RE = re.compile(r"^[A-Za-z]+$")
# ------------------------------------


# ---------- Pydantic models ----------
class DataRequest(BaseModel):
    data: List[Any]

    @validator("data")
    def must_be_list(cls, v):
        if not isinstance(v, list):
            raise ValueError("`data` must be a list")
        return v


class SuccessResponse(BaseModel):
    is_success: bool
    user_id: str
    email: str
    roll_number: str
    odd_numbers: List[str]
    even_numbers: List[str]
    alphabets: List[str]
    special_characters: List[str]
    sum: str
    concat_string: str
# ------------------------------------


# ---------- Utility functions ----------
def generate_user_id(full_name: str) -> str:
    date_suffix = datetime.now().strftime("%d%m%Y")
    name_part = "_".join(full_name.strip().lower().split())
    return f"{name_part}_{date_suffix}"


def classify_item(item: Any) -> Tuple[str, Any, str]:
    s = str(item)
    if INTEGER_RE.match(s):
        return "number", int(s), s
    if ALPHA_RE.match(s):
        return "alphabet", s, s
    return "special", s, s


def build_concat_string(alphabet_items: List[str]) -> str:
    chars: List[str] = []
    for it in reversed(alphabet_items):
        for ch in reversed(it):
            chars.append(ch)
    # alternating caps starting with upper
    return "".join(ch.upper() if i % 2 == 0 else ch.lower() for i, ch in enumerate(chars))
# ---------------------------------------


# ---------- Endpoints ----------
@app.get("/")
async def root():
    return {
        "service": "BFHL API",
        "version": "1.0.0",
        "endpoints": {"POST /bfhl": "process data", "GET /health": "health check", "GET /bfhl": "op code"},
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/bfhl")
async def bfhl_get():
    return {"operation_code": 1}


@app.post("/bfhl", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def bfhl_post(request: DataRequest):
    logger.info("POST /bfhl - received %d items", len(request.data))
    odd_numbers: List[str] = []
    even_numbers: List[str] = []
    alphabets: List[str] = []
    special_characters: List[str] = []
    alphabet_items: List[str] = []
    total_sum = 0

    for item in request.data:
        try:
            category, processed, original = classify_item(item)
            if category == "number":
                total_sum += processed
                (even_numbers if processed % 2 == 0 else odd_numbers).append(original)
            elif category == "alphabet":
                alphabets.append(original.upper())
                alphabet_items.append(original)
            else:
                special_characters.append(original)
        except Exception as e:
            logger.warning("Failed to process item %r: %s", item, e)
            special_characters.append(str(item))

    concat_string = build_concat_string(alphabet_items)
    user_id = generate_user_id(FULL_NAME)

    resp = {
        "is_success": True,
        "user_id": user_id,
        "email": EMAIL,
        "roll_number": ROLL_NUMBER,
        "odd_numbers": odd_numbers,
        "even_numbers": even_numbers,
        "alphabets": alphabets,
        "special_characters": special_characters,
        "sum": str(total_sum),
        "concat_string": concat_string,
    }

    logger.info(
        "POST /bfhl - success (odd=%d even=%d alphabets=%d specials=%d sum=%s)",
        len(odd_numbers),
        len(even_numbers),
        len(alphabets),
        len(special_characters),
        resp["sum"],
    )
    return resp
# ---------------------------------


# ---------- Global exception handler ----------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    content = {"is_success": False, "error": "An unexpected error occurred"}
    if DEBUG:
        content["detail"] = str(exc)
    return JSONResponse(status_code=500, content=content)
# -------------------------------------------


# ---------- Run locally ----------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=DEBUG, log_level="info")
# --------------------------------
