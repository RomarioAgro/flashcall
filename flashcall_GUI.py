import time
import PySimpleGUI as sg
import os
from sys import exit, argv
from decouple import config
import logging
logging.basicConfig(
    filename='D:\\files\\' + argv[1] + '_' + os.path.basename(__file__)[:-3] + '_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')

try:
    from turing_smart_screen_python.library.lcd.lcd_comm_rev_b import LcdCommRevB
    from turing_smart_screen_python.qr import check_com_port, qr_image, show_qr
except Exception as exs:
    logging.debug(exs)
    print(exs)

COM_PORT = config('lcd_com', None)

os.chdir('d:\\kassa\\script_py\\flashcall\\')
from flashcall_newtel_OOP import Newtel
from newtel_cv import readable_number
from newtel_cv import NewtelCV
from flashcall_sigmasms_OOP import SigmaSMS
from flashcall_nothing_OOP import Nothing
from smstraffic_OOP import SMStraffic
from mts_push import Mts_push
from typing import Any


CALL_TIMEOUT = 90  # таймаут между звонками
QT_ENTER_KEY1 = 'special 16777220'
QT_ENTER_KEY2 = 'special 16777221'
QT_ESCAPE = 'Escape:27'
#TODO после деплоя и успешной работы в течении месяца почистить все "старые хвосты"


