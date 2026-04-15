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
    odd_count, even_count = map(int, criteria.홀짝.split(":"))
    high_count, low_count = map(int, criteria.고저.split(":"))

    # 숫자 풀 분류
    odd_low = [n for n in range(1, 23) if n % 2 == 1]
    even_low = [n for n in range(1, 23) if n % 2 == 0]
    odd_high = [n for n in range(23, 46) if n % 2 == 1]
    even_high = [n for n in range(23, 46) if n % 2 == 0]

    results = []
    attempts = 0

    while len(results) < count and attempts < MAX_GENERATION_ATTEMPTS:
        attempts += 1
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
    """100개 후보에서 가중치 기반으로 5세트를 최종 선택한다.

    선택 전략:
    1. 각 번호(1~45)의 후보 내 출현 빈도를 계산
    2. 각 조합의 점수 = 소속 번호들의 출현빈도 합
    3. 빈도가 높은 번호를 포함한 조합이 높은 점수 -> 자주 추천되는 번호 위주
    4. 상위 점수 조합들 중 번호 다양성을 고려하여 5세트 선택
    """
    if len(candidates) <= num_sets:
        return candidates

    # 번호별 출현 빈도
    freq = Counter()
    for nums in candidates:
        for n in nums:
            freq[n] += 1

    # 각 조합의 점수 계산
    scored = []
    for i, nums in enumerate(candidates):
        score = sum(freq[n] for n in nums)
        scored.append((i, score, nums))

    # 점수 내림차순 정렬
    scored.sort(key=lambda x: -x[1])

    # 다양성을 고려한 선택: 이미 선택된 세트와 번호 중복이 적은 것 우선
    selected = []
    used_numbers = Counter()

    for _, score, nums in scored:
        if len(selected) >= num_sets:
            break
        # 이미 선택된 세트와의 중복도 체크
        overlap = sum(used_numbers[n] for n in nums)
        # 상위 점수 조합 중 중복이 적으면 선택
        if overlap <= 3 or len(selected) < 2:
            selected.append(nums)
            for n in nums:
                used_numbers[n] += 1

    # 부족하면 나머지에서 랜덤 추가
    if len(selected) < num_sets:
        remaining = [nums for _, _, nums in scored if nums not in selected]
        random.shuffle(remaining)
        selected.extend(remaining[:num_sets - len(selected)])

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
