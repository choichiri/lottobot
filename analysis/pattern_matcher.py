"""과거 데이터에서 최근 패턴과 유사한 시퀀스를 찾는 모듈

매칭 전략 (적응형):
1단계: 최근 N회차 전체 시퀀스 매칭 (가장 엄격)
2단계: 피처 수를 줄여가며 시퀀스 매칭
3단계: 시퀀스 길이를 줄여가며 매칭
4단계: 최근 1회차의 피처 기반 유사 회차 탐색 (가장 완화)
"""

import pandas as pd
from collections import Counter
from config.settings import (
    RECENT_ROUNDS, MIN_MATCHES,
    SUM_BUCKET_SIZE, LAST_DIGIT_SUM_BUCKET_SIZE,
)
from analysis.features import compute_features, add_features_to_df
from data.store import get_numbers


def _bucketize(value: int, bucket_size: int) -> int:
    """연속값을 구간(bucket)으로 이산화한다."""
    return (value // bucket_size) * bucket_size


def _discretize_features(features: dict) -> dict:
    """연속 피처를 이산값으로 변환한다."""
    return {
        "홀짝": features["홀짝"],
        "고저": features["고저"],
        "번호합_구간": _bucketize(features["번호합"], SUM_BUCKET_SIZE),
        "끝수합_구간": _bucketize(features["끝수합"], LAST_DIGIT_SUM_BUCKET_SIZE),
        "AC값": features["AC값"],
    }


# 매칭에 사용할 피처 우선순위
FEATURE_PRIORITY = ["홀짝", "고저", "번호합_구간", "끝수합_구간", "AC값"]


def find_pattern_matches(
    df: pd.DataFrame,
    recent_n: int = RECENT_ROUNDS,
    min_matches: int = MIN_MATCHES,
) -> list[dict]:
    """최근 패턴과 유사한 과거 시퀀스를 찾고, 그 다음 회차의 피처를 반환한다."""
    df = df.copy().sort_values(df.columns[0]).reset_index(drop=True)
    df = add_features_to_df(df, get_numbers)

    # 각 행의 이산화된 피처
    discrete = []
    for _, row in df.iterrows():
        d = _discretize_features({
            "홀짝": row["홀짝"],
            "고저": row["고저"],
            "번호합": row["번호합"],
            "끝수합": row["끝수합"],
            "AC값": row["AC값"],
        })
        discrete.append(d)

    total = len(df)

    # === 1단계: 시퀀스 매칭 (윈도우 크기 + 피처 수 축소) ===
    for window_size in range(min(recent_n, 5), 0, -1):
        recent_pattern = discrete[total - window_size : total]
        for num_features in range(len(FEATURE_PRIORITY), 1, -1):
            selected = FEATURE_PRIORITY[:num_features]
            matches = _search_matches(discrete, recent_pattern, selected, total, window_size)
            if len(matches) >= min_matches:
                print(f"[matcher] 윈도우={window_size}, 피처={num_features}개로 {len(matches)}개 매칭")
                return _collect_next_features(df, matches, total)

    # === 2단계: 최근 1회차와 가장 유사한 회차 탐색 ===
    print("[matcher] 시퀀스 매칭 실패 - 유사도 기반 탐색으로 전환")
    return _find_similar_rounds(df, discrete, total, min_matches)


def _search_matches(
    discrete: list[dict],
    recent_pattern: list[dict],
    features: list[str],
    total: int,
    window_size: int,
) -> list[int]:
    """슬라이딩 윈도우로 패턴 매칭 위치(윈도우 마지막 인덱스)를 찾는다."""
    matches = []
    search_end = total - window_size
    for start in range(search_end):
        window = discrete[start : start + window_size]
        if _is_match(window, recent_pattern, features):
            matches.append(start + window_size - 1)
    return matches


def _is_match(window: list[dict], pattern: list[dict], features: list[str]) -> bool:
    """윈도우와 패턴이 선택된 피처에서 모두 일치하는지 확인한다."""
    for w, p in zip(window, pattern):
        for f in features:
            if w[f] != p[f]:
                return False
    return True


def _find_similar_rounds(
    df: pd.DataFrame,
    discrete: list[dict],
    total: int,
    min_matches: int,
) -> list[dict]:
    """최근 회차와 유사한 과거 회차들을 점수 기반으로 탐색한다."""
    recent = discrete[total - 1]
    scores = []

    for i in range(total - 1):
        score = 0
        d = discrete[i]
        if d["홀짝"] == recent["홀짝"]:
            score += 3
        if d["고저"] == recent["고저"]:
            score += 3
        if d["번호합_구간"] == recent["번호합_구간"]:
            score += 2
        if d["끝수합_구간"] == recent["끝수합_구간"]:
            score += 1
        if d["AC값"] == recent["AC값"]:
            score += 1
        scores.append((i, score))

    # 높은 점수 순으로 정렬
    scores.sort(key=lambda x: -x[1])

    # 최소 min_matches 이상, 상위 점수 회차의 다음 회차 수집
    top_score = scores[0][1]
    threshold = max(top_score - 1, scores[min(min_matches - 1, len(scores) - 1)][1])

    matches = [idx for idx, score in scores if score >= threshold and idx + 1 < total]
    matches = matches[:20]  # 최대 20개

    print(f"[matcher] 유사도 기반 {len(matches)}개 매칭 (임계점수: {threshold})")
    return _collect_next_features(df, matches, total)


def _collect_next_features(
    df: pd.DataFrame,
    match_indices: list[int],
    total: int,
) -> list[dict]:
    """매칭 위치의 다음 회차 피처를 수집한다."""
    results = []
    for idx in match_indices:
        next_idx = idx + 1
        if next_idx < total:
            row = df.iloc[next_idx]
            results.append({
                "홀짝": row["홀짝"],
                "고저": row["고저"],
                "번호합": int(row["번호합"]),
                "끝수합": int(row["끝수합"]),
                "AC값": int(row["AC값"]),
                "회차": int(row.iloc[0]),
            })
    return results
