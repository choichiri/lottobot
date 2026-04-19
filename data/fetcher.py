"""동행복권 당첨번호를 가져오는 모듈 (네이버 검색 크롤링 + 동행복권 API 폴백)"""

import re
import requests
from bs4 import BeautifulSoup
from config.settings import DRAW_RESULT_API
from data.store import load_data, get_latest_round, append_draws

NAVER_SEARCH_URL = "https://search.naver.com/search.naver?query=로또+{round_no}회+당첨번호"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _fetch_from_naver(round_no: int) -> dict | None:
    """네이버 검색 결과에서 당첨번호를 크롤링한다."""
    url = NAVER_SEARCH_URL.format(round_no=round_no)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[fetcher] {round_no}회 네이버 크롤링 실패: {e}")
        return None

    winning_div = soup.select_one(".winning_number")
    if not winning_div:
        return None

    # 결과 카드에 표시된 실제 회차 확인 (미추첨 회차 방지)
    parent = winning_div.parent
    for _ in range(5):
        round_match = re.search(r"(\d{3,4})회", parent.get_text()[:200])
        if round_match:
            displayed_round = int(round_match.group(1))
            if displayed_round != round_no:
                print(f"[fetcher] {round_no}회 요청했으나 {displayed_round}회 결과 반환 (미추첨)")
                return None
            break
        parent = parent.parent

    main_balls = [int(b.text.strip()) for b in winning_div.select("span.ball")]
    all_balls = [int(b.text.strip()) for b in soup.select("span.ball")]
    bonus_balls = [b for b in all_balls if b not in main_balls]

    if len(main_balls) != 6 or len(bonus_balls) != 1:
        print(f"[fetcher] {round_no}회 번호 파싱 이상: main={main_balls}, bonus={bonus_balls}")
        return None

    return {
        "회차": round_no,
        "번호1": main_balls[0],
        "번호2": main_balls[1],
        "번호3": main_balls[2],
        "번호4": main_balls[3],
        "번호5": main_balls[4],
        "번호6": main_balls[5],
        "보너스": bonus_balls[0],
    }


def _fetch_from_dhlottery(round_no: int) -> dict | None:
    """동행복권 API에서 당첨번호를 가져온다 (폴백)."""
    url = DRAW_RESULT_API.format(round_no=round_no)
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"[fetcher] {round_no}회 동행복권 API 실패: {e}")
        return None

    if data.get("returnValue") != "success":
        return None

    return {
        "회차": data["drwNo"],
        "번호1": data["drwtNo1"],
        "번호2": data["drwtNo2"],
        "번호3": data["drwtNo3"],
        "번호4": data["drwtNo4"],
        "번호5": data["drwtNo5"],
        "번호6": data["drwtNo6"],
        "보너스": data["bnusNo"],
    }


def fetch_draw(round_no: int) -> dict | None:
    """특정 회차의 당첨번호를 가져온다. 네이버 우선, 실패 시 동행복권 API 폴백."""
    result = _fetch_from_naver(round_no)
    if result:
        return result
    return _fetch_from_dhlottery(round_no)


def fetch_latest_draws() -> list[dict]:
    """CSV에 없는 최신 회차들을 모두 가져와서 CSV에 추가한다."""
    latest = get_latest_round()
    print(f"[fetcher] 현재 저장된 최신 회차: {latest}")

    new_rows = []
    round_no = latest + 1
    while True:
        result = fetch_draw(round_no)
        if result is None:
            break
        new_rows.append(result)
        print(f"[fetcher] {round_no}회 데이터 가져옴")
        round_no += 1

    if new_rows:
        append_draws(new_rows)
        print(f"[fetcher] 총 {len(new_rows)}개 신규 회차 추가 완료")
    else:
        print("[fetcher] 신규 회차 없음")

    return new_rows


if __name__ == "__main__":
    fetch_latest_draws()
