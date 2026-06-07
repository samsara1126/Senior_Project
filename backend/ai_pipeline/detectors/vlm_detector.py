import os
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava16ChatHandler 
import base64
from PIL import Image
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = "/app/models/models"  

MODEL_PATH = os.path.join(MODEL_DIR, "llava-v1.6-vicuna-7b.Q4_K_M.gguf")
PROJ_PATH = os.path.join(MODEL_DIR, "mmproj-model-f16.gguf") #
chat_handler = Llava16ChatHandler(clip_model_path=PROJ_PATH)


llm = Llama(
    model_path=MODEL_PATH,
    chat_handler=chat_handler,
    n_ctx=2048,      
    n_gpu_layers=-1, 
    n_threads=8
)

def analyze_with_vlm(image_bytes: bytes, article_text: str):
    # 1. 해상도 다이어트 (추론 속도 최적화)
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((336, 336))
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        optimized_image_bytes = buffered.getvalue()
    except Exception as e:
        optimized_image_bytes = image_bytes 

    base64_image = base64.b64encode(optimized_image_bytes).decode('utf-8')
    image_data_uri = f"data:image/jpeg;base64,{base64_image}"

    # 2. 🌟 LLaVA 통합 3대 임무 부여 프롬프트 (신뢰도 점수 포맷 완벽 매핑)
    prompt = f"""
    You are an expert AI fact-checker. 
    Analyze the image and the news article text below.
    
    [News Article Text]
    {article_text[:500]}
    
    Think step-by-step before making your final judgment.
    Task 1: Determine if the image is AI-generated and provide a confidence score (0-100).
    
    Task 2: Determine if the text is AI-generated. 
    CRITICAL INSTRUCTION FOR TASK 2: Assume the text is written by a HUMAN journalist by default. Well-structured, formal, or objective writing is standard for news articles and does NOT necessarily mean it is AI-generated. Give the text the benefit of the doubt. ONLY flag as AI-generated if there are undeniable, stereotypical machine artifacts. If you are not 100% certain, classify it as HUMAN ("is_ai_generated_text": false) and keep the confidence score low.
    
    Task 3: Does the image logically match the claims in the text? Provide a confidence score (0-100).
    
    CRITICAL INSTRUCTIONS:
    - You MUST write the "reason" fields in highly detailed ENGLISH, regardless of the language of the article text.
    - Provide specific visual artifacts and contextual evidence in your reasoning. Do not write short generic sentences.
    
    Respond STRICTLY with this JSON format only:
    {{
        "image_analysis_reason": "Step-by-step reasoning for the image in Korean...",
        "is_ai_generated_image": false,
        "image_confidence_score": 80,
        
        "text_analysis_reason": "Step-by-step reasoning for the text in Korean...",
        "is_ai_generated_text": false,
        "text_confidence_score": 50,
        
        "consistency_analysis_reason": "Step-by-step reasoning for multimodal consistency in Korean...",
        "multimodal_consistency": true,
        "consistency_confidence_score": 90
    }}
    """

    response = llm.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                    {"type": "text", "text": prompt}
                ]
            }
        ],
        max_tokens=850,
        temperature=0.0 # 일관된 팩트체크 결과를 위해 0으로 고정
    )

    return response["choices"][0]["message"]["content"]