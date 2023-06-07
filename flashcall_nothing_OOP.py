import logging
from typing import Tuple
from sys import argv
import os
import random

if __name__ == '__main__':
    logging.basicConfig(
        filename='D:\\files\\' + os.path.basename(__file__)[:-3] + '_.log',
        filemode='a',
        level=logging.DEBUG,
        format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
        datefmt='%H:%M:%S')


class Nothing:
    """
    класс-пустышка для отладки логики работы GUI совершения звонков
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
        self.code = str(random.randint(1000, 9999))
        self.answer = None

    def __str__(self) -> str:
        return 'класс-пустышка для отладки'

    def call_password(self) -> Tuple:
        """
        метод callpassword это когда звонок и код тебе диктует робот
        :return: tuple код ошибки, проверочный код сервис сам сгенерировал
        """
        self.code = str(random.randint(1000, 9999))
        logging.debug(self.__str__())
        logging.debug('{0} код мы загадали'.format(self.code))
        o_status_code = 200
        o_pin = self.code
        return o_status_code, o_pin, 'метод-пустышка не делает ничего'

    def status(self) -> str:
        return 'тест запущен'


def main():
    i_phone = argv[1]
    caller = Nothing(phone=i_phone)
    caller.call_password()


if __name__ == '__main__':
    main()
