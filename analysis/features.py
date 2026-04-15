"""로또 번호의 분석 지표(피처) 계산 모듈

피처 목록:
- 홀짝: 홀수:짝수 비율 (예: "3:3")
- 고저: 고(23~45):저(1~22) 비율 (예: "2:4")
- 끝수합: 각 번호의 일의자리 합
- 번호합: 6개 번호의 총합
- AC값: Arithmetic Complexity (유니크 차이 수 - 5)
"""

from itertools import combinations
from config.settings import LOW_HIGH_BOUNDARY


def calc_odd_even(numbers: list[int]) -> str:
    """홀짝 비율을 '홀:짝' 형식으로 반환한다."""
    odd = sum(1 for n in numbers if n % 2 == 1)
    even = len(numbers) - odd
    return f"{odd}:{even}"


def calc_high_low(numbers: list[int]) -> str:
    """고저 비율을 '고:저' 형식으로 반환한다."""
    high = sum(1 for n in numbers if n >= LOW_HIGH_BOUNDARY)
    low = len(numbers) - high
    return f"{high}:{low}"


def calc_last_digit_sum(numbers: list[int]) -> int:
    """끝수합(일의자리 숫자의 합)을 반환한다."""
    return sum(n % 10 for n in numbers)


def calc_number_sum(numbers: list[int]) -> int:
    """번호합(6개 번호의 총합)을 반환한다."""
    return sum(numbers)


def calc_ac_value(numbers: list[int]) -> int:
    """AC값을 계산한다. (모든 쌍의 차이값 중 유니크 개수 - 5)"""
    diffs = set()
    for a, b in combinations(sorted(numbers), 2):
        diffs.add(b - a)
    return len(diffs) - 5


def compute_features(numbers: list[int]) -> dict:
    """6개 번호에 대한 모든 피처를 계산하여 딕셔너리로 반환한다."""
    return {
        "홀짝": calc_odd_even(numbers),
        "고저": calc_high_low(numbers),
        "끝수합": calc_last_digit_sum(numbers),
        "번호합": calc_number_sum(numbers),
        "AC값": calc_ac_value(numbers),
    }


def add_features_to_df(df, get_numbers_fn):
    """DataFrame에 피처 컬럼들을 추가한다.

    Args:
        df: 로또 데이터 DataFrame
        get_numbers_fn: 행에서 번호 리스트를 추출하는 함수
    """
    features_list = []
    for _, row in df.iterrows():
        nums = get_numbers_fn(row)
        features_list.append(compute_features(nums))

    import pandas as pd
    features_df = pd.DataFrame(features_list)
    for col in features_df.columns:
        df[col] = features_df[col].values
    return df
