from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import time
import re

from scraper.article_scraper import scrape_article_data
from ai_pipeline.detectors.vlm_detector import analyze_with_vlm

app = FastAPI(title="AI Hybrid Fact-Check API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ArticleRequest(BaseModel):
    url: str

@app.post("/api/v1/analyze-url")
async def analyze_url_endpoint(request: ArticleRequest):
    
    async def event_generator():
        start_time = time.time()
        
        # [단계 1] 스크래핑 시작 알림
        yield f"data: {json.dumps({'status': 'progress', 'step': 'scraping', 'message': '1/2: 뉴스 기사와 이미지를 수집하고 있습니다...'})}\n\n"
        scraped_data = await asyncio.to_thread(scrape_article_data, request.url)

        if "error" in scraped_data:
            msg = f"스크래핑 실패: {scraped_data.get('error')}"
            yield f"data: {json.dumps({'status': 'error', 'message': msg})}\n\n"
            return

        text = scraped_data.get("text", "")
        image_bytes = scraped_data.get("image_bytes")

        if not text or not image_bytes:
            yield f"data: {json.dumps({'status': 'error', 'message': '기사에서 텍스트 또는 이미지를 찾을 수 없습니다.'})}\n\n"
            return

        # [단계 2] LLaVA 통합 분석 시작 알림 (원래대로 2단계 구조 복원)
        yield f"data: {json.dumps({'status': 'progress', 'step': 'analyzing', 'message': '2/2: LLaVA 모델이 이미지/텍스트 조작 여부와 정합성을 통합 판별 중입니다...'})}\n\n"
        
        try:
            vlm_result_str = await asyncio.to_thread(analyze_with_vlm, image_bytes, text)
            
            match = re.search(r'\{.*?\}', vlm_result_str, re.DOTALL)
            if match:
                vlm_result = json.loads(match.group(0))
            else:
                raise ValueError("JSON 형식을 파싱할 수 없습니다.")
                
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'VLM 분석 실패: {str(e)}'})}\n\n"
            return

        # [단계 3] 결과 도출
        end_time = time.time()
        
        final_response = {
            "status": "success",
            "elapsed_time_seconds": round(end_time - start_time, 1),
            "scraped_info": {
                "title": scraped_data.get("title", "제목 없음"),
                "image_url": scraped_data.get("image_url", "")
            },
            "analysis_result": vlm_result # 프론트엔드가 요구하는 구조와 100% 일치
        }
        
        yield f"data: {json.dumps(final_response)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/")
def read_root():
    return {"status": "Fact-Check Backend is running!"}