def make_window(i_number: str = '55555555', i_caller: object = None, smssender: object = None, understudy: object = None) -> int:
    """
    функция создания GUI формы звонка(смс) до покупателя, логика такая: делаем запрос на звонок, потом ожидаем 2 минуты,
    если звонок не пришел, то даем совершить еще один вызов
    :param i_number: str строка с номером через 79123456789
    :param i_caller: объект который звонит, разные оператор могут быть, по-умолчанию это будет push мтс
    :param smssender: объект который посылает смс, если оператор не смог дозвониться
    :param understudy: (дублер) объект резервный звонок, если пуш не придет, тогда можно будет сделать звонок,
    если и он не придет, тогда можно сделать смс
    :return: int код возврата
    """
    logging.debug('старт формы GUI')
    list_providers = [i_caller, understudy, smssender]
    mini_display = False
    for prov in list_providers:
        i_caller = prov
        try:
            if type(i_caller).__name__ == 'NewtelCV':
                status_code, i_pin, info_text = i_caller.call_password(timeout=CALL_TIMEOUT)
                # вывод QR на минидисплее
                try:
                    if check_com_port(COM_PORT):
                        qr_pict = qr_image(i_text='tel:+{0}'.format(i_pin['confirmationNumber']))
                        lcd_comm = LcdCommRevB(com_port=COM_PORT,
                                               display_width=320,
                                               display_height=480)
                        show_qr(lcd=lcd_comm, image=qr_pict, qr_text="Для списания\n"
                                                                     "бонусов совершите звонок\n"
                                                                     "на номер: {0}\n"
                                                                     "с номера: {1}".format(
                            readable_number(i_pin['confirmationNumber']), readable_number(i_pin['client_Number'])))
                        mini_display = True
                except Exception as exc:
                    logging.error(exc)
            else:
                status_code, i_pin, info_text = i_caller.call_password()
        except Exception as exc:
            info_text = 'ошибка отправки запроса'
            logging.debug(exc)
            print(exc)
        if type(i_caller).__name__ == 'NewtelCV':
            info_text = '{0}'.format(info_text)
        else:
            info_text = '{0} {1}'.format(info_text, i_number)
        if status_code != 200:
            info_text = 'ОШИБКА\n' + str(i_caller.answer)
            logging.debug(info_text)
        else:
            break

    sg.theme('SystemDefaultForReal')  # Add a touch of color
    # All the stuff inside your window.
    progressbar = [
        [sg.ProgressBar(CALL_TIMEOUT, orientation='h', size=(60, 30), key='progressbar')]
    ]

    outputwin = [
        [sg.Text(text=info_text, size=(100, 10), key='output')]
    ]
    layout = [[sg.Frame('Progress', layout=progressbar)],
              [sg.Text(i_number)],
              [sg.Text('введите проверочный код'),
               sg.InputText(key='INPUT_ONE',
                            default_text='сюда надо ввести проверочный код',
                            do_not_clear=True,
                            focus=True),
               sg.Button(button_text='Ok', key='-Ok-')],
              [sg.Button(button_text='Try call', disabled=True),
               sg.Button(button_text='Send SMS', disabled=True),
               [sg.Frame('Output', layout=outputwin)],
               sg.Button(button_text='Cancel'),
               sg.Button(button_text='Статус')]]

    # Create the Window
    # Event Loop to process "events" and get the "values" of the inputs

    s_time = int(time.time())  # время запуска звонка
    errorlevel = 0  # ошибка с которой выйдем
    window = sg.Window('Сервис отправки звонка', layout, finalize=True, return_keyboard_events=True,
                       keep_on_top=True)  # создаем окно с гуем

    progress_bar = window['progressbar']
    window['INPUT_ONE'].Widget.select_to(50)  # выделяем текст в input как-будто мышкой выделен
    # количество совершенных звонков, после 2-х звонков делаем доступной кнопку смс
    count_calls = 1
    i = 0  # изменение прогрессбара
    push_status = 'notanswered'
    while True:
        event, values = window.read(timeout=1500)  # ждем ввода, это миллисекунды
        if event in ('\r', QT_ENTER_KEY1, QT_ENTER_KEY2):  # отрабатываем ввод с клавиатуры
            event = '-Ok-'
        if event == QT_ESCAPE:
            errorlevel = 2000
            break
        n_time = int(time.time())  # время сейчас
        delta_time = n_time - s_time  # разница между стартом и сейчас
        if delta_time > CALL_TIMEOUT:  # если прошло достаточно времени, то сделаем кнопку доступной
            # window['Try call'].update(disabled=False)
            window['Send SMS'].update(disabled=False)
            window['output'].update(value='время для паузы вышло, можно сделать смс')
            print('время для паузы вышло, можно сделать смс')
        else:
            print('до следующего события {0} сек.'.format(CALL_TIMEOUT - delta_time))
        if type(i_caller).__name__ == 'Mts_push':
            if push_status == 'notanswered':
                push_status = i_caller.status()
            if push_status == 'good':
                logging.debug('Mts_push все ОК')
                break
            if push_status == 'bad':
                logging.debug('Покупатель отказался списывать бонусы, делайте звонок')
                window['output'].update(value='Покупатель отказался списывать бонусы, делайте звонок')
                # if count_calls < 2:
                #     print(f'count_calls={count_calls}')
                #     window['Try call'].update(disabled=False)
            if push_status == 'notanswered':
                window['output'].update(value='Статус PUSH-сообщения пока неизвестен')

        if type(i_caller).__name__ == 'NewtelCV':
            if push_status == 'notanswered':
                push_status = i_caller.status()
            if push_status == 'good':
                if mini_display:
                    show_qr(lcd=lcd_comm, image=None)
                logging.debug('NewTel call verification все ОК')
                break
            if push_status == 'bad':
                logging.debug('Покупатель отказался списывать бонусы, делайте звонок')
                window['output'].update(value='Покупатель отказался списывать бонусы, делайте смс')
                # if count_calls < 2:
                #     print(f'count_calls={count_calls}')
                window['Send SMS'].update(disabled=False)
                # window['Try call'].update(disabled=False)
            if push_status == 'notanswered':
                window['output'].update(value=info_text)
        if event == '-Ok-':
            n_time = int(time.time())
            delta_time = n_time - s_time
            logging.debug('ввели =={0}=='.format(values['INPUT_ONE']))
            #  если код верный, то выходим из цикла
            if type(i_caller).__name__ == 'Mts_push':
                mts_code = values['INPUT_ONE']
                print(mts_code)
                push_status = i_caller.status(code=mts_code)
                if push_status == 'good':
                    logging.debug('Mts_push все ОК')
                    break
            if values['INPUT_ONE'] == str(i_pin):
                print(values['INPUT_ONE'])
                break
            else:
                window['output'].update(value='вы ввели "{1}" - это не верный код,\n'
                                              'до следующего события {0} секунд'.
                                        format(CALL_TIMEOUT - delta_time, values['INPUT_ONE']))
                print('вы ввели "{1}" - это не верный код,\nдо следующего события {0} секунд'
                      .format(CALL_TIMEOUT - delta_time, values['INPUT_ONE']))
                window['INPUT_ONE'].Update('сюда надо ввести проверочный код')
                window['INPUT_ONE'].Widget.select_to(50)
        n_time = int(time.time())
        delta_time = n_time - s_time
        if event == 'Send SMS':  #
            i = 0  # обнуляем прогрессбар
            i_caller = smssender
            status_code, i_pin, info_text = i_caller.call_password(i_pin='')
            window['output'].update(value='{0} {1} с НОВЫМ КОДОМ'.format(info_text, i_number))
            print('{0} {1} с НОВЫМ КОДОМ'.format(info_text, i_number))
            window['Try call'].update(disabled=True)
            count_calls += 1
            window['Send SMS'].update(disabled=True)
            s_time = int(time.time())
        if event == 'Статус':
            window['output'].update(value='статус звонка на номер {0}: {1}'.format(i_number, i_caller.status()))
        if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
            errorlevel = 2000
            break
        progress_bar.UpdateBar(i + 1)
        i += 1
    window.close()
    if mini_display:
        show_qr(lcd=lcd_comm, image=None)
    logging.debug('финиш формы GUI, код выхода {0}'.format(errorlevel))
    return errorlevel


def choice_caller(in_caller) -> Any:
    """
    функция выбора класса оператора звонка
    :param in_caller: str строковое имя оператора
    :return: объект оператора
    """
    dict_caller = {
        'sigmasms': SigmaSMS,
        'newtel': Newtel,
        'newtel_cv': NewtelCV,
        'nothing': Nothing,
        'smstraffic': SMStraffic,
        'mtspush': Mts_push
    }
    return dict_caller.get(in_caller, Nothing)


def main():
    """
    скрипт организации проверочных звонков с кодом
    чтоб девки звонками не спамили сделал таймаут между звонками 1.5 минуты
    :return:
    """
    logging.debug('*' * 50)
    phone = argv[1]
    caller = choice_caller(argv[2])(phone=phone)
    sigmasms = SigmaSMS(phone=phone)
    sendsms = SMStraffic(phone=phone)
    error = make_window(i_number=phone, i_caller=caller, smssender=sendsms, understudy=sigmasms)
    logging.debug('*' * 50)
    exit(error)


if __name__ == '__main__':
    main()
