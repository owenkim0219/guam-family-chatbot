# 괌 가족여행 챗봇

LangChain 기반 괌 가족여행 어시스턴트 챗봇입니다. 부부 + 어린 자녀 3명 가족의 괌 4박 5일 여행 계획을 도와주는 LLM 응용 프로젝트입니다.

> **상태**: 개발 중 (발표일 2026-05-11)

## 데모

(Day 3에 GIF/스크린샷 추가 예정)

## 시스템 구조

```
사용자 질문
    ↓
Streamlit UI / CLI (main.py)
    ↓
LangGraph create_agent (Solar-pro + ReAct)
    ↓
도구 4개 (Agent가 자동 선택)
├── search_guam_guide   (RAG, FAISS)
├── get_guam_weather    (OpenWeatherMap)
├── convert_currency    (한국은행 ECOS)
└── search_web          (Tavily, 선택)
```

- **LLM**: Upstage Solar-pro
- **Embedding**: UpstageEmbeddings (solar-embedding-1-large-query)
- **Vector Store**: FAISS (로컬)
- **Memory**: MemorySaver + thread_id
- **Framework**: LangChain 1.x + LangGraph

## 폴더 구조

```
guam-family-chatbot/
├── README.md
├── requirements.txt
├── .env / .env.example
├── .gitignore
├── practice/                  # 탐색 노트북
│   ├── 01_collect_data.ipynb
│   ├── 02_build_index.ipynb
│   ├── 03_rag_test.ipynb
│   ├── 04_tools_test.ipynb
│   └── 05_agent_test.ipynb
├── src/guam_chatbot/
│   ├── __init__.py
│   ├── config.py             # LLM·Splitter·Tool 가드
│   ├── schemas.py            # Pydantic 스키마
│   ├── loader.py
│   ├── retriever.py
│   ├── tools/
│   │   ├── guide.py
│   │   ├── weather.py
│   │   ├── currency.py
│   │   └── web_search.py
│   └── agent.py
├── main.py                   # CLI 진입점
├── app.py                    # Streamlit UI
└── data/                     # gitignore 처리
    ├── raw/
    └── faiss_index/
```

## 실행 방법

### 1. 가상환경 생성 + 활성화

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 의존성 설치

```powershell
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env.example`을 복사해서 `.env` 파일을 만들고 API 키 4개를 채웁니다.

```powershell
Copy-Item .env.example .env
```

### 4. 실행

```powershell
# CLI
python main.py

# Streamlit UI
streamlit run app.py
```

## 사용한 API

| API | 용도 | 발급 가이드 |
|---|---|---|
| Upstage Solar | LLM, Embedding | https://console.upstage.ai/ |
| OpenWeatherMap | 괌 날씨 조회 | https://openweathermap.org/api |
| 한국은행 ECOS | 환율 조회 | https://ecos.bok.or.kr/ |
| Tavily (선택) | 웹 검색 | https://tavily.com/ |

## 데이터 출처

본 프로젝트의 RAG 데이터베이스는 학습 목적의 비상업적 사용을 전제로 다음 출처에서 정제하여 사용합니다.

- 위키백과 "괌" (CC BY-SA)
- Wikivoyage "Guam" (CC BY-SA)
- 외교부 0404.go.kr (공공누리 1유형 자료에 한함)
- 괌정부관광청 visitguamkorea.com (약관 확인 후)

데이터 파일은 `.gitignore`로 처리되어 GitHub 저장소에는 포함되지 않습니다.

## 라이선스

패스트캠퍼스 강의 과제로 작성된 학습용 프로젝트입니다.