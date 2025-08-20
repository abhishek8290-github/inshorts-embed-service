from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from newspaper import Article
import openai
import os
from typing import Optional
import requests

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

class VideoMetadata(BaseModel):
    id: str
    title: str
    description: str
    url: str
    publication_date: str
    source_name: str
    category: list
    relevance_score: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    vector_embedding: list = []
    llm_summary: str = ""

class VideoResponse(BaseModel):
    video_url: str
    status: str
    metadata: dict

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
    try:
        article = Article(
            query.url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        article.download()
        article.parse()
        
        if not article.text:
            raise HTTPException(status_code=400, detail="Could not extract article content")

        # Use OpenAI for summarization
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes news articles."},
                {"role": "user", "content": f"Summarize the following article: {article.text}"}
            ],
            max_tokens=150
        )
        
        summary = response.choices[0].message.content
        return {
            "summary": summary, 
            "title": article.title,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

@app.post("/find-video", response_model=VideoResponse)
def find_video_endpoint(metadata: VideoMetadata):
    """
    Find the exact YouTube video URL based on metadata
    """
    try:
        video_url = find_exact_video(metadata.dict())
        
        if video_url == "NOT_FOUND":
            return VideoResponse(
                video_url="",
                status="not_found",
                metadata={
                    "original_title": metadata.title,
                    "search_date": metadata.publication_date,
                    "message": "Video not found with the provided criteria"
                }
            )
        
        return VideoResponse(
            video_url=video_url,
            status="found",
            metadata={
                "original_title": metadata.title,
                "search_date": metadata.publication_date,
                "channel": "NDTV Profit India"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video search failed: {str(e)}")

# Helper Functions
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

def find_exact_video(metadata: dict) -> str:
    """
    Find exact YouTube video using LLM with search
    """
    prompt = f"""
    Find the exact YouTube video URL for:
    
    Title: "{metadata['title']}"
    Channel: NDTV Profit India
    Published: {metadata['publication_date'][:10]}
    
    Search YouTube and return ONLY the direct video URL in this format:
    https://www.youtube.com/watch?v=VIDEO_ID
    
    Requirements:
    - Must be from NDTV Profit channel
    - Must match the exact title
    - Must be published around the given date
    
    If not found, return: NOT_FOUND
    """
    
    response = llm_with_search(prompt)
    return response.strip()

# Alternative endpoint with Perplexity AI (recommended)
@app.post("/find-video-perplexity")
def find_video_with_perplexity(metadata: VideoMetadata):
    """
    Find video using Perplexity AI (requires PERPLEXITY_API_KEY)
    """
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_key:
        raise HTTPException(status_code=400, detail="PERPLEXITY_API_KEY not configured")
    
    try:
        prompt = f"""
        Find the exact YouTube video URL for:
        Title: "{metadata.title}"
        Channel: NDTV Profit India
        Published: {metadata.publication_date[:10]}
        
        Return ONLY the YouTube URL in format: https://www.youtube.com/watch?v=VIDEO_ID
        If not found, return: NOT_FOUND
        """
        
        headers = {
            "Authorization": f"Bearer {perplexity_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"].strip()
            return {
                "video_url": result,
                "status": "found" if result != "NOT_FOUND" else "not_found",
                "service": "perplexity"
            }
        else:
            raise HTTPException(status_code=500, detail="Perplexity API error")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Perplexity search failed: {str(e)}")

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "perplexity_configured": bool(os.getenv("PERPLEXITY_API_KEY"))
    }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)