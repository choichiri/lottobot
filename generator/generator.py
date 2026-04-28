"""예측 조건을 만족하는 로또 번호 조합을 생성하는 모듈

프로세스:
1. 조건에 맞는 100개 후보 번호 생성 -> candidates.csv 저장
2. 100개 중 가중치 기반으로 5세트 최종 선택
"""

import random
import pandas as pd
from collections import Counter
from datetime import datetime
from analysis.features import (
    calc_odd_even, calc_high_low, calc_last_digit_sum,
    calc_number_sum, calc_ac_value,
)
from analysis.predictor import PredictionCriteria
from config.settings import (
    NUM_CANDIDATES, NUM_SETS, MAX_GENERATION_ATTEMPTS,
    CANDIDATES_CSV_PATH,
)


def generate_candidates(criteria: PredictionCriteria, count: int = NUM_CANDIDATES) -> list[list[int]]:
    """예측 조건을 만족하는 후보 번호 조합을 생성한다."""
    # 홀짝/고저 조합 리스트 생성
    oe_hl_combos = []
    for oe in criteria.홀짝:
        for hl in criteria.고저:
            oe_hl_combos.append((oe, hl))

    # 숫자 풀 분류
    odd_low = [n for n in range(1, 23) if n % 2 == 1]
    even_low = [n for n in range(1, 23) if n % 2 == 0]
    odd_high = [n for n in range(23, 46) if n % 2 == 1]
    even_high = [n for n in range(23, 46) if n % 2 == 0]

    results = []
    attempts = 0

    while len(results) < count and attempts < MAX_GENERATION_ATTEMPTS:
        attempts += 1
        oe, hl = random.choice(oe_hl_combos)
        odd_count, even_count = map(int, oe.split(":"))
        high_count, low_count = map(int, hl.split(":"))

        nums = _stratified_sample(
            odd_count, even_count, high_count, low_count,
            odd_low, even_low, odd_high, even_high,
        )
        if nums is None:
            continue

        s = calc_number_sum(nums)
        if not (criteria.번호합_min <= s <= criteria.번호합_max):
            continue

        lds = calc_last_digit_sum(nums)
        if not (criteria.끝수합_min <= lds <= criteria.끝수합_max):
            continue

        ac = calc_ac_value(nums)
        if ac < criteria.AC값_min:
            continue

        nums_sorted = sorted(nums)
        if nums_sorted not in results:
            results.append(nums_sorted)

    if len(results) < count:
        print(f"[generator] 경고: {attempts}회 시도 후 {len(results)}개만 생성됨")
    else:
        print(f"[generator] {count}개 후보 번호 생성 완료 ({attempts}회 시도)")

    return results


def save_candidates(candidates: list[list[int]], target_round: int) -> None:
    """후보 번호 100개를 CSV에 저장한다."""
    rows = []
    for i, nums in enumerate(candidates, 1):
        rows.append({
            "대상회차": target_round,
            "생성일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "순번": i,
            "번호1": nums[0], "번호2": nums[1], "번호3": nums[2],
            "번호4": nums[3], "번호5": nums[4], "번호6": nums[5],
        })
    df = pd.DataFrame(rows)
    df.to_csv(CANDIDATES_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[generator] 후보 {len(candidates)}개 저장: {CANDIDATES_CSV_PATH}")


def load_candidates(target_round: int | None = None) -> list[list[int]]:
    """저장된 후보 번호를 로드한다."""
    try:
        df = pd.read_csv(CANDIDATES_CSV_PATH, encoding="utf-8-sig")
    except FileNotFoundError:
        return []

    if target_round is not None:
        df = df[df["대상회차"] == target_round]

    candidates = []
    for _, row in df.iterrows():
        candidates.append([int(row[f"번호{i}"]) for i in range(1, 7)])
    return candidates


def select_final_sets(candidates: list[list[int]], num_sets: int = NUM_SETS) -> list[list[int]]:
    """100개 후보에서 다양성 기반으로 5세트를 최종 선택한다.

    선택 전략:
    1. 후보를 무작위로 섞음
    2. 첫 세트는 무조건 선택
    3. 이후 세트는 이미 선택된 세트들과의 번호 중복(overlap)이 적은 것 우선
    4. 5개 못 채우면 남은 후보에서 순서대로 추가
    """
    if len(candidates) <= num_sets:
        return candidates

    shuffled = candidates[:]
    random.shuffle(shuffled)

    selected = [shuffled[0]]
    used_numbers = Counter(shuffled[0])

    # overlap 임계치를 점진적으로 완화하며 다양성 우선 선택
    for threshold in (2, 3, 4, 5):
        for nums in shuffled[1:]:
            if len(selected) >= num_sets:
                break
            if nums in selected:
                continue
            overlap = sum(used_numbers[n] for n in nums)
            if overlap <= threshold:
                selected.append(nums)
                for n in nums:
                    used_numbers[n] += 1
        if len(selected) >= num_sets:
            break

    # 그래도 부족하면 남은 후보로 채움
    if len(selected) < num_sets:
        for nums in shuffled:
            if nums not in selected:
                selected.append(nums)
                if len(selected) >= num_sets:
                    break

    print(f"[generator] 최종 {len(selected)}세트 선택 완료")
    return selected


def _stratified_sample(
    odd_count: int, even_count: int,
    high_count: int, low_count: int,
    odd_low: list, even_low: list,
    odd_high: list, even_high: list,
) -> list[int] | None:
    """홀짝/고저 비율을 만족하도록 계층적으로 번호를 추출한다."""
    oh_min = max(0, odd_count - len(odd_low), high_count - len(even_high))
    oh_max = min(odd_count, high_count, len(odd_high))
    if oh_min > oh_max:
        return None

    oh = random.randint(oh_min, oh_max)
    ol = odd_count - oh
    eh = high_count - oh
    el = even_count - eh

    if ol < 0 or eh < 0 or el < 0:
        return None
    if ol > len(odd_low) or eh > len(even_high) or el > len(even_low):
        return None

    try:
        nums = (
            random.sample(odd_high, oh)
            + random.sample(odd_low, ol)
            + random.sample(even_high, eh)
            + random.sample(even_low, el)
        )
    except ValueError:
        return None

    return nums


def format_results(results: list[list[int]]) -> str:
    """생성 결과를 포맷팅한다."""
    lines = []
    for i, nums in enumerate(results, 1):
        nums_str = " ".join(f"{n:2d}" for n in nums)
        s = sum(nums)
        lines.append(f"  [{i}] {nums_str}  (합:{s})")
    return "\n".join(lines)
