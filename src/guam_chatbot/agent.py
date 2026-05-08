"""괌 가족여행 챗봇 — Agent 정의.

create_react_agent (LangGraph prebuilt) + ReAct 패턴 + MemorySaver.

가드 헬퍼는 config.py에서 import:
- get_llm(): 표준 ChatUpstage 인스턴스 팩토리
- with_guards(): recursion_limit 자동 주입
- TOOL_CALL_LIMIT, RECURSION_LIMIT: 가드 상수

도구 호출 한도(TOOL_CALL_LIMIT)는 자체 구현. 이유:
config.py의 with_call_quota는 강사 패턴 그대로 closure로 counter를 캡슐화하여
매 invoke마다 reset이 불가. 시연 5개를 연속 실행할 때 두 번째 invoke부터
첫 invoke의 카운터가 남아 차단되는 문제 발생. → 모듈 레벨 카운터 +
invoke_agent()에서 명시적 clear 패턴으로 해결.

⚠️ langgraph.prebuilt.create_react_agent는 v1.0+ 이후 deprecation 대상이지만
   여전히 작동. plan Section 4 "create_agent (LangGraph prebuilt)" 표기는 이
   함수를 가리킴 (v1.0의 langchain.agents.create_agent는 v1.1.0에서 다시 제거됨).

SYSTEM_PROMPT 강화 이력:
- 1차 (5/8): 규칙 1번에 "수치+고유명사" 구체화, 규칙 2번 도구 호출 강제, 양식 압축
  → 시연 #4 도구 호출 누락 해결, 가격 환각은 잔존
- 2차 (5/8): 규칙 4번 신설 — "예상·평균·추정·대략 등 우회 표현 금지" + max_tokens 1024→512
  로 환각 면적 축소
"""
from collections import Counter

from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from guam_chatbot.config import TOOL_CALL_LIMIT, get_llm, with_guards
from guam_chatbot.tools.currency import convert_currency
from guam_chatbot.tools.guide import search_guam_guide
from guam_chatbot.tools.weather import get_guam_weather


# 도구 호출 카운터 — 모듈 레벨, invoke_agent()에서 매번 clear.
_call_counter: Counter = Counter()


def _wrap_with_quota(base, limit: int):
    """도구를 호출 카운터 래퍼로 감쌈 (config._wrap_tool과 같은 강사 패턴이나,
    counter를 모듈 레벨로 끌어내 reset 가능).
    """
    name = base.name

    def runner(**kwargs):
        _call_counter[name] += 1
        if _call_counter[name] > limit:
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


# 시스템 프롬프트 (2차 강화) — 우회 표현 금지(규칙 4) + 짧은 답변 유도.
SYSTEM_PROMPT = """당신은 괌 가족여행 어시스턴트입니다. 사용자는 부부 + 어린 아이 1~3명 가족.
**괌**에만 답변하고, 사이판 등 다른 지역 정보는 도구 결과에 섞여 와도 무시하세요.

사용 가능한 도구:
- search_guam_guide: 괌 가이드 정보(리조트·식당·명소·액티비티·교통·안전) RAG 검색
- get_guam_weather: 괌 5일 날씨 예보
- convert_currency: USD/KRW 환율 (환산 계산은 직접 수행)

**절대 규칙 (위반 시 답변 실패)**

1. 수치(가격·금액·거리·기간)와 고유명사(호텔명·식당명·관광지명)는 도구 결과에
   명시된 것만 답변에 포함하세요. 도구 결과에 없는 수치·이름을 만들어내거나
   일반 상식으로 추정하지 마세요.

2. 예산·가격·달러/원화 환산이 들어간 질문은 답변 작성 전에 반드시
   convert_currency를 호출하세요. 사용자에게 "환율 확인이 필요합니다"라고
   되묻지 말고 본인이 직접 호출해 환산까지 마치고 답변하세요.

3. 도구 결과에 정보가 없으면 "해당 정보는 자료에 없습니다"라고 솔직히 답하고
   더 이상 일반론·추측·예시를 덧붙이지 마세요.

4. 도구 결과에 없는 숫자는 어떤 형태로도 답변에 포함하지 마세요.
   "약 50달러", "평균 1박 10~15만원", "예상 비용", "추정 200만원", "대략 4박",
   "보통 50~80달러", "일반적으로 1인당" 같은 모든 추정·근사·일반화 표현 금지.
   가격이나 견적이 필요한데 도구 결과에 없으면 견적표를 작성하지 말고
   "구체 가격은 자료에 없으니 예약 사이트를 직접 확인하세요"로 끝내세요.

**답변 형식**: 친근한 말투, 핵심만 5~8줄로 간결하게. search_guam_guide 결과를
사용한 경우 출처를 한 번 자연스럽게 인용 (예: "[리조트] 퍼시픽 아일랜드 클럽 -
나무위키"). 환산은 도구가 준 환율로 직접 계산해 답변에 포함
(예: "100달러 × 1,450.80 = 145,080원")."""


# 도구 리스트 — 호출 한도 래퍼 적용
_guarded_tools = [
    _wrap_with_quota(t, TOOL_CALL_LIMIT)
    for t in [search_guam_guide, get_guam_weather, convert_currency]
]

# 도구 이름 export (노트북에서 메타 확인용)
TOOL_NAMES = [t.name for t in _guarded_tools]

# Memory + Agent (plan Section 4)
# - MemorySaver: thread_id 기준 단기 메모리 (시연 #5 검증용).
# - create_react_agent: ReAct (Reason + Act), 도구 호출 불필요 시 LLM이 바로 답변.
# - max_tokens=512: 1024 대비 절반으로, 환각 만들 면적 축소 (2차 강화).
_checkpointer = MemorySaver()
agent = create_react_agent(
    model=get_llm(max_tokens=512),
    tools=_guarded_tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=_checkpointer,
)


def invoke_agent(question: str, thread_id: str = "default") -> dict:
    """Agent에 질문을 보내고 결과를 받음 (노트북·CLI에서 한 줄로 호출).

    - 매 호출마다 도구 호출 카운터 reset (TOOL_CALL_LIMIT은 invoke 단위 적용).
    - 같은 thread_id로 연속 호출 시 MemorySaver가 메모리 자동 유지 (시연 #5).
    - recursion_limit은 config.with_guards()로 자동 주입.

    반환:
        {"messages": [HumanMessage, AIMessage, (ToolMessage, AIMessage)*, ...]}
        마지막 메시지(.content)가 최종 답변.
    """
    _call_counter.clear()
    return agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config=with_guards({"configurable": {"thread_id": thread_id}}),
    )
