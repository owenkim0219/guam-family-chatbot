"""괌 가이드북 RAG 검색 도구 — Agent의 @tool로 등록됨.

옵션 A: 검색 결과만 string으로 반환 (도구 안에서 LLM 호출 X).
Agent의 LLM이 이 결과를 받아 사용자에게 답변을 작성함.
"""
from langchain_core.tools import tool

from guam_chatbot.retriever import retriever


def format_docs(docs):
    """retriever 결과(list[Document]) → Agent에 전달할 문자열.

    [category] title 형태로 라벨링하여 Agent가 출처를 식별·인용할 수 있게 함.
    03_rag_test.ipynb에서 검증된 형식 그대로.
    """
    return "\n\n".join(
        f"[{doc.metadata.get('category', '?')}] {doc.metadata.get('title', '?')}\n"
        f"{doc.page_content}"
        for doc in docs
    )


@tool
def search_guam_guide(query: str) -> str:
    """괌 여행 정보(리조트, 식당, 관광 명소, 액티비티, 교통, 안전 등)를 검색합니다.

    가족 여행자가 물어볼 만한 괌 현지 정보를 답할 때 사용하세요.
    예: 어떤 리조트가 가족에게 좋은지, 추천 식당, 아이들과 가볼 만한 명소,
        공항-시내 이동 방법, 안전 주의사항 등.

    이 도구는 미리 수집한 가이드북 자료(위키백과 ko/en, Wikivoyage, 나무위키,
    PIC 공식 사이트)에서 검색합니다. 실시간 정보(현재 날씨, 환율, 최신 가격)는
    다루지 않으므로 그런 질문에는 다른 도구를 사용하세요.
    """
    docs = retriever.invoke(query)
    return format_docs(docs)