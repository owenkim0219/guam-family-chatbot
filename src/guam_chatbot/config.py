"""
src/guam_chatbot/config.py
프로젝트 전역 설정·가드 상수 + LLM/Splitter 팩토리 + Agent 가드 헬퍼.
"""
from collections import Counter

from langchain_core.tools import StructuredTool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_upstage import ChatUpstage


# ─────────────────────────────────────────────
# 모델 (강의 표준 — S1-1)
# ─────────────────────────────────────────────
MODEL_NAME = "solar-pro"

# ─────────────────────────────────────────────
# LLM 가드 (출처: 01-contract-analyzer-solution.ipynb 8장)
# ─────────────────────────────────────────────
DEFAULT_MAX_TOKENS = 1024   # 출력 토큰 상한 (비용 폭주 방지)
DEFAULT_TIMEOUT = 30        # 응답 대기 시간(초)
DEFAULT_MAX_RETRIES = 2     # 실패 시 재시도 상한

# ─────────────────────────────────────────────
# Splitter 가드 (출처: S2-1, 여행 가이드는 단락 단위)
# ─────────────────────────────────────────────
CHUNK_SIZE = 800            # 청크 1개의 최대 글자 수
CHUNK_OVERLAP = 150         # 인접 청크 간 겹치는 글자 수

# ─────────────────────────────────────────────
# Agent 가드 (출처: 260504_exercise.ipynb 셀 5)
# ─────────────────────────────────────────────
RECURSION_LIMIT = 25        # LangGraph 노드 전이 최대 횟수
TOOL_CALL_LIMIT = 2         # 한 invoke에서 도구당 호출 최대 횟수


# ─────────────────────────────────────────────
# LLM 팩토리
# ─────────────────────────────────────────────
def get_llm(max_tokens: int = DEFAULT_MAX_TOKENS) -> ChatUpstage:
    """프로젝트 표준 가드가 적용된 ChatUpstage 인스턴스를 생성한다.

    Args:
        max_tokens: 응답 토큰 상한. 기본 1024(일반 답변).
                    짧은 Q&A는 512, 긴 리포트는 2048~4096 권장.
    """
    return ChatUpstage(
        model=MODEL_NAME,
        temperature=0,
        max_tokens=max_tokens,
        timeout=DEFAULT_TIMEOUT,
        max_retries=DEFAULT_MAX_RETRIES,
    )


# ─────────────────────────────────────────────
# Splitter 팩토리
# ─────────────────────────────────────────────
def get_splitter() -> RecursiveCharacterTextSplitter:
    """프로젝트 표준 청크 크기로 RecursiveCharacterTextSplitter를 생성한다."""
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )


# ─────────────────────────────────────────────
# Agent 가드 헬퍼
# ─────────────────────────────────────────────
def _wrap_tool(base, counter: Counter, limit: int):
    """기존 도구 하나를 호출 카운터 래퍼로 감싼다.

    Args:
        base: 원래 도구 (StructuredTool).
        counter: 모든 도구가 공유하는 호출 카운터.
        limit: 도구 하나당 허용 최대 호출 횟수.
    """
    name = base.name

    def runner(**kwargs):
        counter[name] += 1
        if counter[name] > limit:
            return (
                f"[quota] '{name}' 도구는 이미 {limit}회 호출되었습니다. "
                "추가 호출이 차단됩니다. 지금까지 수집한 정보로 결론을 내리세요."
            )
        return base.invoke(kwargs)

    return StructuredTool.from_function(
        func=runner,
        name=name,
        description=base.description,
        args_schema=base.args_schema,
    )


def with_call_quota(tools, limit: int = TOOL_CALL_LIMIT):
    """도구 리스트의 각 도구에 호출 한도를 일괄 적용한다."""
    counter = Counter()  # 카운터 1개를 모든 도구가 공유
    return [_wrap_tool(t, counter, limit) for t in tools]


def with_guards(config: dict | None = None) -> dict:
    """invoke/stream 호출에 recursion_limit을 자동 주입한다."""
    base = {"recursion_limit": RECURSION_LIMIT}
    if config:
        return {**base, **config}
    return base