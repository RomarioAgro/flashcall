"""
скрипт отправки пушей через сервера мтс
"""
import requests
from decouple import config
import uuid
from jwcrypto import jwk, jwt
import json
from sys import argv
import logging
import os
import http.client
from typing import Tuple
import random


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


class Mts_push:


    def __init__(self, phone: str = '55555555') -> None:
        """
        конструктор класса отправителя пушей через мтс
        :param phone: str номер телефона куда хотим отправить пуш
        :param mts_client_notification_token: str токен, с которым мтс пришлет ответ на наш сервер
        correlation_id: str Уникальный сквозной идентификатор для всех транзакций пользователя.
        """
        if phone.startswith('7') is True:
            self.phone = phone
        else:
            self.phone = '7' + phone[1:]
        self.client_id = config('mts_client_id', None)
        self.secret = config('mts_secret', None)
        self.kid = config('mts_kid', None)
        self.url = config('mts_push_url', None)
        self.aud = config('mts_aud', None)
        self.mts_notification_url = config('mts_notification_url', None)
        self.mts_status_url = config('mts_status_url', None)
        self.mts_client_notification_token = 'nothing'
        self.correlation_id = None
        self.answer = None

    def __str__(self):
        return 'метод отправки пушей через МТС'

    def request_si_auth(self) -> str:
        """
        генерация обязательный параметр запроса /si-authorize
        :return: str JWT токен
        """
        header = {
            'alg': 'RS256',
            'kid': self.kid,
            'typ': 'JWT'
        }
        id_token = str(uuid.uuid4())
        payload = {
            'response_type': 'mc_si_async_code',
            'client_id': self.client_id,
            'scope': 'openid mc_authn',
            'version': 'mc_si_r2_v1.0',
            'nonce': id_token,
            'login_hint': 'MSISDN:' + self.phone,
            'acr_values': '2 3',
            'iss': self.client_id,
            'aud': self.aud,
            'notification_uri': self.mts_notification_url,
            'client_notification_token': self.mts_client_notification_token,
            'correlation_id': self.correlation_id
        }
        logging.debug(payload)
        with open('sig_key.json', 'r', encoding='utf-8') as fjson:
            key_sig = json.load(fjson)
        key_sig_str = json.dumps(key_sig)
        header_json = json.dumps(header)
        payload_json = json.dumps(payload)
        private_key = jwk.JWK.from_json(key_sig_str)
        jwt_token = jwt.JWT(header=header_json, claims=payload_json)
        jwt_token.make_signed_token(private_key)
        return jwt_token.serialize()

    def call_password(self) -> Tuple:
        """
        типа вызываем пуш
        :return:
        """
        self.correlation_id = str(uuid.uuid4())
        i_pin = random.randint(1000, 9999)
        headers = {"Content-Type": "application/json"}
        param = {
            "client_id": self.client_id,
            "response_type": "mc_si_async_code",
            "scope": "openid mc_authn",
            "request": self.request_si_auth(),
            "correlation_id": self.correlation_id
        }
        r = requests.post(url=self.url, headers=headers, json=param, timeout=10)
        logging.debug(str(r.status_code) + '*' * 5 + r.text)
        logging.debug('pin = {0}'.format(i_pin))
        self.answer = r.json()
        if r.status_code == 200:
            return_text = 'PUSH-запрос отправлен на номер'
        else:
            return_text = r.text
        return r.status_code, i_pin, return_text

    def status(self, code=None) -> str:
        """
        метод узнаем статус отправки нашего пуша
        param code str у мтс, есть смс нотификация, если не прошел пуш, то они высылают код в смс
        и вот этот код надо им будет посылать обратно
        :return: str результат отправки пуша
        """
        r = requests.get(url=self.mts_status_url, params=self.answer, timeout=10)
        logging.debug(r.text)
        print(r.json())
        result = r.json().get('result', None)
        smsotp_endpoint = None
        if result and result != 'Error! Record not found':
            result_dict = json.loads(result)
            smsotp_endpoint = result_dict.get('SMSOTP_ENDPOINT', None)
        if code and smsotp_endpoint:
            headers_smsotp = {
                "Content-Type": "application/json"
            }
            param_smsotp = {
                "verify_code": code
            }
            logging.debug('PUSH не удался, переходим к SMSOTP, CODE={2} H={0}, PARAM={1}'.format(headers_smsotp, param_smsotp, code))
            r_smsotp = requests.post(url=smsotp_endpoint, json=param_smsotp, headers=headers_smsotp)
            logging.debug('результат SMSOTP = {0}, ответ сервера {1}'.format(r_smsotp.status_code, r_smsotp.text))
            if r_smsotp.status_code == 200 or r_smsotp.status_code == 204:
                return 'good'
        if r.json()['result'] == 'Error! Record not found':
            return 'notanswered'
        if 'cancel' in r.json()['result']:
            return 'bad'
        if 'success' in r.json()['result']:
            return 'good'



def main():
    i_mts = Mts_push(phone=argv[1])
    i_mts.call_password()
    while True:
        i_mts.status()


if __name__ == '__main__':
    main()