import queue
import threading

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.domain.dtos import UpdateResponseDto
from src.infra.logger import get_logger

logger = get_logger(__name__)

