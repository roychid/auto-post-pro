# run.py
import uvicorn
import os
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from pathlib import Path

# Import the FastAPI app from your main file
# Assuming your FastAPI code is in a file named main.py or similar
from main import app  # Import the app instance

# Add these routes AFTER importing app
@app.get("/")
async def serve_frontend():
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    else:
        return {"error": "Frontend not found"}

# Also serve favicon if you have one
@app.get("/favicon.ico")
async def favicon():
    favicon_path = Path(__file__).parent / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return {"error": "Favicon not found"}

if __name__ == "__main__":
    load_dotenv()  # Load environment variables
    print("🚀 Starting AutoPost Pro Server...")
    print("📊 API Docs available at: http://localhost:8000/docs")
    print("🌐 Web interface: http://localhost:8000")
    uvicorn.run(
        "main:app",  # This tells uvicorn to get 'app' from the 'main' module
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        log_level="info"
    )