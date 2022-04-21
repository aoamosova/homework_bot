import os
import telegram
import requests
import time
import logging
import sys
from exceptions import (MissingDataException, EmptyValueException,
                        StatusCodeException)
from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)

PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID_TELEGRAM')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение в чат."""
    text = message
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text)
        logging.info('Сообщение успешно отправлено')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(current_timestamp):
    """Проверяем ответ api."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    raise StatusCodeException('Ошибка при запросе к основному API')


def check_response(response):
    """Проверяем данные в ответе."""
    if not response['homeworks']:
        error = f'Отсутствуют данные в:{response}'
        raise MissingDataException(error)
    homework = response['homeworks']
    if not homework:
        error = f'Список {homework[0]} пуст'
        raise EmptyValueException(error)
    logging.info('Статус домашнего задания обновлен')
    return homework[0]


def parse_status(homework):
    """Запрашиваем статус работы."""
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа "homework_name" в ответе API')
    homework_name = homework['homework_name']
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа "homework_status" в ответе API')
    homework_status = homework['status']
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
    while check_tokens() is True:
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
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != status:
                send_message(bot, message)
                status = message
            logging.error(error, exc_info=True)
            time.sleep(RETRY_TIME)
        finally:
            logging.debug('Статус не обновился')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
