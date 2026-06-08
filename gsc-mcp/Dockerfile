# Google Search Console MCP — corrected, pinned build for Fly.io / Render.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# HTTP transport on 8000 (must match fly.toml internal_port)
EXPOSE 8000
CMD ["fastmcp", "run", "src/mcp_gsc/server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
