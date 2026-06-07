import React, { useState } from 'react';

export default function App() {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  // 💡 본인의 로컬 백엔드 주소 (GCP Cloud Run 배포 후에는 배포된 https://... 주소로 변경하세요)
  const BACKEND_URL = 'https://factcheck-service-121580552392.us-central1.run.app/api/v1/analyze-url'; 

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!url) return;

    setIsLoading(true);
    setProgressMsg('서버와 연결 중입니다...');
    setResult(null);
    setError('');

    try {
      const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) throw new Error('서버 응답 에러가 발생했습니다.');

      // 백엔드의 StreamingResponse(SSE) 데이터를 실시간으로 파싱
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop(); 

        for (const part of parts) {
          if (part.startsWith('data: ')) {
            const dataStr = part.replace('data: ', '');
            const parsedData = JSON.parse(dataStr);

            // 💡 백엔드 진행도에 따라 로딩 창 메시지를 실시간 변경
            if (parsedData.status === 'progress') {
              setProgressMsg(parsedData.message);
            } else if (parsedData.status === 'success') {
              setResult(parsedData);
              setIsLoading(false);
            } else if (parsedData.status === 'error') {
              throw new Error(parsedData.message);
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4 font-sans text-gray-800">
      <div className="max-w-5xl w-full bg-white rounded-2xl shadow-xl p-8">
        <h1 className="text-3xl font-extrabold mb-2 text-center text-blue-700">
          🕵️‍♀️ AI 멀티모달 팩트체커 플랫폼
        </h1>
        <p className="text-gray-500 mb-8 text-center">
          뉴스 기사 URL을 입력하면 크롤링 후 이미지/텍스트 위조와 문맥 정합성을 교차 검증합니다.
        </p>

        {/* 검색 창 */}
        <form onSubmit={handleAnalyze} className="flex flex-col md:flex-row gap-3 mb-8">
          <input
            type="url"
            className="flex-1 border-2 border-gray-200 rounded-xl px-5 py-3 focus:border-blue-500 focus:ring-0 outline-none transition-all"
            placeholder="검증할 뉴스 URL 입력"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isLoading}
            required
          />
          <button
            type="submit"
            disabled={isLoading}
            className="bg-blue-600 text-white font-bold px-8 py-3 rounded-xl hover:bg-blue-700 disabled:bg-blue-300 transition-colors shadow-md min-w-[140px]"
          >
            {isLoading ? '분석 중...' : '검증 시작'}
          </button>
        </form>

        {/* 에러 안내창 */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-r-xl mb-6 font-medium">
            🚨 {error}
          </div>
        )}

        {/* ⏳ 실시간 로딩 창 UI */}
        {isLoading && (
          <div className="bg-blue-50 border border-blue-100 p-8 rounded-xl text-center mb-6">
            <div className="text-5xl mb-4 animate-spin">⏳</div>
            <p className="text-blue-800 font-semibold text-lg animate-pulse">{progressMsg}</p>
          </div>
        )}

        {/* ✅ 종합 분석 결과 카드 */}
        {result && !isLoading && (
          <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-blue-50 p-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="font-bold text-lg text-blue-800">📋 크로스 멀티모달 분석 결과</h2>
              <span className="text-sm bg-white border border-blue-200 px-3 py-1 rounded-full text-blue-600 font-bold">
                총 처리 시간: {result.elapsed_time_seconds}초
              </span>
            </div>
            
            <div className="p-6">
              {/* 스크래핑된 기사 프리뷰 */}
              <div className="flex flex-col md:flex-row gap-6 mb-8 pb-8 border-b border-gray-100">
                <img src={result.scraped_info.image_url} alt="기사 이미지" className="w-full md:w-1/3 h-48 object-cover rounded-xl shadow-sm border" />
                <div className="flex-1">
                  <span className="text-xs font-bold text-gray-500 bg-gray-100 px-2 py-1 rounded mb-2 inline-block">수집된 원본 데이터 정보</span>
                  <h3 className="text-xl font-bold text-gray-800 mt-2">{result.scraped_info.title}</h3>
                </div>
              </div>

              {/* 3개 영역 판정 카드 리스트 (신뢰도 대응 렌더링) */}
              {(() => {
                const res = result.analysis_result;
                
                // 카드 UI 생성 함수
                const renderCard = (title, icon, isThreat, reason, score, threatLabel, safeLabel) => {
                  const isLowConfidence = score < 70; // 70점 미만은 신뢰도 낮음
                  
                  let bgColor, borderColor, textColor, finalLabel;
                  
                  if (isLowConfidence) {
                    bgColor = 'bg-yellow-50';
                    borderColor = 'border-yellow-300';
                    textColor = 'text-yellow-700';
                    finalLabel = '⚠️ 판정 보류 (전문가 검토 권장)';
                  } else if (isThreat) {
                    bgColor = 'bg-red-50';
                    borderColor = 'border-red-300';
                    textColor = 'text-red-600';
                    finalLabel = `🚨 ${threatLabel}`;
                  } else {
                    bgColor = 'bg-green-50';
                    borderColor = 'border-green-300';
                    textColor = 'text-green-600';
                    finalLabel = `✅ ${safeLabel}`;
                  }

                  return (
                    <div className={`p-5 rounded-xl border-2 ${bgColor} ${borderColor} flex flex-col h-full`}>
                      
                      {/* 1. 카드 제목 */}
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-2xl">{icon}</span>
                        <h3 className="font-bold text-gray-800">{title}</h3>
                      </div>
                      
                      {/* 2. 판단 결과 (예: 🚨 AI 생성 의심) */}
                      <p className={`text-xl font-extrabold mb-3 ${textColor}`}>
                        {finalLabel}
                      </p>

                      {/* 3. 💡 신뢰도 점수 (판단 결과와 근거 사이로 이동!) */}
                      <div className="mb-3">
                        <span className="inline-block bg-white px-3 py-1 rounded-md shadow-sm text-xs font-bold text-gray-600 border border-gray-200">
                          🎯 AI 판정 신뢰도: {score}%
                        </span>
                      </div>
                      
                      {/* 4. 판결 근거 */}
                      <p className="text-sm text-gray-700 leading-relaxed bg-white/60 p-3 rounded flex-grow">
                        {reason}
                      </p>

                    </div>
                  );
                };

                return (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {renderCard(
                      "AI 생성 이미지", "🖼️", 
                      res.is_ai_generated_image, res.image_analysis_reason, res.image_confidence_score,
                      "AI 생성 의심", "실제 사진 (정상)"
                    )}
                    {renderCard(
                      "AI 작성 텍스트", "📝", 
                      res.is_ai_generated_text, res.text_analysis_reason, res.text_confidence_score,
                      "AI 작성 의심", "사람이 쓴 글 (정상)"
                    )}
                    {renderCard(
                      "텍스트-이미지 일치", "⚖️", 
                      !res.multimodal_consistency, res.consistency_analysis_reason, res.consistency_confidence_score,
                      "불일치 / 조작 의심", "내용 일치함"
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}