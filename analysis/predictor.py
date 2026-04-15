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
    홀짝: str                  # 예: "3:3"
    고저: str                  # 예: "2:4"
    번호합_min: int
    번호합_max: int
    끝수합_min: int
    끝수합_max: int
    AC값_min: int

    def __str__(self) -> str:
        return (
            f"홀짝={self.홀짝} | 고저={self.고저} | "
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
    """매칭 결과에서 최빈값/범위를 이용해 조건을 만든다."""
    # 홀짝: 최빈값
    odd_even_counter = Counter(m["홀짝"] for m in matches)
    best_odd_even = odd_even_counter.most_common(1)[0][0]

    # 고저: 최빈값
    high_low_counter = Counter(m["고저"] for m in matches)
    best_high_low = high_low_counter.most_common(1)[0][0]

    # 번호합: 평균 ± 표준편차
    sums = [m["번호합"] for m in matches]
    avg_sum = sum(sums) / len(sums)
    if len(sums) > 1:
        std_sum = (sum((s - avg_sum) ** 2 for s in sums) / (len(sums) - 1)) ** 0.5
    else:
        std_sum = 20  # 데이터 부족 시 기본 편차
    sum_min = max(21, int(avg_sum - std_sum))
    sum_max = min(255, int(avg_sum + std_sum))

    # 끝수합: 평균 ± 표준편차
    lds = [m["끝수합"] for m in matches]
    avg_ld = sum(lds) / len(lds)
    if len(lds) > 1:
        std_ld = (sum((s - avg_ld) ** 2 for s in lds) / (len(lds) - 1)) ** 0.5
    else:
        std_ld = 8
    ld_min = max(0, int(avg_ld - std_ld))
    ld_max = min(54, int(avg_ld + std_ld))

    # AC값: 최빈값을 최소값으로
    ac_counter = Counter(m["AC값"] for m in matches)
    best_ac = ac_counter.most_common(1)[0][0]
    ac_min = max(best_ac - 1, 0)

    criteria = PredictionCriteria(
        홀짝=best_odd_even,
        고저=best_high_low,
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
        홀짝="3:3",
        고저="3:3",
        번호합_min=100,
        번호합_max=170,
        끝수합_min=15,
        끝수합_max=35,
        AC값_min=7,
    )
    print(f"[predictor] 폴백 조건 사용: {criteria}")
    return criteria
