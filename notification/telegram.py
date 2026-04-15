"""텔레그램 알림 모듈"""

import logging
import requests
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def send_message(text: str) -> bool:
    """텔레그램 메시지를 전송한다."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("텔레그램 설정 없음 - 콘솔 출력으로 대체")
        print(f"[TELEGRAM] {text}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("텔레그램 알림 전송 완료")
            return True
        else:
            logger.error(f"텔레그램 전송 실패: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"텔레그램 전송 오류: {e}")
        return False


def send_result_report(round_no: int, winning_nums: list[int], bonus: int,
                       purchased_sets: list[list[int]], candidates_100: list[list[int]]) -> None:
    """이전 회차 결과 비교 리포트를 텔레그램으로 전송한다."""
    winning_set = set(winning_nums)

    # 구매한 5세트 결과
    purchase_lines = []
    for i, nums in enumerate(purchased_sets, 1):
        matched = sorted(set(nums) & winning_set)
        bonus_hit = bonus in nums
        rank = _determine_rank(len(matched), bonus_hit)
        mark = f" *** {rank} ***" if rank else ""
        purchase_lines.append(
            f"  [{i}] {_format_nums(nums)} - {len(matched)}개 일치{mark}"
        )

    # 100개 후보 등수별 통계
    from collections import Counter
    rank_counter = Counter()
    rank_details = {}  # 등수별 대표 번호 저장
    for nums in candidates_100:
        matched = sorted(set(nums) & winning_set)
        bonus_hit = bonus in nums
        rank = _determine_rank(len(matched), bonus_hit)
        label = rank or "낙첨"
        rank_counter[label] += 1
        if rank and label not in rank_details:
            rank_details[label] = f"{_format_nums(nums)} ({len(matched)}개 일치)"

    candidate_lines = []
    for r in ["1등", "2등", "3등", "4등", "5등"]:
        if rank_counter[r] > 0:
            candidate_lines.append(f"  {r}: {rank_counter[r]}건  ex) {rank_details[r]}")
    candidate_lines.append(f"  낙첨: {rank_counter['낙첨']}건")
    candidate_summary = "\n".join(candidate_lines)

    text = (
        f"<b>[로또 {round_no}회 결과]</b>\n"
        f"당첨번호: {_format_nums(winning_nums)} + {bonus}\n\n"
        f"<b>구매 5세트 결과:</b>\n"
        + "\n".join(purchase_lines) + "\n\n"
        f"<b>100개 후보 결과:</b>\n"
        + candidate_summary
    )
    send_message(text)


def send_purchase_report(round_no: int, purchased_sets: list[list[int]], success: bool) -> None:
    """구매 완료/실패 알림을 전송한다."""
    if success:
        lines = [f"  [{i}] {_format_nums(nums)}" for i, nums in enumerate(purchased_sets, 1)]
        text = (
            f"<b>[로또 {round_no}회 구매 완료]</b>\n"
            + "\n".join(lines)
        )
    else:
        text = f"<b>[로또 {round_no}회 구매 실패]</b>\n오류가 발생했습니다. 로그를 확인하세요."
    send_message(text)


def send_error(message: str) -> None:
    """에러 알림을 전송한다."""
    send_message(f"<b>[로또 오류]</b>\n{message}")


def _format_nums(nums: list[int]) -> str:
    return " ".join(f"{n:2d}" for n in sorted(nums))


def _determine_rank(match_count: int, bonus_hit: bool) -> str | None:
    """일치 개수로 등수를 판별한다."""
    if match_count == 6:
        return "1등"
    elif match_count == 5 and bonus_hit:
        return "2등"
    elif match_count == 5:
        return "3등"
    elif match_count == 4:
        return "4등"
    elif match_count == 3:
        return "5등"
    return None


def _rank_value(rank: str) -> int:
    """등수를 숫자로 변환 (비교용)."""
    return {"1등": 1, "2등": 2, "3등": 3, "4등": 4, "5등": 5}.get(rank, 99)
