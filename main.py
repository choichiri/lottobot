"""로또 자동화 시스템 - 메인 엔트리포인트

프로세스 흐름:
1. 이전 회차 당첨번호 조회 + CSV 업데이트
2. 이전 스케줄의 100개 후보/5개 구매번호와 당첨번호 비교 -> 텔레그램 알림
3. 최근 패턴 분석 -> 다음 회차 조건 유추
4. 조건 기반 100개 후보 번호 생성 -> candidates.csv 저장
5. 100개 중 가중치 기반 5세트 선택
6. 동행복권 사이트에서 자동 구매
7. 구매 결과 텔레그램 알림
8. 반복 (스케줄러)

사용법:
    python main.py convert       # xlsx -> csv 1회성 변환
    python main.py run            # 전체 파이프라인 실행
    python main.py run --dry-run  # 구매 없이 테스트
    python main.py scheduler      # 매주 자동 실행 데몬
    python main.py analyze        # 분석 + 번호 생성만
    python main.py fetch          # 신규 회차 데이터만 가져오기
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import PURCHASE_DAY, PURCHASE_TIME, LOG_PATH

# 로깅 설정
LOG_PATH.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            LOG_PATH / f"lotto_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("main")


def cmd_convert():
    """xlsx -> csv 변환"""
    from data.converter import convert_xlsx_to_csv
    convert_xlsx_to_csv()
    logger.info("변환 완료")


def cmd_fetch():
    """신규 회차 데이터 가져오기"""
    from data.fetcher import fetch_latest_draws
    new = fetch_latest_draws()
    logger.info(f"가져온 회차: {len(new)}건")
    return new


def cmd_analyze():
    """패턴 분석 + 번호 생성 (100개 후보 + 5개 선택)"""
    from data.store import load_data, get_latest_round
    from analysis.predictor import predict_next_criteria
    from generator.generator import (
        generate_candidates, save_candidates,
        select_final_sets, format_results,
    )

    df = load_data()
    latest_round = get_latest_round(df)
    target_round = latest_round + 1
    logger.info(f"데이터: {len(df)}회차 (최신: {latest_round}회)")
    logger.info(f"대상 회차: {target_round}회")

    # 예측 조건 도출
    criteria = predict_next_criteria(df)
    logger.info(f"예측 조건: {criteria}")

    # 100개 후보 생성 + 저장
    candidates = generate_candidates(criteria)
    save_candidates(candidates, target_round)

    # 5세트 최종 선택
    final_sets = select_final_sets(candidates)
    logger.info(f"최종 {len(final_sets)}세트:\n{format_results(final_sets)}")

    return target_round, candidates, final_sets


def step_check_previous_results():
    """[STEP 1-2] 이전 회차 결과 확인 + 텔레그램 알림"""
    from data.store import load_data, get_latest_round
    from data.history import get_purchased_sets, update_results
    from generator.generator import load_candidates
    from notification.telegram import send_result_report

    df = load_data()
    latest_round = get_latest_round(df)
    logger.info(f"=== 이전 회차({latest_round}회) 결과 확인 ===")

    # 당첨번호
    latest_row = df[df[df.columns[0]] == latest_round].iloc[0]
    winning_nums = [int(latest_row[f"번호{i}"]) for i in range(1, 7)]
    bonus = int(latest_row["보너스"])
    logger.info(f"당첨번호: {winning_nums} + {bonus}")

    # 구매한 5세트 결과 확인
    purchased = get_purchased_sets(latest_round)
    if not purchased:
        logger.info("이전 회차 구매 이력 없음 - 결과 비교 생략")
        return

    # 이력 업데이트
    results = update_results(latest_round, winning_nums, bonus)
    for r in results:
        rank_str = r["등수"] or "낙첨"
        logger.info(f"  {r['번호']} -> {r['일치수']}개 일치, {rank_str}")

    # 100개 후보 로드
    candidates = load_candidates(latest_round)

    # 텔레그램 알림
    send_result_report(latest_round, winning_nums, bonus, purchased, candidates)


def step_purchase(target_round: int, final_sets: list[list[int]], dry_run: bool = False):
    """[STEP 7] 동행복권 사이트에서 구매"""
    from purchase.buyer import LottoBuyer
    from data.history import save_purchase
    from notification.telegram import send_purchase_report, send_error

    # 구매 이력 저장 (구매 시도 전에 저장)
    save_purchase(target_round, final_sets)

    if dry_run:
        logger.info("[dry-run] 실제 구매 건너뜀")
        send_purchase_report(target_round, final_sets, True)
        return True

    try:
        with LottoBuyer(headless=True) as buyer:
            if not buyer.login():
                send_error(f"{target_round}회 로그인 실패")
                return False

            balance = buyer.check_balance()
            if balance < 5000:
                logger.info(f"예치금 부족({balance:,}원) - 자동 충전 시도")
                if buyer.charge_deposit():
                    time.sleep(5)
                    balance = buyer.check_balance()
                    logger.info(f"충전 후 잔액: {balance:,}원")
                    if balance < 5000:
                        send_error(f"{target_round}회 충전 후에도 잔액 부족: {balance:,}원")
                        return False
                else:
                    send_error(f"{target_round}회 예치금 부족({balance:,}원) + 자동 충전 실패")
                    return False

            success = buyer.purchase(final_sets)
            send_purchase_report(target_round, final_sets, success)
            return success
    except Exception as e:
        logger.error(f"구매 중 오류: {e}")
        send_error(f"{target_round}회 구매 오류: {e}")
        return False


def cmd_run(dry_run: bool = False):
    """전체 파이프라인 실행"""
    from notification.telegram import send_error

    logger.info("=" * 50)
    logger.info("로또 자동화 파이프라인 시작")
    logger.info("=" * 50)

    try:
        # STEP 1: 신규 회차 데이터 가져오기
        logger.info("[STEP 1] 최신 당첨번호 가져오기")
        cmd_fetch()

        # STEP 1-2: 이전 회차 결과 확인 + 텔레그램 알림
        logger.info("[STEP 2] 이전 회차 결과 확인")
        step_check_previous_results()

        # STEP 3-5: 분석 + 100개 생성 + 5개 선택
        logger.info("[STEP 3-5] 패턴 분석 + 번호 생성")
        target_round, candidates, final_sets = cmd_analyze()

        # STEP 6-7: 구매
        logger.info(f"[STEP 6-7] {target_round}회 구매")
        step_purchase(target_round, final_sets, dry_run=dry_run)

    except Exception as e:
        logger.error(f"파이프라인 오류: {e}", exc_info=True)
        send_error(f"파이프라인 오류: {e}")

    logger.info("파이프라인 완료")


def cmd_scheduler():
    """매주 자동 실행 데몬"""
    import schedule

    logger.info(f"스케줄러 시작 - 매주 {PURCHASE_DAY} {PURCHASE_TIME}")

    day_map = {
        "monday": schedule.every().monday,
        "tuesday": schedule.every().tuesday,
        "wednesday": schedule.every().wednesday,
        "thursday": schedule.every().thursday,
        "friday": schedule.every().friday,
        "saturday": schedule.every().saturday,
        "sunday": schedule.every().sunday,
    }

    job = day_map.get(PURCHASE_DAY, schedule.every().friday)
    job.at(PURCHASE_TIME).do(cmd_run)

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="로또 자동화 시스템")
    parser.add_argument(
        "command",
        choices=["convert", "fetch", "analyze", "run", "scheduler"],
        help="실행할 명령",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="구매 시 실제 결제 없이 테스트만 수행",
    )
    args = parser.parse_args()

    commands = {
        "convert": cmd_convert,
        "fetch": cmd_fetch,
        "analyze": cmd_analyze,
        "run": lambda: cmd_run(dry_run=args.dry_run),
        "scheduler": cmd_scheduler,
    }

    commands[args.command]()


if __name__ == "__main__":
    main()
