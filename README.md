# Inshorts Embed Service

A small FastAPI service that provides two primary capabilities:
- Generate sentence embeddings for text using SentenceTransformers.
- Summarize news articles (by URL) using OpenAI and an extraction fallback with Playwright when `newspaper3k` fails.

This repository contains a minimal API that demonstrates extracting article content, generating embeddings, and producing summaries via OpenAI.

---

## Features

- /embed — create an embedding vector for a given text using `sentence-transformers` (`all-MiniLM-L6-v2`).
- /summarize — fetch and extract article text from a URL (tries `newspaper3k` first, falls back to Playwright), then summarize using OpenAI chat models.
- /health — basic health check endpoint.

---

## Requirements

- Python 3.8+
- An OpenAI API key (set in environment as `OPENAI_API_KEY`)
- The Python dependencies in `requirements.txt`
- Playwright browsers installed if you expect the Playwright fallback to be used

Dependencies (as listed in `requirements.txt`):
- fastapi
- pydantic
- sentence-transformers
- newspaper3k
- openai
- python-dotenv
- requests
- uvicorn
- playwright

Note: `sentence-transformers` will download the model (`all-MiniLM-L6-v2`) on first use which requires internet and some disk space. `newspaper3k` has additional system dependencies for some platforms.

---

## Installation

1. Clone the repo
   git clone https://github.com/abhishek8290-github/inshorts-embed-service.git
   cd inshorts-embed-service

2. Create a virtual environment (recommended)
   python -m venv .venv
   source .venv/bin/activate

3. Install Python dependencies
   pip install -r requirements.txt

4. (Optional) Use a .env file to store environment variables and a tool like `python-dotenv` if you prefer local .env loading.

5. Install Playwright browsers (required if Playwright fallback will be used)
   playwright install

---

## Environment Variables

- OPENAI_API_KEY (required) — OpenAI API key used for summarization and LLM calls.

The service will raise an error on startup if `OPENAI_API_KEY` is not set.

---

## Running the Service (Development)

Run the API with Uvicorn:

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Or simply:

python main.py

The API will be available at: http://0.0.0.0:8000

API docs (Swagger UI): http://0.0.0.0:8000/docs

---

## API Endpoints

1. GET /

- Description: Basic welcome message
- Response: { "message": "Welcome to the News Summarizer & Video Finder API" }

2. POST /embed

- Description: Generate an embedding for provided text.
- Request body (JSON):
  {
    "text": "Your text to embed"
  }
- Response:
  {
    "embedding": [ ...floating point numbers... ],
    "status": "success"
  }

Curl example:

curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a short test sentence."}'

3. POST /summarize

- Description: Extract article content from a URL, then summarize via OpenAI. Uses `newspaper3k` first, and falls back to Playwright extraction if needed.
- Request body (JSON):
  {
    "url": "https://some-news-site/article"
  }
- Response:
  {
    "summary": "Summary text...",
    "title": "Article title",
    "status": "success"
  }

Curl example:

curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/some-article"}'

4. GET /health

- Description: Basic health check that also indicates if OPENAI_API_KEY is configured.
- Response:
  {
    "status": "healthy",
    "openai_configured": true|false
  }

---

## Notes & Implementation Details

- The app uses `SentenceTransformer('all-MiniLM-L6-v2')` to produce embeddings.
- Summarization is implemented by sending the article text to OpenAI chat completions (configured in the code). Be mindful of token usage and cost.
- On extraction:
  - The service first attempts to use `newspaper3k`.
  - If extraction fails or returns empty, it falls back to Playwright to retrieve the page HTML and re-run `newspaper3k` on that HTML.
  - Playwright must have browser binaries installed (run `playwright install`).
- The code raises a ValueError during startup if `OPENAI_API_KEY` is missing; ensure it is set before starting.

---

## Docker

A Dockerfile is included in the repository. Typical build/run steps:

docker build -t inshorts-embed-service .
docker run -e OPENAI_API_KEY=sk-... -p 8000:8000 inshorts-embed-service

Notes:
- If you plan to rely on Playwright inside Docker, ensure the Docker image includes Playwright browsers (the provided Dockerfile may already include relevant steps — review and adjust as needed).

---

## Security & Cost Considerations

- The app calls OpenAI APIs — monitor your API usage and enforce quotas or authentication as necessary for production.
- Never commit your `OPENAI_API_KEY` into git or public places.

---

## Development & Testing

- To run locally, follow the installation and run steps above.
- For testing summarization on many URLs, consider batching and throttling requests to avoid hitting OpenAI rate limits or spending excessive credits.
- Additional improvements:
  - Add request size limits and validation
  - Stream summaries if you need to support very large inputs
  - Add caching for embeddings and summaries to reduce repeated API calls
  - Add authentication for endpoints

---

## Contributing

1. Fork the repo
2. Create a branch for your feature
3. Open a pull request with a clear description of changes

---

## License

Add an appropriate license file (e.g., MIT) if you want to make licensing explicit.

---

## Contact / Author

Repository: https://github.com/abhishek8290-github/inshorts-embed-service
