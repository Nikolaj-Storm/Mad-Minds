FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["fastmcp", "run", "src/gads_mcp/server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
