# -*- coding: utf-8 -*-
import datetime
import requests
from sys import argv
from typing import Tuple
import logging
from decouple import config as conf_token
import os
import http.client
import random
import re


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


class SMStraffic:
    """
    класс отправки смс из SMStraffic
    для проверки владельцев карт
    """

    def __init__(self, phone: str = '75555555555', message: str = 'Код авторизации ', individual_messages: int = 0,
                 start: str = '') -> None:
        """
        конструктор класса, храним телефон и
        генерим случайный проверочный код
        :param phone: str номер телефона в str
        message: str текст сообщения
        individual_messages:int 1 если у нас индивидуальные сообдщения, 0 если одинаковые
        start:str дата и время отправки "ГГГГММ-ДД ЧЧ:ММ:СС", если пусто, то немедленно
        """
        if phone.startswith('7') is True:
            self.phone = phone
        else:
            self.phone = '7' + phone[1:]
        self.code = str(random.randint(1000, 9999))  #генерируем случайный код
        self.login = conf_token('smstraffic_login', None)
        self.pas = conf_token('smstraffic_pass', None)
        self.messagestr = message
        self.individual_messages = individual_messages
        self.start_date = start
        self.answer = None

    def __str__(self) -> str:
        return 'оператор СМС SMSTraffic'

    def call_password(self, i_pin: str = '') -> Tuple:
        """
        метод отправки смс, если вызываем без пин, то генерирует сам
        :param i_pin:
        individual_messages: int 0 если все сообзщения одинаковые, 1 у каждого свое сообщение
        st_date: str дата и время отправки, если пусто, то отправка немедленно
        :return:
        """
        logging.debug('----------'+i_pin+'----------')
        if i_pin == '':
            self.code = str(random.randint(1000, 9999))  # генерируем случайный код, при каждом вызове будет новый
        else:
            self.code = i_pin
        url = 'https://api.smstraffic.ru/multi.php'
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.individual_messages == 0:
            message = self.messagestr + self.code
        else:
            message = ''
        params = {'login': self.login,
                  'password': self.pas,
                  'rus': 5,
                  'message': message,
                  'phones': self.phone,
                  'want_sms_ids ': '1',
                  'originator': 'CleverWear',
                  'individual_messages': self.individual_messages,
                  'start_date': self.start_date}
        logging.debug(params)
        logging.debug(headers)
        if self.phone[1] != '9':
            self.answer = 'ОШИБКА В НОМЕРЕ ТЕЛЕФОНА ' + self.phone + '\nНомер телефона не является мобильным.\nНеобходимо заполнить анкету и указать актуальную информацию'
            return 'error', self.code, self.answer
        try:
            r = requests.post(url=url, headers=headers, params=params, verify=True, timeout=10)
        except Exception as exs:
            logging.error(exs)
            return 'error', self.code, exs
        logging.debug(r.text)
        logging.info(r.status_code)
        return r.status_code, self.code, r.text

    def status(self):
        return 'not error'


def main():
    i_phone = argv[1]
    caller = SMStraffic(phone=i_phone)
    caller.call_password()
    caller.status()

if __name__ == '__main__':
    main()