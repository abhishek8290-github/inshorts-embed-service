from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from newspaper import Article
import openai
import os
from typing import Optional
import requests
from playwright.sync_api import sync_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="News Summarizer & Video Finder API", version="1.0.0")

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

client = openai.OpenAI()

# Embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Pydantic Models
class Query(BaseModel):
    text: str

class URLQuery(BaseModel):
    url: str


# Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to the News Summarizer & Video Finder API"}

@app.post("/embed")
def embed_text(query: Query):
    try:
        embedding = model.encode(query.text).tolist()
        return {"embedding": embedding, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

@app.post("/summarize")
def summarize_url(query: URLQuery):
    article_text = ""
    article_title = ""

    # Try with newspaper3k first
    try:
        article = Article(
            query.url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        article.download()
        article.parse()
        article_text = article.text
        article_title = article.title
        if not article_text:
            logger.warning(f"Newspaper3k failed to extract content from {query.url}. Trying with Playwright.")
            raise ValueError("Newspaper3k failed") # Force fallback
    except Exception as e:
        logger.error(f"Newspaper3k download/parse failed: {e}")
        # Fallback to Playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(query.url, wait_until="domcontentloaded")
                article_html = page.content()
                browser.close()

                article = Article(query.url)
                article.set_html(article_html)
                article.parse()
                article_text = article.text
                article_title = article.title
                if not article_text:
                    raise HTTPException(status_code=400, detail="Could not extract article content with Playwright")
                logger.info(f"Successfully extracted content with Playwright from {query.url}")
        except Exception as playwright_e:
            logger.error(f"Playwright failed to extract content from {query.url}: {playwright_e}")
            raise HTTPException(status_code=500, detail=f"Failed to extract article content from URL: {playwright_e}")

    try:
        # Use OpenAI for summarization
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes news articles."},
                {"role": "user", "content": f"Summarize the following article: {article_text}"}
            ],
            max_tokens=150
        )
        
        summary = response.choices[0].message.content
        return {
            "summary": summary, 
            "title": article_title,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")



def llm_with_search(prompt: str) -> str:
    """
    LLM with web search capability using OpenAI
    Note: This is a simplified version. In production, you'd want to use 
    a service that actually has web browsing capabilities like Perplexity AI
    """
    try:
        # For now, using standard GPT-4 - you'd replace this with actual web search
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a helpful assistant. When asked to find YouTube videos, 
                    provide realistic YouTube URLs in the format https://www.youtube.com/watch?v=VIDEO_ID.
                    If you cannot find the exact video, respond with 'NOT_FOUND'."""
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Search failed: {str(e)}"


# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
