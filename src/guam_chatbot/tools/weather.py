"""괌 날씨 정보 도구 — OpenWeatherMap 5-day / 3-hour Forecast API.

가족 여행자가 괌의 날씨·기온·강수확률을 묻는 질문에 답하기 위한 도구.
시점이 있는 실시간 정보(예보)는 이 도구가, 일반 기후 정보(우기·건기 등)는
search_guam_guide가 담당.
"""

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

# .env에서 환경 변수 로드 (이미 로드되었어도 멱등적이라 안전)
load_dotenv()

# 괌 (Tumon) 좌표 — plan Section 5
GUAM_LAT = 13.4443
GUAM_LON = 144.7937

# 괌 표준시 UTC+10 (서머타임 없음)
GUAM_TZ = timezone(timedelta(hours=10))

# 한국어 요일 매핑 (locale 의존성 회피)
WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]

# OpenWeatherMap 5-day / 3-hour Forecast (무료, 카드 등록 X)
API_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _parse_to_guam_local(dt_txt: str) -> datetime:
    """OpenWeatherMap의 dt_txt(UTC, 'YYYY-MM-DD HH:MM:SS')를 괌 현지 시각으로 변환."""
    utc_dt = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(GUAM_TZ)


def _summarize_by_day(forecast_list: list) -> str:
    """40개 3시간 데이터를 괌 현지 날짜로 그룹화한 후 일별 한 줄 요약."""
    by_day = defaultdict(list)
    for item in forecast_list:
        guam_dt = _parse_to_guam_local(item["dt_txt"])
        by_day[guam_dt.date()].append((guam_dt, item))

    lines = []
    for day in sorted(by_day.keys()):
        items = by_day[day]
        temps = [it["main"]["temp"] for _, it in items]
        pops = [it.get("pop", 0.0) for _, it in items]

        # 대표 날씨 description: 정오 부근 (현지 12시)에 가장 가까운 슬롯
        noon_dt, noon_item = min(items, key=lambda x: abs(x[0].hour - 12))
        desc = noon_item["weather"][0]["description"]

        weekday_ko = WEEKDAYS_KO[day.weekday()]
        lines.append(
            f"{day.isoformat()} ({weekday_ko}) — "
            f"평균 {sum(temps) / len(temps):.0f}°C "
            f"(최저 {min(temps):.0f} / 최고 {max(temps):.0f}), "
            f"비 확률 {max(pops) * 100:.0f}%, "
            f"{desc}"
        )
    return "\n".join(lines)


@tool
def get_guam_weather(query: str) -> str:
    """괌의 현재 및 5일치 날씨 예보를 가져옵니다.

    사용자가 괌의 날씨, 기온, 강수확률, 우천 여부 등 시점이 있는 실시간 정보를
    물어볼 때 사용하세요.
    예: 5월 둘째 주 괌 날씨 어때?, 내일 비 와?, 오늘 우비 챙겨야 해?

    이 도구는 5일 후까지의 예보만 제공합니다. 그 이후의 날씨나 일반 기후 정보
    (우기·건기, 평균 기온 등)는 search_guam_guide를 사용하세요.
    """
    # query는 현재 사용 안 함. 위치는 괌 (Tumon) 고정.
    # 향후 시간대 필터 등으로 확장 시 활용 가능.

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return (
            "날씨 정보 조회 실패: OPENWEATHER_API_KEY가 설정되지 않았습니다. "
            ".env 파일을 확인하세요. 다른 방법을 시도해주세요."
        )

    try:
        response = requests.get(
            API_URL,
            params={
                "lat": GUAM_LAT,
                "lon": GUAM_LON,
                "appid": api_key,
                "units": "metric",   # 섭씨
                "lang": "kr",         # 한국어 description
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.HTTPError as e:
        status = response.status_code
        if status == 401:
            return (
                "날씨 정보 조회 실패: OpenWeatherMap API 키가 활성화되지 않았거나 "
                "잘못되었습니다. 키 발급 후 활성화에 10분~2시간 걸립니다. "
                "다른 방법을 시도해주세요."
            )
        if status == 429:
            return (
                "날씨 정보 조회 실패: 호출 한도(분당 60회) 초과. "
                "잠시 후 다시 시도해주세요."
            )
        return f"날씨 정보 조회 실패: HTTP {status} ({e}). 다른 방법을 시도해주세요."

    except requests.exceptions.RequestException as e:
        return f"날씨 정보 조회 실패: {e}. 다른 방법을 시도해주세요."

    # JSON 파싱 단계 — 응답 구조가 예상과 다를 경우 잡힘
    try:
        summary = _summarize_by_day(data["list"])
    except (KeyError, ValueError) as e:
        return f"날씨 데이터 형식 오류: {e}. 다른 방법을 시도해주세요."

    return (
        f"괌 (Tumon) 5일 일별 날씨 예보 (괌 현지 시각 기준)\n"
        f"{summary}\n\n"
        f"※ 본 예보는 5일 한도이며, 그 이후 날짜는 알 수 없습니다."
    )