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

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((336, 336))
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        optimized_image_bytes = buffered.getvalue()
    except Exception as e:
        print(f"이미지 최적화 실패: {e}")
        optimized_image_bytes = image_bytes 

    base64_image = base64.b64encode(optimized_image_bytes).decode('utf-8')
    image_data_uri = f"data:image/jpeg;base64,{base64_image}"

    prompt = f"""
    You are an expert AI fact-checker. 
    Analyze the image and the news article text below.
    
    [News Article Text]
    {article_text[:500]}
    
    Task 1: Determine if the image is AI-generated.
    Task 2: Determine if the text is likely AI-generated (e.g., written by ChatGPT, Claude).
    Task 3: Does the image match the claims in the text?
    
    Respond STRICTLY with this JSON format only:
    {{
        "is_ai_generated_image": true,
        "image_analysis_reason": "reason",
        "is_ai_generated_text": true,         
        "text_analysis_reason": "reason",     
        "multimodal_consistency": true,
        "consistency_analysis_reason": "reason"
    }}
    """

    # 3. 모델 추론
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
        max_tokens=768,
        temperature=0.1
    )

    return response["choices"][0]["message"]["content"]