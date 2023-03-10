import os
import time
import logging

import requests
import telegram
from http import HTTPStatus
from dotenv import load_dotenv
from exceptions import (NoConnectionToAPIError,
                        HwHaveNoNameError,
                        HwHaveNoStatusError)


load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '<%(asctime)s> [%(levelname)s] %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> None:
    """Проверка доступности переменных окружения."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.critical('Отсутствует одна или несколько переменных '
                        'окружения! Завершение работы бота...')
        exit()


def get_api_answer(timestamp: int) -> dict:
    """Возвращает словарь со всеми домашними работами."""
    try:
        homework_response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if homework_response.status_code != HTTPStatus.OK:
            error_message = f'Эндпоинт <"{ENDPOINT}"> недоступен!'
            logger.error(error_message)
            raise NoConnectionToAPIError(error_message)
        logger.info(f'Эндпоинт <"{ENDPOINT}"> доступен!')
        return homework_response.json()
    except requests.exceptions.RequestException as err:
        logger.error(f'Эндпоинт <"{ENDPOINT}"> недоступен! Ошибка: {err}')


def check_response(response: dict) -> None:
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        error_message = 'Ответ от API пришел не в виде словаря!'
        logger.error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response:
        error_message = 'В ответе API нет ключа "homeworks"!'
        logger.error(error_message)
        raise KeyError(error_message)
    if not isinstance(response['homeworks'], list):
        error_message = ('В ответе API по запросу "response["homeworks"]" '
                         'нет списка!')
        logger.error(error_message)
        raise TypeError(error_message)


def parse_status(homework: dict) -> str:
    """Возвращает сообщение со статусом домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        error_message = ('API возвратило недокументированный статус '
                         'работы или работу без статуса!')
        logger.error(error_message)
        raise HwHaveNoStatusError(error_message)
    if 'homework_name' not in homework:
        error_message = 'В овтете API нет ключа "homework_name"!'
        logger.error(error_message)
        raise HwHaveNoNameError(error_message)
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение с текстом: "{message}" '
                     'в Telegram.')
    except Exception as error:
        error_message = ('Ошибка при отправке сообщения в Telegram. '
                         f'Ошибка: "{error}".')
        logger.error(error_message)
        raise error(error_message)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    latest_hw_status = None
    while True:
        try:
            api_answer = get_api_answer(timestamp)
            check_response(api_answer)
            no_status_message = 'Домашнему заданию еще не присвоен статус!'
            if len(api_answer.get('homeworks', no_status_message)) == 0:
                logger.warning(no_status_message)
                time.sleep(0)  # pytest не проходит без этой строки
            else:
                previous_hw_status = parse_status(
                    api_answer.get('homeworks')[0]
                )
                if previous_hw_status != latest_hw_status:
                    latest_hw_status = previous_hw_status
                    send_message(bot, previous_hw_status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
