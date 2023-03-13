import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (HwHaveNoNameError, HwHaveNoStatusError,
                        JsonDecodeError, NoConnectionToAPIError,
                        SendMessageError)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(stream=sys.stdout)
file_handler = logging.FileHandler(
    filename=f'{__file__}.log',
    mode='a',
    encoding='utf-8'
)
formatter = logging.Formatter(
    '<%(asctime)s> [%(levelname)s] %(message)s'
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

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

UNAVAILABLE_ENDPIONT_ERROR = f'Эндпоинт <"{ENDPOINT}"> недоступен!'
AVAILABLE_ENDPOINT_MESSAGE = f'Эндпоинт <"{ENDPOINT}"> доступен!'
NO_TOKEN_ERROR = ('Отсутствует одна или несколько переменных '
                  'окружения! Завершение работы бота...')
WRONG_RESPONSE_ERROR = 'Ответ от API пришел не в виде словаря!'
NO_KEY_ERROR = 'В ответе API нет нужного ключа!'
NO_LIST_ERROR = ('В ответе API по запросу "response["homeworks"]" '
                 'нет списка!')
UNKNOWN_STATUS_ERROR = ('API возвратило недокументированный статус '
                        'работы или работу без статуса!')
SEND_MESSAGE_ERROR = 'Ошибка при отправке сообщения в Telegram!'
SUCCESS_SENT_MESSAGE = 'Бот успешно отправил сообщение в Telegram!'
DECODE_ERROR = 'Ошибка преобразования к типу данных Python!'
HW_HAVE_NO_STATUS = 'Домашнему заданию еще не присвоен статус!'


def check_tokens() -> None:
    """Проверка доступности переменных окружения."""
    empty_tokens = {}
    for token in ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']:
        if globals().get(token) is None:
            empty_tokens[token] = None
    if len(empty_tokens) != 0:
        logger.critical(f'{NO_TOKEN_ERROR}. {empty_tokens}')
        sys.exit(NO_TOKEN_ERROR)


def get_api_answer(timestamp: int) -> dict:
    """Возвращает словарь со всеми домашними работами."""
    try:
        homework_response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if homework_response.status_code != HTTPStatus.OK:
            logger.error(UNAVAILABLE_ENDPIONT_ERROR)
            raise NoConnectionToAPIError(UNAVAILABLE_ENDPIONT_ERROR)
        else:
            try:
                return homework_response.json()
            except json.JSONDecodeError:
                raise JsonDecodeError(DECODE_ERROR)
            finally:
                logger.info(AVAILABLE_ENDPOINT_MESSAGE)
    except requests.exceptions.RequestException as err:
        logger.error(f'{UNAVAILABLE_ENDPIONT_ERROR}. Ошибка: {err}')


def check_response(response: dict) -> None:
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(WRONG_RESPONSE_ERROR)
    if 'homeworks' not in response:
        raise KeyError(NO_KEY_ERROR)
    if not isinstance(response['homeworks'], list):
        raise TypeError(NO_LIST_ERROR)


def parse_status(homework: dict) -> str:
    """Возвращает сообщение со статусом домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise HwHaveNoStatusError(UNKNOWN_STATUS_ERROR)
    if 'homework_name' not in homework:
        raise HwHaveNoNameError(NO_KEY_ERROR)
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError:
        logger.error(SEND_MESSAGE_ERROR)
        raise SendMessageError(SEND_MESSAGE_ERROR)
    else:
        logger.debug(SUCCESS_SENT_MESSAGE)


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
            if len(api_answer.get('homeworks', HW_HAVE_NO_STATUS)) == 0:
                logger.warning(HW_HAVE_NO_STATUS)
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
