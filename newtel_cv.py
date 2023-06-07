import logging
from typing import Dict, Tuple
from flashcall_newtel_OOP import Newtel
from decouple import config as conf_token
import requests
from sys import argv
import os
import http.client
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


def readable_number(phone: str = '') -> str:
    """
    небольшая функция которая делает из телефонного номера
    человекочитаемый формат
    :param phone: str номер телефона в международном формате
    :return: str номер телефона читаемый
    """
    o_phone = '+' + phone[0] + '(' + phone[1:4] + ')-' + phone[4:7] + '-' + phone[7:]
    return o_phone


class NewtelCV(Newtel):
    """
    класс аутентификации из NewTell, только тут мы даем человеку номер
    и ждем когда он на этот номер сделает звонок
    """

    def __init__(self, phone: str = '') -> None:
        super().__init__(phone)

    def __str__(self) -> str:
        return 'оператор звонков Ньютел call verification'

    def call_password(self, timeout: int = 90) -> Tuple:
        """
        метод верификации, когда юзер звонит на сервер на тот номер, который ему сообщили
        :return:
        """
        url = 'https://api.new-tel.net/call-verification/start-inbound-call-waiting'
        method = 'call-verification/start-inbound-call-waiting'  # имя метода
        params = {
            "callbackLink": "https://beletag.com/rest/call-password/",
            "clientNumber": self.phone,
            "timeout": timeout
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.get_token(params=params, method=method)
        }
        r = requests.post(url=url, headers=headers, json=params, verify=True, timeout=20)
        logging.debug(r.text)
        logging.info(r.status_code)
        self.callid = r.json()["data"]["callDetails"]["callId"]
        if r.status_code == 200:
            i_phone = readable_number(phone=r.json()['data']['callDetails']['confirmationNumber'])
            return_text = 'Покупатель должен позвонить на номер {0}'.format(i_phone)
            out_params = {
                'auth_req_id': r.json()['data']['callDetails']['callId'],
                'client_Number': r.json()['data']['callDetails']['clientNumber'],
                "confirmationNumber": r.json()['data']['callDetails']['confirmationNumber']
            }
            self.answer = out_params

        else:
            return_text = r.text
            out_params = {
                'auth_req_id': '',
                'client_Number': '',
                "confirmationNumber": ''
            }
        logging.debug(return_text)
        return r.status_code, out_params, return_text

    def status(self):
        """
        метод проверки статуса звонка call_verification
        :return:
        """
        url = conf_token('mts_status_url', None)
        r = requests.get(url=url, params=self.answer)
        logging.debug(r.json())
        if r.json()['result'] == 'Error! Record not found':
            return 'notanswered'
        if 'cancel' in r.json()['result']:
            return 'bad'
        if 'success' in r.json()['result']:
            return 'good'


def main():
    i_phone = argv[1]
    caller = NewtelCV(phone=i_phone)
    cv_params = caller.call_password()
    while True:
        ans = caller.status()
        print(ans[1])
        time.sleep(2)
        print('1')


if __name__ == '__main__':
    main()
