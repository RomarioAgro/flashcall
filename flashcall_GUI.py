import time
import PySimpleGUI as sg
import os
from sys import exit, argv
from decouple import config
import logging
from typing import Tuple, Any
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



CALL_TIMEOUT = 90  # таймаут между звонками
QT_ENTER_KEY1 = 'special 16777220'
QT_ENTER_KEY2 = 'special 16777221'
QT_ESCAPE = 'Escape:27'


def start_make_window(*inf_text_number):
    """
    функция создает объект с GUI окном
    inf_text_number tuple
    [0] - str с текстом в окне
    [1] - str номер телефона
    """
    sg.theme('SystemDefaultForReal')  # Add a touch of color
    # All the stuff inside your window.
    progressbar = [
        [sg.ProgressBar(CALL_TIMEOUT, orientation='h', size=(60, 30), key='progressbar')]
    ]

    outputwin = [
        [sg.Text(text=inf_text_number[0], size=(100, 10), key='output')]
    ]
    layout = [[sg.Frame('Progress', layout=progressbar)],
              [sg.Text(inf_text_number[1])],
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

    window = sg.Window('Сервис отправки звонка', layout, finalize=True, return_keyboard_events=True,
                       keep_on_top=True)  # создаем окно с гуем
    window['INPUT_ONE'].Widget.select_to(50)  # выделяем текст в input как-будто мышкой выделен
    return window


def qr_display_out(*numbers):
    """
    функция создает объект вывода QR кода на миниэкран
    ну и сразу что-то там выводит
    """
    qr_pict = qr_image(i_text='tel:+{0}'.format(numbers[0]))
    lcd_comm_mini_display = LcdCommRevB(com_port=COM_PORT,
                           display_width=320,
                           display_height=480)
    show_qr(lcd=lcd_comm_mini_display, image=qr_pict, qr_text="Для списания\n"
                                                 "бонусов совершите звонок\n"
                                                 "на номер: {0}\n"
                                                 "с номера: {1}".format(
        readable_number(numbers[0]), readable_number(numbers[1])))

    return lcd_comm_mini_display



def make_window(i_number: str = '55555555', callers: Tuple = None) -> int:
    """
    функция создания GUI формы звонка(смс) до покупателя, логика такая: делаем запрос на звонок, потом ожидаем 2 минуты,
    если звонок не пришел, то даем совершить еще один вызов
    :param i_number: str строка с номером через 79123456789
    :param i_caller: кортеж наших операторов: звонки смс, вот это вот все
    :param smssender: объект который посылает смс, если оператор не смог дозвониться
    :param understudy: (дублер) объект резервный звонок, если пуш не придет, тогда можно будет сделать звонок,
    если и он не придет, тогда можно сделать смс
    :return: int код возврата
    """
    logging.debug('старт формы GUI')
    mini_display = False
    status_code = 0
    count_calls = 0  #это наши этапы каскада
    i_caller = callers[0]
    # если у нас call_password о Newtel и есть миниэкран
    # то пытаемя вывести на него QR код с номером
    try:
        if type(i_caller).__name__ == 'NewtelCV':
            status_code, i_pin, info_text = i_caller.call_password(timeout=CALL_TIMEOUT)
            # вывод QR на минидисплее
            try:
                if check_com_port(COM_PORT):
                    lcd_comm = qr_display_out(i_pin['confirmationNumber'], i_pin['client_Number'])
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

    window = start_make_window(info_text, i_number)  #запускаем GUI окно
    progress_bar = window['progressbar']
    errorlevel = 0  # ошибка с которой выйдем
    s_time = int(time.time())  # время запуска звонка
    # количество совершенных звонков, после 1 звонка делаем доступной кнопку смс
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
        if count_calls == 1 and delta_time > CALL_TIMEOUT:
            # i_caller = callers[count_calls]
            window['Try call'].update(disabled=False)
            info_text = 'время для паузы вышло, можно сделать исходящий звонок'
            window['output'].update(value=info_text)
            s_time = int(time.time())
            print(info_text)
        if count_calls == 2 and delta_time > CALL_TIMEOUT:
            # i_caller = callers[count_calls]
            window['Send SMS'].update(disabled=False)
            info_text = 'время для паузы вышло, можно отправить смс'
            window['output'].update(value=info_text)
            s_time = int(time.time())
            print(info_text)
        delta_time = n_time - s_time  # разница между стартом и сейчас
        if delta_time > CALL_TIMEOUT:  # если прошло достаточно времени, то сделаем кнопку доступной
            count_calls += 1
        else:
            print('до следующего события {0} сек.'.format(CALL_TIMEOUT - delta_time))
        if count_calls > 2:
            count_calls = 1
        if type(i_caller).__name__ == 'NewtelCV':
            if push_status == 'notanswered':
                push_status = i_caller.status()
            if push_status == 'good':
                if mini_display:
                    show_qr(lcd=lcd_comm, image=None)
                logging.debug('NewTel call verification все ОК')
                break
            if push_status == 'bad':
                info_text = 'Покупатель отказался списывать бонусы, делайте звонок'
                logging.debug(info_text)
                window['output'].update(value=info_text)
                window['Try call'].update(disabled=False)
            if push_status == 'notanswered':
                window['output'].update(value=info_text)
        if event == '-Ok-':
            n_time = int(time.time())
            delta_time = n_time - s_time
            logging.debug('ввели =={0}=='.format(values['INPUT_ONE']))
            #  если код верный, то выходим из цикла
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
        if event == 'Try call':  #
            i = 0  # обнуляем прогрессбар
            i_caller = callers[count_calls]
            status_code, i_pin, info_text = i_caller.call_password()
            window['Try call'].update(disabled=True)
            window['output'].update(value='{0} {1} с НОВЫМ КОДОМ'.format(info_text, i_number))
            print('{0} {1} с НОВЫМ КОДОМ'.format(info_text, i_number))
            s_time = int(time.time())
        if event == 'Send SMS':  #
            i = 0  # обнуляем прогрессбар
            i_caller = callers[count_calls]
            status_code, i_pin, info_text = i_caller.call_password(i_pin='')
            window['Send SMS'].update(disabled=True)
            window['output'].update(value='{0} {1} с НОВЫМ КОДОМ'.format(info_text, i_number))
            print('{0} {1} с НОВЫМ КОДОМ'.format(info_text, i_number))
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
    return int код ошибки
    """
    logging.debug('*' * 50)
    phone = argv[1]
    caller = choice_caller(argv[2])(phone=phone)
    sigmasms = SigmaSMS(phone=phone)  ## несмотря на SMS в названии, это звонок
    newtel = Newtel(phone=phone)
    sendsms = SMStraffic(phone=phone)
    callers = (caller, sigmasms, sendsms)
    error = make_window(i_number=phone, callers=callers)
    logging.debug('*' * 50)
    exit(error)


if __name__ == '__main__':
    main()
