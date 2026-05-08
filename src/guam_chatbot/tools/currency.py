"""괌 가족 여행자용 USD/KRW 환율 정보 도구 — 한국은행 ECOS Open API.

옵션 A 패턴: 도구는 raw 환율값만 string으로 반환. "100달러 = 한국 돈 얼마?"
같은 환산 계산은 Agent의 LLM이 환율값을 받아 직접 수행함.

도구 이름은 plan Section 4의 'convert_currency'를 그대로 사용. 옵션 A 결정
이후 실제 동작은 환산이 아닌 환율 조회이지만, plan 일관성 우선. docstring에서
호출자에게 환산 책임을 명시함.
"""

import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

# .env에서 환경 변수 로드 (이미 로드되었어도 멱등적이라 안전)
load_dotenv()

# 한국은행 ECOS Open API (plan Section 5)
# 통계표 731Y001 — 주요국 통화의 대원화환율 / 주기 D — 일별
# 항목 0000001 — 미국 달러
# 정상 응답: {"StatisticSearch": {"list_total_count": N,
#            "row": [{"TIME": "YYYYMMDD", "DATA_VALUE": "1378.5", ...}, ...]}}
# 에러 응답: {"RESULT": {"CODE": "INFO-100|...", "MESSAGE": "..."}}
API_URL_TEMPLATE = (
    "https://ecos.bok.or.kr/api/StatisticSearch/"
    "{key}/json/kr/{page_start}/{page_end}/731Y001/D/{from_date}/{to_date}/0000001"
)

# 한국어 요일 매핑 (locale 의존성 회피, weather.py와 동일 스타일)
WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]

# 환율은 영업일 기준 (주말·공휴일 결측). 데이터가 1~2일 지연 가능.
# → 최근 14일 검색하면 평일 약 10건 확보, 그중 최근 5영업일을 사용자에게 표시.
LOOKBACK_DAYS = 14
DISPLAY_COUNT = 5


@tool
def convert_currency(query: str) -> str:
    """미국 달러(USD)와 한국 원화(KRW) 사이 환율을 가져옵니다.

    사용자가 환율, 미국 달러, 원화 환산을 물어볼 때 사용하세요.
    예: 100달러면 한국 돈 얼마?, 환율 알려줘, 1달러 몇 원?

    이 도구는 한국은행이 고시하는 매매기준율을 반환합니다 (영업일 기준,
    주말·공휴일 데이터 없음). 환율값만 제공하므로 100 × 환율 같은 환산
    계산은 호출자가 직접 수행해야 합니다. 다른 통화 쌍(JPY, EUR 등)은
    지원하지 않습니다.
    """
    # query는 미사용 (weather.py와 동일 패턴). 향후 시점·통화쌍 파싱으로 확장 가능.

    api_key = os.getenv("ECOS_API_KEY")
    if not api_key:
        return (
            "환율 정보 조회 실패: ECOS_API_KEY가 설정되지 않았습니다. "
            ".env 파일을 확인하세요. 다른 방법을 시도해주세요."
        )

    today = datetime.now()
    from_date = (today - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    to_date = today.strftime("%Y%m%d")

    url = API_URL_TEMPLATE.format(
        key=api_key,
        page_start=1,
        page_end=LOOKBACK_DAYS + 1,  # 영업일 5+ 보장 위해 여유 페이지
        from_date=from_date,
        to_date=to_date,
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as e:
        return (
            f"환율 정보 조회 실패: HTTP {response.status_code} ({e}). "
            "다른 방법을 시도해주세요."
        )
    except requests.exceptions.RequestException as e:
        return f"환율 정보 조회 실패: {e}. 다른 방법을 시도해주세요."

    # ECOS는 인증키·코드 오류도 HTTP 200으로 반환하므로 응답 본문에서 분기.
    if "RESULT" in data:
        code = data["RESULT"].get("CODE", "?")
        msg = data["RESULT"].get("MESSAGE", "?")
        return (
            f"환율 정보 조회 실패: ECOS API 에러 ({code}: {msg}). "
            "API 키 또는 통계 코드 확인 필요. 다른 방법을 시도해주세요."
        )

    try:
        rows = data["StatisticSearch"]["row"]
    except (KeyError, TypeError) as e:
        return f"환율 데이터 형식 오류: {e}. 다른 방법을 시도해주세요."

    if not rows:
        return (
            f"환율 정보 조회 실패: 최근 {LOOKBACK_DAYS}일간 영업일 데이터 없음. "
            "다른 방법을 시도해주세요."
        )

    # 최신순 정렬 (TIME 내림차순) 후 최근 DISPLAY_COUNT 영업일 사용
    rows_sorted = sorted(rows, key=lambda r: r["TIME"], reverse=True)
    recent = rows_sorted[:DISPLAY_COUNT]

    lines = []
    for row in recent:
        date = datetime.strptime(row["TIME"], "%Y%m%d")
        rate = float(row["DATA_VALUE"])
        weekday_ko = WEEKDAYS_KO[date.weekday()]
        lines.append(
            f"{date.strftime('%Y-%m-%d')} ({weekday_ko}) — 1 USD = {rate:.2f} KRW"
        )

    latest_date = datetime.strptime(recent[0]["TIME"], "%Y%m%d").strftime("%Y-%m-%d")

    return (
        "USD/KRW 환율 (한국은행 매매기준율 — 영업일 기준)\n"
        + "\n".join(lines)
        + f"\n\n※ 가장 최근 영업일: {latest_date}. 환율 데이터는 1~2일 지연될 수 있습니다."
    )