from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from tools.test_connect import TestConnect
from pydantic import BaseModel

class EmotionRequest(BaseModel):
    text: str

app = FastAPI()

# Add CORS middleware to allow requests from our frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World! We are connected!"}

@app.get("/test")
async def test():
    test_connect = TestConnect()
    return test_connect.test_connect()

@app.post("/analyze_emotion")
async def analyze_emotion(request: EmotionRequest):
    sentiment_analysis = TestConnect()
    return sentiment_analysis.analyze_emotion(request.text)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 