"""동행복권 API에서 신규 당첨번호를 가져오는 모듈"""

import requests
from config.settings import DRAW_RESULT_API
from data.store import load_data, get_latest_round, append_draws


def fetch_draw(round_no: int) -> dict | None:
    """특정 회차의 당첨번호를 동행복권 API에서 가져온다."""
    url = DRAW_RESULT_API.format(round_no=round_no)
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"[fetcher] {round_no}회 API 호출 실패: {e}")
        return None

    if data.get("returnValue") != "success":
        return None

    return {
        "회차": data["drwNo"],
        "추첨일": data["drwNoDate"],
        "번호1": data["drwtNo1"],
        "번호2": data["drwtNo2"],
        "번호3": data["drwtNo3"],
        "번호4": data["drwtNo4"],
        "번호5": data["drwtNo5"],
        "번호6": data["drwtNo6"],
        "보너스": data["bnusNo"],
    }


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
