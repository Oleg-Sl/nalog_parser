import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional


from captcha_solver.solver import solve_captcha


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class NalogClient:
    BASE_URL = "https://service.nalog.ru"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        })
        self.is_initialized = False

        self.captcha_token = None

    def _ensure_session(self):
        if not self.is_initialized:
            logging.info("Открытие стартовой страницы для инициализации сессии...")
            try:
                self.session.get(f"{self.BASE_URL}/bi.do", timeout=10)
                self.is_initialized = True
            except Exception as e:
                logging.error(f"Ошибка инициализации: {e}")

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
                print('captcha_text = ', captcha_text)
                # captcha_text = input('Введите решение капчи: ')

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

    # {"ERROR":"-","ERRORS":{"captcha":["Требуется ввести цифры с картинки (123, .45)"]},"STATUS":400}
    # {"ERROR":"-","ERRORS":{"innPRS":["Некорректный ИНН ЮЛ"]},"STATUS":400}
    def get_data(self, inn: str, bik: str) -> Optional[dict]:
        self._ensure_session()

        print('self.captcha_token = ', self.captcha_token)
        payload = {
            'requestType': 'FINDPRS',
            'innPRS': inn,
            'bikPRS': bik,
            'captchaToken': self.captcha_token or ''
        }

        try:
            response = self.session.post(f"{self.BASE_URL}/bi2-proc.json", data=payload, timeout=15)
            data = response.json()
            if response.status_code == 400 and 'ERRORS' in data and 'captcha' in data['ERRORS']:
                logging.warning(f"Требуется капча для ИНН {inn}...")
                new_token = self._try_solve_captcha()
                self.captcha_token = new_token
                if new_token:
                    return self.get_data(inn, bik)
                return None
            elif response.status_code == 400:
                logging.warning(f"Требуется капча для ИНН {inn}...")
                return data

            return data
        
        except Exception as e:
            logging.error(f"Ошибка запроса для {inn}: {e}")
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
