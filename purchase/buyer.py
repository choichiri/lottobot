"""동행복권 자동 로그인 및 로또 구매 모듈

Selenium을 이용해 동행복권 사이트에 접속하여:
1. 로그인 (RSA 암호화 방식)
2. 예치금 잔액 확인
3. 로또 번호 선택 및 구매
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.settings import DHLOTTERY_ID, DHLOTTERY_PW, DEPOSIT_PIN, DEPOSIT_AMOUNT

logger = logging.getLogger(__name__)

# 동행복권 URL (2026년 리뉴얼 반영)
BASE_URL = "https://www.dhlottery.co.kr"
LOGIN_PAGE = f"{BASE_URL}/login"
PURCHASE_PAGE = "https://ol.dhlottery.co.kr/olotto/game/game645.do"


class LottoBuyer:
    def __init__(self, headless: bool = False):
        self.driver = None
        self.headless = headless

    def _init_driver(self):
        """Chrome WebDriver를 초기화한다."""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        self.driver.implicitly_wait(10)

    def login(self) -> bool:
        """동행복권 사이트에 로그인한다."""
        if not DHLOTTERY_ID or not DHLOTTERY_PW:
            logger.error("동행복권 ID/PW가 .env에 설정되지 않았습니다")
            return False

        try:
            self._init_driver()
            self.driver.get(LOGIN_PAGE)
            time.sleep(3)

            # ID 입력
            id_input = self.driver.find_element(By.ID, "inpUserId")
            id_input.clear()
            id_input.send_keys(DHLOTTERY_ID)

            # PW 입력
            pw_input = self.driver.find_element(By.ID, "inpUserPswdEncn")
            pw_input.clear()
            pw_input.send_keys(DHLOTTERY_PW)
            time.sleep(0.5)

            # login() JS 함수 호출 (RSA 암호화 + 폼 제출)
            self.driver.execute_script("login();")
            time.sleep(5)

            # 로그인 성공 확인 (로그인 페이지에서 벗어났는지)
            current_url = self.driver.current_url
            if "/login" not in current_url:
                logger.info("로그인 성공")
                return True
            else:
                logger.error("로그인 실패 - ID/PW를 확인하세요")
                return False

        except Exception as e:
            logger.error(f"로그인 중 오류: {e}")
            return False

    def check_balance(self) -> int:
        """예치금 잔액을 확인한다 (마이페이지에서 조회)."""
        try:
            self.driver.get(f"{BASE_URL}/mypage/home")
            time.sleep(3)

            # 예치금 잔액: div.deposit-inner-box 내부 숫자
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, ".deposit-inner-box")
                text = el.text.replace(",", "").replace("원", "").strip()
                # 숫자만 추출
                import re
                nums = re.findall(r'\d+', text)
                if nums:
                    balance = int(nums[0])
                    logger.info(f"예치금 잔액: {balance:,}원")
                    return balance
            except Exception:
                pass

            # 구매가능금액 폴백
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, ".pssbl-num")
                text = el.text.replace(",", "").replace("원", "").strip()
                import re
                nums = re.findall(r'\d+', text)
                if nums:
                    balance = int(nums[0])
                    logger.info(f"구매가능 금액: {balance:,}원")
                    return balance
            except Exception:
                pass

            logger.warning("잔액 확인 실패 - 셀렉터를 찾지 못함")
            return 0
        except Exception as e:
            logger.warning(f"잔액 확인 실패: {e}")
            return 0

    def charge_deposit(self, amount: int = DEPOSIT_AMOUNT) -> bool:
        """예치금을 간편충전한다.

        1. 충전 페이지 접속
        2. 금액 선택 (드롭다운)
        3. 충전하기 버튼 클릭
        4. 보안 키패드에서 비밀번호 입력
        """
        if not DEPOSIT_PIN:
            logger.error("간편충전 비밀번호가 .env에 설정되지 않았습니다 (DEPOSIT_PIN)")
            return False

        try:
            self.driver.get(f"{BASE_URL}/mypage/mndpChrg")
            time.sleep(3)

            # 금액 드롭다운 선택 (id=EcAmt)
            from selenium.webdriver.support.ui import Select
            select = Select(self.driver.find_element(By.ID, "EcAmt"))
            select.select_by_value(str(amount))
            time.sleep(1)
            logger.info(f"충전 금액 {amount:,}원 선택")

            # 충전하기 버튼 클릭 (JS 함수 직접 호출)
            self.driver.execute_script("MndpChrgM.fn_openEcRegistAccountCheck();")
            time.sleep(5)

            # 보안 키패드 비밀번호 입력
            success = self._enter_pin(DEPOSIT_PIN)
            if not success:
                logger.error("비밀번호 입력 실패")
                return False

            time.sleep(5)
            logger.info(f"예치금 {amount:,}원 충전 요청 완료")
            return True

        except Exception as e:
            logger.error(f"예치금 충전 중 오류: {e}")
            return False

    def _enter_pin(self, pin: str) -> bool:
        """NProtect 보안 키패드에서 OCR로 숫자 위치를 파악하여 비밀번호를 입력한다.

        키패드 구조: 3열 x 4행 이미지 (390x252px 실제, 이미지는 780px 2배)
        - 행 0~2: 숫자 9개 (랜덤 배치)
        - 행 3: 전체삭제 / 나머지 숫자 1개 / 삭제(x)
        """
        import io
        import os
        import platform
        from PIL import Image
        import pytesseract

        # OS별 tesseract 경로 자동 설정 (Windows는 기본 설치 경로, 리눅스는 PATH 사용)
        if platform.system() == "Windows":
            win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            if os.path.exists(win_path):
                pytesseract.pytesseract.tesseract_cmd = win_path

        try:
            time.sleep(2)

            # 키패드 이미지 요소
            keypad_img_el = self.driver.find_element(By.CSS_SELECTOR, ".kpd-image-button")
            img_bytes = keypad_img_el.screenshot_as_png
            img = Image.open(io.BytesIO(img_bytes))

            # 이미지의 왼쪽 절반만 실제 키패드 (오른쪽은 빈 영역)
            actual_w = img.width // 2
            actual_h = img.height
            keypad_area = img.crop((0, 0, actual_w, actual_h))

            # 3열 x 4행 격자에서 각 셀 OCR
            cell_w = actual_w // 3
            cell_h = actual_h // 4
            digit_positions = {}  # digit -> (center_x, center_y) in keypad_img_el 좌표

            for row in range(4):
                for col in range(3):
                    x1 = col * cell_w
                    y1 = row * cell_h
                    # 셀 중앙 부분만 크롭 (여백 제거로 OCR 정확도 향상)
                    margin_x = cell_w // 4
                    margin_y = cell_h // 6
                    cell = keypad_area.crop((x1 + margin_x, y1 + margin_y,
                                             x1 + cell_w - margin_x, y1 + cell_h - margin_y))

                    text = pytesseract.image_to_string(
                        cell, config="--psm 10 -c tessedit_char_whitelist=0123456789"
                    ).strip()

                    if text and len(text) == 1 and text.isdigit():
                        # 클릭 좌표는 원본 이미지(2배) 기준이 아니라 요소 기준
                        # kpd-image-button의 실제 렌더링 크기 사용
                        el_width = keypad_img_el.size["width"]
                        el_height = keypad_img_el.size["height"]
                        scale_x = el_width / img.width
                        scale_y = el_height / img.height
                        center_x = int((x1 + cell_w / 2) * scale_x)
                        center_y = int((y1 + cell_h / 2) * scale_y)
                        digit_positions[text] = (center_x, center_y)

            logger.info(f"키패드 OCR 결과: {list(digit_positions.keys())}")

            if len(digit_positions) < 10:
                logger.warning(f"OCR 인식 부족: {len(digit_positions)}/10개만 인식됨")

            # 각 PIN 숫자 클릭
            from selenium.webdriver.common.action_chains import ActionChains
            for digit in pin:
                if digit not in digit_positions:
                    logger.error(f"키패드에서 숫자 '{digit}'를 OCR로 인식하지 못함")
                    return False
                cx, cy = digit_positions[digit]
                ActionChains(self.driver).move_to_element_with_offset(
                    keypad_img_el, cx - keypad_img_el.size["width"] // 2,
                    cy - keypad_img_el.size["height"] // 2
                ).click().perform()
                time.sleep(0.5)

            logger.info("비밀번호 입력 완료")
            return True

        except Exception as e:
            logger.error(f"키패드 OCR 입력 오류: {e}")
            return False

    def purchase(self, number_sets: list[list[int]], dry_run: bool = False) -> bool:
        """로또 번호를 선택하고 구매한다."""
        if len(number_sets) > 5:
            logger.error("온라인 구매는 1회 최대 5세트까지 가능합니다")
            number_sets = number_sets[:5]

        try:
            self.driver.get(PURCHASE_PAGE)
            time.sleep(5)

            # 팝업 닫기
            self._close_popups()
            time.sleep(1)

            # iframe 안에 구매 UI가 있을 수 있음 - 자동 진입
            self._switch_to_purchase_iframe()

            for i, nums in enumerate(number_sets):
                logger.info(f"[{i+1}세트] 번호 선택: {nums}")
                for num in nums:
                    self._click_number_label(num)
                    time.sleep(0.1)

                # 확인 버튼 클릭 (#btnSelectNum)
                self._safe_click(By.ID, "btnSelectNum")
                time.sleep(0.5)

            if dry_run:
                logger.info("[dry-run] 번호 선택 완료 - 실제 구매는 건너뜁니다")
                return True

            # 구매하기 버튼 클릭
            self._safe_click(By.ID, "btnBuy")
            time.sleep(1)

            # 구매 확인 팝업 - "확인" 클릭
            self.driver.execute_script("closepopupLayerConfirm(true);")
            time.sleep(3)

            logger.info(f"구매 완료: {len(number_sets)}세트")
            return True

        except Exception as e:
            logger.error(f"구매 중 오류: {e}")
            return False

    def _switch_to_purchase_iframe(self):
        """구매 페이지의 번호 선택 iframe으로 전환한다 (있을 경우)."""
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    if self.driver.find_elements(By.CSS_SELECTOR, 'label[for^="check645num"]'):
                        logger.info("구매 iframe으로 전환됨")
                        return
                    self.driver.switch_to.default_content()
                except Exception:
                    self.driver.switch_to.default_content()
        except Exception:
            pass

    def _click_number_label(self, num: int):
        """번호 label을 클릭한다 (intercepted 시 JS click 폴백)."""
        label = self.driver.find_element(By.CSS_SELECTOR, f'label[for="check645num{num}"]')
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
            time.sleep(0.05)
            label.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", label)

    def _safe_click(self, by, value):
        """일반 click 실패 시 JS click으로 폴백한다."""
        el = self.driver.find_element(by, value)
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            time.sleep(0.05)
            el.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", el)

    def _close_popups(self):
        """사이트 팝업/모달을 닫는다."""
        try:
            popups = self.driver.find_elements(
                By.CSS_SELECTOR, ".popup_close, .close, .close-btn, .btn-close, .modal-close"
            )
            for popup in popups:
                try:
                    if popup.is_displayed():
                        popup.click()
                        time.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

        # alert 처리
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        except Exception:
            pass

    def close(self):
        """브라우저를 종료한다."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
