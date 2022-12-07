import os
import sys
import time
import logging
import telegram
from dotenv import load_dotenv
import requests
from http import HTTPStatus


load_dotenv()


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


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения (токенов)."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат TELEGRAM_CHAT_ID."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        logging.error('Ошибка отправки сообщения')
    else:
        logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса.
    Возвращает ответ API в JSON-формате.
    """
    params = {'from_date': timestamp}
    try:
        logging.info('Попытка подключения к эндпоинту.')
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            response.raise_for_status()
        else:
            logging.info('Успешный запрос. Статус 200')
            return response.json()
    except Exception:
        message = 'Проблема с подключением к эндпоинту.'
        logging.error(message)
        raise ConnectionError(message)


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.
    Получает ответ API, приведенный к типам данных Python.
    """
    if not isinstance(response, dict):
        raise TypeError('Объект не является словарем')
    if 'homeworks' not in response:
        raise KeyError('Ключ homeworks не найден')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Список не найден')
    if not homeworks:
        raise IndexError('Список пуст')
    homework = homeworks[0]
    return homework


def parse_status(homework):
    """Извлекает из информации о домашней работе ее статус.
    Возвращает строку для отправки в Telegram, содержащую один
    из HOMEWORK_VERDICTS.
    """
    if not isinstance(homework, dict):
        raise TypeError('Неверный формат данных. Объект не является словарем.')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ homework_name. '
                       'Возможно, словарь пуст.')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Неизвестный статус домашней работы')
    verdict = HOMEWORK_VERDICTS[status]
    return ('Изменился статус проверки работы '
            f'"{homework_name}". {verdict}')


def main():
    """Основная логика работы бота."""
    logging.info('Старт')
    if not check_tokens():
        logging.critical('Ошибка проверки переменных окружения')
        sys.exit(0)
    timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(timestamp)
            logging.info('Получен ответ API')
            homework = check_response(response)
            if not homework:
                logging.info('Новых заданий нет')
            else:
                bot_message = parse_status(homework)
                send_message(bot, bot_message)
                # timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.critical(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[
            logging.FileHandler('output.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()
