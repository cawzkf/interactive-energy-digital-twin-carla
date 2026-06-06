
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

FROM base AS test
COPY pyproject.toml ./
COPY src ./src
COPY tests ./tests
COPY config ./config
RUN python -m pytest -q

FROM base AS runtime
COPY src ./src
COPY config/.env.dev config/.env.example ./config/
ENV APP_ENV=prod
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
