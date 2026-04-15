import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ===== 경로 =====
BASE_DIR = Path(__file__).resolve().parent.parent
XLSX_PATH = BASE_DIR / "lotto.xlsx"
CSV_PATH = BASE_DIR / "lotto.csv"
CANDIDATES_CSV_PATH = BASE_DIR / "candidates.csv"   # 100개 후보번호 저장
HISTORY_CSV_PATH = BASE_DIR / "purchase_history.csv" # 구매 이력 누적
LOG_PATH = BASE_DIR / "logs"

# ===== 동행복권 =====
DHLOTTERY_ID = os.getenv("DHLOTTERY_ID", "")
DHLOTTERY_PW = os.getenv("DHLOTTERY_PW", "")
DRAW_RESULT_API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={round_no}"
DHLOTTERY_LOGIN_URL = "https://dhlottery.co.kr/user.do?method=login"
DHLOTTERY_PURCHASE_URL = "https://ol.dhlottery.co.kr/olotto/game/game645.do"

# ===== 텔레그램 =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ===== 예치금 충전 =====
DEPOSIT_PIN = os.getenv("DEPOSIT_PIN", "")  # 간편충전 비밀번호 (6자리)
DEPOSIT_AMOUNT = 5000  # 충전 금액 (원)

# ===== 분석 파라미터 =====
RECENT_ROUNDS = 5          # 최근 몇 회차를 패턴으로 사용할지
MIN_MATCH_LENGTH = 3       # 최소 연속 매칭 길이
MIN_MATCHES = 3            # 최소 매칭 횟수 (이 이상이어야 예측에 사용)
FALLBACK_FEATURES = 3      # 매칭 실패 시 줄여나갈 피처 수

# 번호합 구간 (버킷 크기)
SUM_BUCKET_SIZE = 20
# 끝수합 구간
LAST_DIGIT_SUM_BUCKET_SIZE = 10

# ===== 번호 생성 =====
NUM_CANDIDATES = 100       # 후보 번호 조합 수
NUM_SETS = 5               # 최종 구매 조합 수
NUMBERS_PER_SET = 6
NUMBER_RANGE = (1, 45)
MAX_GENERATION_ATTEMPTS = 500_000  # 최대 생성 시도 횟수

# ===== 스케줄 =====
PURCHASE_DAY = "friday"
PURCHASE_TIME = "18:00"

# ===== 로또 기본 상수 =====
LOW_HIGH_BOUNDARY = 23     # 1~22: 저, 23~45: 고
LOTTO_START_DATE = "2002-12-07"  # 1회차 추첨일
