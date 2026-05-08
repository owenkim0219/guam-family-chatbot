"""괌 가족여행 챗봇 — CLI 진입점 (OT 보강 D).

실행:
    python main.py

사용법:
- 질문 입력 → Enter
- 같은 세션 안에서는 메모리 자동 유지 (예: "PIC 리조트 추천" → "그럼 더 저렴한 곳은?")
- 종료: 'exit' / 'quit' / '종료' 입력 또는 Ctrl+C

구조:
- src/guam_chatbot/agent.py 의 invoke_agent(question, thread_id) 호출
- 반환 dict의 마지막 메시지(.content)가 최종 답변
- thread_id를 세션 내내 동일하게 유지해 MemorySaver 단기 메모리 활용 (시연 #5 패턴)
"""
import sys
from pathlib import Path

# src/ 폴더를 sys.path에 추가 — pip install -e . 안 한 환경에서도 동작.
# 노트북에서 `from guam_chatbot.xxx import ...` 패턴을 그대로 쓰기 위함.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dotenv import load_dotenv

# API 키(UPSTAGE/OPENWEATHER/ECOS) 환경변수 주입.
# agent.py가 import될 때 ChatUpstage 인스턴스가 만들어지므로
# load_dotenv()는 agent import보다 먼저 호출되어야 함.
load_dotenv()

from guam_chatbot.agent import invoke_agent  # noqa: E402


def _extract_answer(result: dict) -> str:
    """invoke_agent 반환 dict에서 최종 답변 텍스트 추출.

    create_react_agent의 invoke 결과 구조:
        {"messages": [HumanMessage, AIMessage(tool_calls?), ToolMessage, ..., AIMessage(final)]}
    마지막 메시지의 .content가 최종 답변 (도구 호출 사이클 종료 후 LLM의 요약).
    """
    messages = result.get("messages", [])
    if not messages:
        return "(답변 없음)"
    return messages[-1].content


def main() -> None:
    print("=" * 50)
    print("괌 가족여행 챗봇")
    print("=" * 50)
    print("질문을 입력하세요. 종료: 'exit' / 'quit' / '종료' / Ctrl+C")
    print()

    # 세션 내 메모리 유지를 위한 단일 thread_id.
    # 같은 세션의 모든 질문이 한 대화 흐름으로 누적됨 (시연 #5 회귀 검증 가능).
    thread_id = "cli-session"

    while True:
        try:
            query = input("질문 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n종료합니다.")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit", "종료"):
            print("종료합니다.")
            break

        try:
            print("(생각 중...)")
            result = invoke_agent(query, thread_id=thread_id)
            answer = _extract_answer(result)
            print(f"\n답변: {answer}\n")
            print("-" * 50)
        except Exception as e:
            # 도구 호출 실패·LLM 타임아웃·환경변수 누락 등을 사용자에게 보여주되
            # 루프는 끊지 않음. 한 번의 실패가 세션 전체를 망치지 않도록.
            print(f"\n[에러] {type(e).__name__}: {e}\n")


if __name__ == "__main__":
    main()
