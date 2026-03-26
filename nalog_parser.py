import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional


from captcha_solver.solver import solve_captcha


logging.basicConfig(filename='nalog_parser.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class NalogClient:
    BASE_URL = "https://service.nalog.ru"

    def __init__(self):
        self.session = None
        self.is_initialized = False
        self.captcha_token = None
        self.request_count = 0
        self.max_requests_per_session = 50 
        
        self._reset_session()

    def _reset_session(self):
        logging.info("Пересоздание сессии (rotate session)...")
        if self.session:
            self.session.close()
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })
        self.is_initialized = False
        self.captcha_token = None
        self.request_count = 0

    def _ensure_session(self):
        if self.request_count >= self.max_requests_per_session:
            self._reset_session()

        if not self.is_initialized:
            try:
                self.session.get(f"{self.BASE_URL}/bi.do", timeout=10)
                self.is_initialized = True
            except Exception as e:
                logging.error(f"Ошибка инициализации: {e}")

    def get_data(self, inn: str, bik: str, timeout: int = 20) -> dict:
        self._ensure_session()
        self.request_count += 1        
        
        result = {"status": "error", "message": "Неизвестная ошибка", "data": None}

        payload = {
            'requestType': 'FINDPRS',
            'innPRS': inn,
            'bikPRS': bik,
            'captchaToken': self.captcha_token or ''
        }

        try:
            response = self.session.post(
                f"{self.BASE_URL}/bi2-proc.json", 
                data=payload, 
                timeout=(5, timeout) 
            )

            if response.status_code in [403, 500, 503]:
                self.is_initialized = False 
                self._reset_session() 
                return {"status": "server_error", "code": response.status_code, "message": "Сервер отклонил сессию"}

            if response.status_code == 200:
                return {"status": "success", "message": "OK", "data": response.json()}

            data = response.json()
            if response.status_code == 400:
                errors = data.get('ERRORS', {})
                if 'captcha' in errors:
                    new_token = self._try_solve_captcha()
                    if new_token:
                        self.captcha_token = new_token
                        return self.get_data(inn, bik, timeout)
                    return {"status": "captcha_failed", "message": "Не удалось разгадать капчу", "data": data}

                return {"status": "validation_error", "message": str(errors), "data": data}

        except requests.exceptions.Timeout:
            self._reset_session() 
            return {"status": "timeout", "message": f"Превышено время ожидания ({timeout}с)", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

        return result
    
    def _try_solve_captcha(self, max_attempts: int = 10) -> Optional[str]:
        for attempt in range(1, max_attempts + 1):
            logging.info(f"Попытка разгадать капчу №{attempt}...")
            
            try:
                resp = self.session.get(f"{self.BASE_URL}/static/captcha-dialog.html")
                soup = BeautifulSoup(resp.text, 'html.parser')
                captcha_token = soup.find("input", attrs={"name": "captchaToken"}).get('value')
                img_src = soup.find("form", id='frmCaptcha').find("img").get("src")

                img_url = self.BASE_URL + img_src

                response = self.session.get(img_url, stream=True)
                
                captcha_name = f'assets/unsolved_captchas/captcha_{int(time.time())}.jpg'

                with open(captcha_name, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

                captcha_text = solve_captcha(captcha_name)

                if not captcha_text:
                    logging.warning(f"Сервис не распознал капчу на попытке {attempt}. Пауза...")
                    time.sleep(2)
                    continue

                submit_resp = self.session.post(
                    f"{self.BASE_URL}/static/captcha-proc.json",
                    data={'captcha': captcha_text, 'captchaToken': captcha_token}
                )
                
                if submit_resp.status_code == 200:
                    logging.info("Капча успешно принята сервисом Налога.")
                    token = submit_resp.json() # Возвращаем подтвержденный токен
                    return token

                logging.warning(f"Налог отклонил текст капчи '{captcha_text}'.")
            except Exception as e:
                logging.error(f"Ошибка в цикле капчи: {e}")

            time.sleep(1)

        logging.error("Не удалось решить капчу после всех попыток.")
        return None


def main_loop(items: List[Tuple[str, str]]):
    client = NalogClient()

    for inn, bik in items:
        logging.info(f"--- Работа с ИНН {inn} ---")
        result = client.get_data(inn, bik)
        
        if result:
            logging.info(f"Данные получены успешно.")
        else:
            logging.error(f"Пропуск ИНН {inn} из-за ошибки.")
            
        time.sleep(random.uniform(2.5, 10.0))


if __name__ == "__main__":
    data_list = [
        ('3811449882', '045004641'),
        ('3811449582', '045004641'),
        ('7707083843', '045004641'),
        ('7707033893', '045004641'),
        ('7707083193', '045004641'),

    ]
    main_loop(data_list)
