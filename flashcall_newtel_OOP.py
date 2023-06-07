import logging
from typing import Dict, Tuple
from decouple import config as conf_token
import requests
import datetime
import hashlib
from sys import argv
import json
import os
import http.client
import random
import time

STATUS_DICT = {
    "answered": 'отвечено',
    "busy": 'занято',
    "no answer": 'нет ответа',
    "no such number": 'номер не существует',
    "not available": 'сеть недоступна',
    "cancel": 'сеть недоступна'
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


class Newtel:
    """
    класс совершения звонков флешкол из NewTell
    для проверки владельцев карт
    """

    def __init__(self, phone: str = '') -> None:
        """
        конструктор класса, в нем храним телефон
        генерируем случайный код проверки
        """
        if phone.startswith('7') is True:
            self.phone = phone
        else:
            self.phone = '7' + phone[1:]
        self.answer = None
        self.callid = '123'
        # self.code = str(random.randint(1000, 9999))  #в ньютел это не используется, они сами код генерят

    def __str__(self) -> str:
        return 'оператор звонков Ньютел'

    def get_token(self, params: Dict = {}, method: str = '') -> str:
        """
        метод получения токена авторизации для совершения звонков
        :param params: dict тело запроса для звонка
        :param method: str метод запроса
        :return: str собственно токен
        """
        keyNewtel = conf_token('keyNewtel', default=None)  # Ключ CallPassword API для авторизации запросов
        writeKey = conf_token('writeKey', default=None)  # Ключ CallPassword API для подписи запросов
        pn = '\n'
        # метка времени запроса, формируется динамически клиентом при создании
        # запроса и передается в виде Unix timestamp. Представляет собой строку, состоящую из
        # 10-и десятичных цифр
        timenow = str(round(datetime.datetime.timestamp(datetime.datetime.now())))
        str_for_hash = (method + pn + timenow + pn + keyNewtel + pn + json.dumps(params) + pn + writeKey).encode(
            'utf-8')
        br_token_hash = hashlib.sha256(str_for_hash).hexdigest()
        token = 'Bearer ' + keyNewtel + timenow + br_token_hash
        return token

    def call_password(self) -> Tuple:
        """
        метод callpassword это когда звонок и код тебе диктует робот
        :return: tuple код ошибки, проверочный код сервис сам сгенерировал
        """
        url = 'https://api.new-tel.net/call-password/start-password-call'
        method = 'call-password/start-password-call'  # имя метода
        params = {
            "async": "1",
            "dstNumber": self.phone,
            "timeout": "20"
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.get_token(params=params, method=method)
        }
        logging.debug(params)
        logging.debug(headers)
        r = requests.post(url=url, headers=headers, json=params, verify=True, timeout=10)
        logging.debug(r.text)
        logging.info(r.status_code)
        self.answer = r.text
        if r.json()["data"]["result"] == 'error':
            if self.phone[1] != '9':
                self.answer = 'ОШИБКА В НОМЕРЕ ТЕЛЕФОНА ' + self.phone + '\nНомер телефона не является мобильным.\nНеобходимо заполнить анкету и указать актуальную информацию'
            return 'error', r.json()["data"]["message"], self.answer
        o_pin = r.json()["data"]["callDetails"]["pin"]
        self.callid = r.json()["data"]["callDetails"]["callId"]
        self.answer = r.json()
        return r.status_code, o_pin, r.text

    def status(self, callid: str = '') -> str:
        """
        метод получения статус звонка по его id
        :param callid: str id звонка
        :return: str статус звонка
        """
        if callid == '':
            callid = self.callid
        url = 'https://api.new-tel.net/call-password/get-password-call-status'
        method = 'call-password/get-password-call-status'  # имя метода
        params = {
            'callId': callid
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.get_token(params=params, method=method)
        }
        logging.debug(params)
        logging.debug(headers)
        r = requests.post(url=url, headers=headers, json=params, verify=True)
        logging.debug(r.text)
        logging.info(r.status_code)
        if r.status_code != 200:
            return r.text
        return STATUS_DICT.get(r.json()['data']['callDetails']['status'], 'статус неизвестен')



def main():
    i_phone = argv[1]
    caller = Newtel(phone=i_phone)
    caller.call_password()
    caller.status()


if __name__ == '__main__':
    main()
