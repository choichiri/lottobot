"""구매 이력 및 결과 비교 관리 모듈"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from config.settings import HISTORY_CSV_PATH


HISTORY_COLUMNS = [
    "회차", "구매일시", "구매번호", "당첨번호", "보너스",
    "일치수", "등수", "당첨금",
]


def save_purchase(target_round: int, purchased_sets: list[list[int]]) -> None:
    """구매한 번호를 이력에 저장한다."""
    rows = []
    for nums in purchased_sets:
        rows.append({
            "회차": target_round,
            "구매일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "구매번호": ",".join(map(str, nums)),
            "당첨번호": "",
            "보너스": "",
            "일치수": "",
            "등수": "",
            "당첨금": "",
        })
    _append_rows(rows)
    print(f"[history] {target_round}회 구매 {len(purchased_sets)}세트 이력 저장")


def update_results(round_no: int, winning_nums: list[int], bonus: int) -> list[dict]:
    """이전 회차 구매 이력에 당첨 결과를 업데이트한다.

    Returns:
        업데이트된 행의 결과 리스트
    """
    if not Path(HISTORY_CSV_PATH).exists():
        return []

    df = pd.read_csv(HISTORY_CSV_PATH, encoding="utf-8-sig", dtype=str)
    winning_set = set(winning_nums)
    results = []

    for idx, row in df.iterrows():
        if str(row["회차"]) != str(round_no):
            continue
        if row.get("등수", "") not in ("", "nan"):
            # 이미 결과가 있으면 스킵
            purchased = list(map(int, str(row["구매번호"]).split(",")))
            matched = len(set(purchased) & winning_set)
            bonus_hit = bonus in purchased
            rank = _determine_rank(matched, bonus_hit)
            results.append({"번호": purchased, "일치수": matched, "등수": rank})
            continue

        purchased = list(map(int, str(row["구매번호"]).split(",")))
        matched = len(set(purchased) & winning_set)
        bonus_hit = bonus in purchased
        rank = _determine_rank(matched, bonus_hit)

        df.at[idx, "당첨번호"] = ",".join(map(str, winning_nums))
        df.at[idx, "보너스"] = str(bonus)
        df.at[idx, "일치수"] = str(matched)
        df.at[idx, "등수"] = rank or "낙첨"
        df.at[idx, "당첨금"] = ""

        results.append({"번호": purchased, "일치수": matched, "등수": rank})

    df.to_csv(HISTORY_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[history] {round_no}회 결과 업데이트 완료")
    return results


def get_purchased_sets(round_no: int) -> list[list[int]]:
    """특정 회차의 구매 번호를 반환한다."""
    if not Path(HISTORY_CSV_PATH).exists():
        return []

    df = pd.read_csv(HISTORY_CSV_PATH, encoding="utf-8-sig", dtype=str)
    df_round = df[df["회차"].astype(str) == str(round_no)]

    sets = []
    for _, row in df_round.iterrows():
        nums = list(map(int, str(row["구매번호"]).split(",")))
        sets.append(nums)
    return sets


def _append_rows(rows: list[dict]) -> None:
    """이력 CSV에 행을 추가한다."""
    new_df = pd.DataFrame(rows)
    if Path(HISTORY_CSV_PATH).exists():
        existing = pd.read_csv(HISTORY_CSV_PATH, encoding="utf-8-sig", dtype=str)
        df = pd.concat([existing, new_df], ignore_index=True)
    else:
        df = new_df
    df.to_csv(HISTORY_CSV_PATH, index=False, encoding="utf-8-sig")


def _determine_rank(match_count: int, bonus_hit: bool) -> str | None:
    if match_count == 6:
        return "1등"
    elif match_count == 5 and bonus_hit:
        return "2등"
    elif match_count == 5:
        return "3등"
    elif match_count == 4:
        return "4등"
    elif match_count == 3:
        return "5등"
    return None
