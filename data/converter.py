"""lotto.xlsx → lotto.csv 1회성 변환 모듈"""

import pandas as pd
from config.settings import XLSX_PATH, CSV_PATH


# CSV 표준 컬럼명 (xlsx의 12개 컬럼 순서에 대응)
POSITIONAL_COLUMNS = [
    "회차", "번호1", "번호2", "번호3", "번호4", "번호5", "번호6",
    "보너스", "1등당첨금", "1등당첨자", "2등당첨금", "2등당첨자",
]

KEEP_COLUMNS = ["회차", "번호1", "번호2", "번호3", "번호4", "번호5", "번호6", "보너스"]


def convert_xlsx_to_csv() -> pd.DataFrame:
    """xlsx 파일을 읽어 표준 CSV로 변환 저장한다."""
    df = pd.read_excel(XLSX_PATH, engine="openpyxl")
    print(f"[converter] xlsx 로드 완료: {len(df)}행, 컬럼 수={len(df.columns)}")

    # 위치 기반 컬럼 매핑 (인코딩 깨짐 대응)
    if len(df.columns) == len(POSITIONAL_COLUMNS):
        df.columns = POSITIONAL_COLUMNS
    else:
        # 컬럼 수가 다르면 기존 이름 기반 매핑 시도
        col_map = _detect_column_mapping(df)
        df = df.rename(columns=col_map)

    # 필요한 컬럼만 추출
    df = df[KEEP_COLUMNS]

    # 회차 기준 오름차순 정렬
    df = df.sort_values("회차").reset_index(drop=True)

    # 숫자 컬럼 정수 변환
    for c in KEEP_COLUMNS:
        df[c] = df[c].astype(int)

    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"[converter] CSV 저장 완료: {CSV_PATH} ({len(df)}행)")
    return df


def _detect_column_mapping(df: pd.DataFrame) -> dict:
    """xlsx 컬럼명을 표준 컬럼명으로 매핑한다 (폴백용)."""
    cols = list(df.columns)
    mapping = {}

    # 첫 번째 숫자 컬럼을 회차로 추정
    for c in cols:
        if df[c].dtype in ("int64", "float64"):
            mapping[c] = "회차"
            start = cols.index(c) + 1
            # 이후 6개를 번호, 1개를 보너스로
            for j in range(6):
                if start + j < len(cols):
                    mapping[cols[start + j]] = f"번호{j+1}"
            if start + 6 < len(cols):
                mapping[cols[start + 6]] = "보너스"
            break

    print(f"[converter] 컬럼 매핑: {mapping}")
    return mapping


if __name__ == "__main__":
    convert_xlsx_to_csv()
