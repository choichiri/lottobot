"""패턴 매칭 결과에서 다음 회차의 예측 조건을 도출하는 모듈"""

from collections import Counter
from dataclasses import dataclass
import pandas as pd
from analysis.pattern_matcher import find_pattern_matches
from analysis.features import add_features_to_df
from data.store import get_numbers


@dataclass
class PredictionCriteria:
    """번호 생성에 사용할 예측 조건"""
    홀짝: list[str]            # 예: ["3:3", "2:4", "4:2"]
    고저: list[str]            # 예: ["3:3", "2:4", "4:2"]
    번호합_min: int
    번호합_max: int
    끝수합_min: int
    끝수합_max: int
    AC값_min: int

    def __str__(self) -> str:
        return (
            f"홀짝={','.join(self.홀짝)} | 고저={','.join(self.고저)} | "
            f"번호합={self.번호합_min}~{self.번호합_max} | "
            f"끝수합={self.끝수합_min}~{self.끝수합_max} | "
            f"AC값≥{self.AC값_min}"
        )


def predict_next_criteria(df: pd.DataFrame) -> PredictionCriteria:
    """과거 패턴 매칭을 통해 다음 회차의 예측 조건을 도출한다."""
    next_features = find_pattern_matches(df)

    if next_features:
        return _derive_from_matches(next_features)
    else:
        return _derive_from_overall(df)


def _derive_from_matches(matches: list[dict]) -> PredictionCriteria:
    """매칭 결과에서 상위 빈도/범위를 이용해 조건을 만든다."""
    # 홀짝: 상위 3개
    odd_even_counter = Counter(m["홀짝"] for m in matches)
    top_odd_even = [v for v, _ in odd_even_counter.most_common(3)]

    # 고저: 상위 3개
    high_low_counter = Counter(m["고저"] for m in matches)
    top_high_low = [v for v, _ in high_low_counter.most_common(3)]

    # 번호합: 평균 ± 2σ, 최소 폭 50 보장
    sums = [m["번호합"] for m in matches]
    avg_sum = sum(sums) / len(sums)
    if len(sums) > 1:
        std_sum = (sum((s - avg_sum) ** 2 for s in sums) / (len(sums) - 1)) ** 0.5
    else:
        std_sum = 20
    sum_range = max(2.0 * std_sum, 25)  # 최소 폭 50 (±25)
    sum_min = max(21, int(avg_sum - sum_range))
    sum_max = min(255, int(avg_sum + sum_range))

    # 끝수합: 평균 ± 2σ, 최소 폭 15 보장
    lds = [m["끝수합"] for m in matches]
    avg_ld = sum(lds) / len(lds)
    if len(lds) > 1:
        std_ld = (sum((s - avg_ld) ** 2 for s in lds) / (len(lds) - 1)) ** 0.5
    else:
        std_ld = 8
    ld_range = max(2.0 * std_ld, 7.5)  # 최소 폭 15 (±7.5)
    ld_min = max(0, int(avg_ld - ld_range))
    ld_max = min(54, int(avg_ld + ld_range))

    # AC값: 최빈값 - 2 이상
    ac_counter = Counter(m["AC값"] for m in matches)
    best_ac = ac_counter.most_common(1)[0][0]
    ac_min = max(best_ac - 2, 0)

    criteria = PredictionCriteria(
        홀짝=top_odd_even,
        고저=top_high_low,
        번호합_min=sum_min,
        번호합_max=sum_max,
        끝수합_min=ld_min,
        끝수합_max=ld_max,
        AC값_min=ac_min,
    )
    print(f"[predictor] 패턴 매칭 기반 예측 조건: {criteria}")
    print(f"[predictor] 참고 매칭 {len(matches)}건 - 회차: {[m['회차'] for m in matches]}")
    return criteria


def _derive_from_overall(df: pd.DataFrame) -> PredictionCriteria:
    """매칭 실패 시 전체 데이터 통계 기반 폴백 조건을 만든다."""
    df = df.copy()
    df = add_features_to_df(df, get_numbers)

    criteria = PredictionCriteria(
        홀짝=["3:3", "2:4", "4:2"],
        고저=["3:3", "2:4", "4:2"],
        번호합_min=100,
        번호합_max=170,
        끝수합_min=15,
        끝수합_max=35,
        AC값_min=7,
    )
    print(f"[predictor] 폴백 조건 사용: {criteria}")
    return criteria
