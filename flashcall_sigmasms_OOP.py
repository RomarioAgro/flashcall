# -*- coding: utf-8 -*-
import requests
from sys import argv
from typing import Tuple
import logging
from decouple import config as conf_token
import os
import http.client
import random

STATUS_DICT = {
    'pending': 'ожидает отправки',
    'paused': 'приостановлено',
    'processing': 'в обработке',
    'sent': 'отправлено',
    'delivered': 'ДОСТАВЛЕНО',
    'seen': 'просмотрено',
    'failed': 'ошибка при обработке/отправке сообщения'
}

if __name__ == '__main__':
    httpclient_logger = logging.getLogger("http.client")
    logging.basicConfig(
        filename='D:\\files\\' + os.path.basename(__file__)[:-3] + '_.log',
        filemode='a',
        level=logging.DEBUG,
        format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
        datefmt='%H:%M:%S')


def httpclient_logging_patch(level=logging.DEBUG):
    """Enable HTTPConnection debug logging to the logging framework"""

    def httpclient_log(*args):
        httpclient_logger.log(level, " ".join(args))

    # mask the print() built-in in the http.client module to use
    # logging instead
    http.client.print = httpclient_log
    # enable debugging
    http.client.HTTPConnection.debuglevel = 1


class SigmaSMS:
    """
    класс совершения звонков флешкол из SigmaSMS
    для проверки владельцев карт
    """

    def __init__(self, phone: str = '75555555555') -> None:
        """
        конструктор класса, храним телефон и
        генерим случайный проверочный код
        :param phone: str номер телефона в str
        """
        if phone.startswith('7') is True:
            self.phone = phone
        else:
            self.phone = '7' + phone[1:]
        self.code = str(random.randint(1000, 9999))  # генерируем случайный код
        self.answer = None

    def __str__(self) -> str:
        return 'оператор звонков СигмаСМС'

    def get_token(self) -> str:
        """
        получаем токен, токен мы на сайте сгенерировали
        :return:
        """
        token = conf_token('sigmasms_token', default=None)
        return token

    def call_password(self) -> Tuple:
        """
        метод совершения звонка сигмасмс
        :return: tuple(str, int) возвращаем кортеж из id звонка и проверочный код
        """
        self.code = str(random.randint(1000, 9999))  # генерируем случайный код, при каждом вызове будет новый
        url = 'https://online.sigmasms.ru/api/sendings'
        headers = {"Content-Type": "application/json",
                   "Authorization": self.get_token()}
        params = {"recipient": self.phone,
                  "type": "flashcall",
                  "payload": {"sender": "beletag",
                              "text": self.code}}
        logging.debug(params)
        logging.debug(headers)
        r = requests.post(url=url, headers=headers, json=params, verify=False, timeout=10)
        self.answer = r.json()
        logging.debug(r.text)
        logging.info(r.status_code)
        if r.status_code == 200:
            return r.status_code, self.code, 'Вызов сделан на номер'
        else:
            if self.phone[1] != '9':
                self.answer = 'ОШИБКА В НОМЕРЕ ТЕЛЕФОНА ' + self.phone + '\nНомер телефона не является мобильным.\nНеобходимо заполнить анкету и указать актуальную информацию'
            return r.status_code, self.code, r.text

    def status(self, id: str = '') -> str:
        """
        метод проверки статуса звонка по его ID
        если ID  не передаем, то узнаем статус последнего звонка
        :param id:
        :return:
        """
        # мало ли вдруг нам захочется узнать статус какого-нибудь прошлого звонка
        if id != '':
            url = 'https://online.sigmasms.ru/api/sendings/' + id
        else:
            url = 'https://online.sigmasms.ru/api/sendings/' + self.answer['id']

        headers = {"Content-Type": "application/json",
                   "Authorization": self.get_token()}

        logging.debug(headers)
        params = {
            'scope': 'full'
        }
        r = requests.get(url=url, headers=headers, params=params, verify=False)
        logging.debug(r.text)
        logging.info(r.status_code)
        if r.status_code != 200:
            return r.text
        return STATUS_DICT.get(r.json()['state']['status'], 'статус неизвестен')


def main():
    i_phone = argv[1]
    caller = SigmaSMS(phone=i_phone)
    caller.call_password()


if __name__ == '__main__':
    main()
