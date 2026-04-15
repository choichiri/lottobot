"""CSV 데이터 저장소 - 읽기/쓰기/추가"""

import pandas as pd
from config.settings import CSV_PATH


def load_data() -> pd.DataFrame:
    """CSV 파일을 DataFrame으로 로드한다."""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    return df


def get_latest_round(df: pd.DataFrame | None = None) -> int:
    """저장된 데이터의 최신 회차 번호를 반환한다."""
    if df is None:
        df = load_data()
    return int(df["회차"].max())


def get_recent(n: int, df: pd.DataFrame | None = None) -> pd.DataFrame:
    """최근 n회차 데이터를 반환한다."""
    if df is None:
        df = load_data()
    return df.sort_values("회차").tail(n).reset_index(drop=True)


def get_numbers(row: pd.Series) -> list[int]:
    """DataFrame 한 행에서 번호 6개를 리스트로 반환한다."""
    return [int(row[f"번호{i}"]) for i in range(1, 7)]


def append_draws(new_rows: list[dict]) -> None:
    """새로운 회차 데이터를 CSV에 추가한다."""
    if not new_rows:
        return
    df = load_data()
    new_df = pd.DataFrame(new_rows)
    df = pd.concat([df, new_df], ignore_index=True)
    df = df.sort_values("회차").reset_index(drop=True)
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[store] {len(new_rows)}개 회차 추가 완료 (최신: {int(df['회차'].max())}회)")
