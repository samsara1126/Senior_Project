# 1. NVIDIA CUDA 베이스 이미지 (Cloud Run L4 GPU 호환)
FROM nvidia/cuda:12.2.2-devel-ubuntu22.04

# 대화형 프롬프트 방지
ENV DEBIAN_FRONTEND=noninteractive

# 2. Python 3 및 필수 시스템 도구 설치
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# python 명령어를 python3로 연결
RUN ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /app

# 3. 요구사항 파일 복사
COPY requirements.txt .

# 4. 🔥 llama-cpp-python을 GPU(CUDA) 모드로 빌드하도록 환경변수 설정 후 설치
ENV CMAKE_ARGS="-DGGML_CUDA=on"
ENV FORCE_CMAKE=1

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. 소스 코드 복사 (models 폴더는 .gcloudignore로 제외됨)
COPY . .

# 5. 서버 포트 8080 노출
EXPOSE 8080

# 6. Uvicorn 서버 실행
# Cloud Run 환경은 기본적으로 8080 포트를 사용함
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]