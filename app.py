"""괌 가족여행 챗봇 — Streamlit UI.

실행:
    streamlit run app.py

(streamlit 미설치 시: pip install streamlit)

구조:
- src/guam_chatbot/agent.py 의 invoke_agent() 호출 (main.py와 동일한 핵심)
- UI 측 메시지 히스토리(st.session_state.messages)와
  agent 측 메모리(MemorySaver, thread_id 기준)를 분리해서 관리.
  thread_id를 세션 내내 동일하게 유지해야 시연 #5 ("그럼 다른 추천도 있어?") 메모리 작동.
- 사이드바에 시연 5개 예시 + 대화 초기화 버튼 제공.
"""
import sys
import uuid
from pathlib import Path

# src/ 폴더를 sys.path에 추가 — main.py와 동일 패턴 (pip install -e . 안 한 환경 대응)
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dotenv import load_dotenv

load_dotenv()  # API 키 환경변수 주입 (agent import 전에 호출 필수)

import re  # noqa: E402

import streamlit as st  # noqa: E402
from guam_chatbot.agent import invoke_agent  # noqa: E402


def _normalize_for_markdown(text: str) -> str:
    """Streamlit이 ~/~~를 strikethrough로 렌더하는 문제 우회. 모든 ~를 -로 치환."""
    return re.sub(r"~+", "-", text)


# ===== 페이지 설정 =====
st.set_page_config(
    page_title="괌 가족여행 챗봇",
    page_icon="🌴",
    layout="centered",
)

st.title("🌴 괌 가족여행 챗봇")
st.caption("가족 단위 여행자를 위한 괌 여행 어시스턴트")


# ===== 세션 상태 초기화 =====
# - messages: 화면에 그릴 대화 히스토리. Streamlit은 매 입력마다 스크립트 전체를
#   재실행하기 때문에 이걸로 누적 표시함.
# - thread_id: agent.py의 MemorySaver가 대화 흐름을 식별하는 키.
#   같은 thread_id로 여러 번 호출해야 단기 메모리 (시연 #5) 작동.
#   초기화 버튼 누르면 새 thread_id 발급 → 메모리 리셋.
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"streamlit-{uuid.uuid4().hex[:8]}"


# ===== 사이드바: 시연 안내 + 대화 초기화 =====
with st.sidebar:
    st.header("사용 안내")
    st.markdown(
        """
**연결된 도구**
- 가이드 (RAG) — 리조트·식당·명소·액티비티
- 날씨 — 괌 5일 예보
- 환율 — USD ↔ KRW (한국은행 ECOS)

**시연 질문 예시**
1. PIC 리조트 어때? 가족이 가도 좋아?
2. 5월 둘째 주 괌 날씨 어때? 우비 챙겨야 해?
3. 100달러면 한국 돈 얼마야?
4. 5인 가족이 5월 둘째 주에 괌 갈 건데, PIC 어때? 날씨도 보고 싶고 100달러 환전 환율도 알려줘
5. (4번 직후) 그럼 다른 추천도 있어?

> 5번은 4번과 같은 세션에서 연속으로 입력해야
> 메모리가 작동합니다 ("그럼"의 맥락 이해).
"""
    )
    st.divider()
    if st.button("🔄 대화 초기화", use_container_width=True):
        # 새 thread_id 발급 → MemorySaver의 이전 흐름과 분리.
        # session_state.messages도 비워서 화면도 깨끗이.
        st.session_state.messages = []
        st.session_state.thread_id = f"streamlit-{uuid.uuid4().hex[:8]}"
        st.rerun()
    st.caption(f"thread_id: `{st.session_state.thread_id}`")


# ===== 기존 대화 표시 =====
# Streamlit이 매 입력마다 이 블록부터 다시 실행 → messages를 순서대로 그려야
# 사용자에게 누적된 대화로 보임.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ===== 사용자 입력 처리 =====
if prompt := st.chat_input("질문을 입력하세요..."):
    # 1) 사용자 메시지: state에 추가 + 화면에 즉시 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Agent 호출 + 답변 표시
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            try:
                result = invoke_agent(
                    prompt,
                    thread_id=st.session_state.thread_id,
                )
                # invoke_agent 반환은 dict, 마지막 메시지가 최종 답변
                messages = result.get("messages", [])
                answer = messages[-1].content if messages else "(답변 없음)"
            except Exception as e:
                # 도구 호출 실패·LLM 타임아웃·환경변수 누락 등.
                # 에러도 대화에 남겨서 디버깅 시 흐름 추적 가능하게.
                answer = f"⚠️ 에러: {type(e).__name__}: {e}"
        answer = _normalize_for_markdown(answer)
        st.markdown(answer)

    # 3) 답변을 state에 저장 → 다음 재실행에서 누적 표시됨
    st.session_state.messages.append({"role": "assistant", "content": answer})
