FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
EXPOSE 8000
# SSE transport — matches the Thribee plugin connector, which had to use SSE
# because pre-wired plugin MCPs got stuck "connecting" over streamable HTTP.
CMD ["fastmcp", "run", "src/rentumo_trials_mcp/server.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
