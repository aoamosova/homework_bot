import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (EmptyValueException, MissingDataException,
                        StatusCodeException)
from settings import ENDPOINT, HOMEWORK_STATUSES, RETRY_TIME

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)

PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID_TELEGRAM')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


def send_message(bot, message):
    """Отправляем сообщение в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение успешно отправлено')
    except telegram.TelegramError as error:
        logging.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(current_timestamp):
    """Проверяем ответ api."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        raise StatusCodeException('Ошибка при запросе к основному API')
    try:
        return response.json()
    except Exception as error:
        logging.error(f'Ошибка преобразования в json: {error}')


def check_response(response):
    """Проверяем данные в ответе."""
    if type(response) != dict:
        error = 'Тип ответа не словарь'
        raise TypeError(error)
    if 'homeworks' not in response:
        error = f'Отсутствуют данные в:{response}'
        raise MissingDataException(error)
    homework = response['homeworks']
    if type(homework) != list:
        error = 'Тип ответа не список'
        raise TypeError(error)
    if not homework:
        error = 'Список работ пуст'
        raise EmptyValueException(error)
    logging.info('Статус домашнего задания обновлен')
    return homework[0]


def parse_status(homework):
    """Запрашиваем статус работы."""
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа "homework_name" в ответе API')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('Нет ключа "homework_status" в ответе API')
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError('Нет ключа "homework_status" в словаре статусов')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Прверяем переменные окружения."""
    token_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    check_tokens = all(token_list)
    return check_tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error = 'Отсутствуют переменные окружения'
        logging.critical(error, exc_info=True)
        sys.exit
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)
            continue
        try:
            if check_response(response):
                homework = check_response(response)
                message = parse_status(homework)
                if message != status:
                    send_message(bot, message)
                    status = message
            current_timestamp = current_timestamp

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != status:
                send_message(bot, message)
                status = message
            logging.error(error, exc_info=True)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
