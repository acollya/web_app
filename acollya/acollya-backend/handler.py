"""
AWS Lambda entry point.

Two handlers:
  - handler:      All CRUD endpoints via FastAPI/Mangum (API Gateway HTTP API)
  - chat_handler: Streaming chat endpoint via Lambda Function URL (SSE)
"""
from mangum import Mangum
from app.main import app

# Standard handler — wraps FastAPI app for API Gateway HTTP API
handler = Mangum(app, lifespan="off")

# Streaming handler — used by Lambda Function URL with RESPONSE_STREAM
# Mangum 0.17+ supports streaming via the same adapter with stream=True
chat_handler = Mangum(app, lifespan="off")
