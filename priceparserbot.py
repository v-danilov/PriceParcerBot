import requests
from bs4 import BeautifulSoup
import datetime
import sched, time
import os
import json
import pymysql
from threading import Thread, Lock


class DataBase:
    def __init__(self):
        conn = pymysql.connect(host="progist.pro", user="progist_marzi", db="progist_marzi", passwd="KatyaKlapp911",
                               charset="utf8",
                               autocommit=True)
        self.cursor = conn.cursor()

    def check(self):
        try:
            self.cursor.execute('SELECT version()')
        except:
            conn = pymysql.connect(host="progist.pro", user="progist_marzi", db="progist_marzi", passwd="KatyaKlapp911",
                                   charset="utf8",
                                   autocommit=True)
            self.cursor = conn.cursor()

    def get(self):
        global lock
        lock.acquire()
        self.check()
        self.cursor.execute('select * from bot')
        ids = self.cursor.fetchall()
        ids_new = []
        for i in ids:
            id, =i
            ids_new.append(id)
        lock.release()
        return ids_new

    def remove(self,_id):
        self.check()
        self.cursor.execute('delete from bot where id = {}'.format(_id))

    def add(self, _id):
        self.check()
        self.cursor.execute('insert into bot set id = {} on duplicate key update id = id'.format(_id))



class BotHandler:

    def __init__(self, _token):
        self.token = _token
        self.api_url = "https://api.telegram.org/bot{}/".format(_token)

    def get_updates(self, offset=None, timeout=30):
        method = 'getUpdates'
        params = {'timeout': timeout, 'offset': offset}
        resp = requests.get(self.api_url + method, params)
        result_json = resp.json()['result']
        return result_json

    def send_message(self, _chat_id, _text):
        params = {'chat_id': _chat_id, 'text': _text,'parse_mode':'HTML', 'reply_markup':json.dumps({'keyboard':[['Подписаться','Отписаться'], ['Текущая цена'],['Помощь']],'resize_keyboard':True}).encode('utf-8')}
        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params)
        return resp

    def get_last_update(self):
        get_result = self.get_updates()

        if len(get_result) > 0:
            last_update = get_result[-1]
        else:
            last_update = None
        return last_update

def get_html(_url):
    resp = requests.get(_url)
    return resp.text

def get_price(_soup):
    div_container = _soup.find_all('div',class_='product-intro__purchase')
    
    for div in div_container:
        div_price = div.find_all('div', class_='product-price__main')
        for span in div_price:
            price = span.getText().strip().replace(' ', '')[:-1]
            return int(price)

def get_availability(_soup):
    div_container = _soup.find_all('div',class_='product-actions__text--unavailable')

    for div in div_container:
        if(div.text.strip() == "Спб (м. Площадь Восстания)"):
            return False
    return True


def check_price():
    adress = 'https://www.wellfix.ru/shop/product/displei-oneplus-x-s-tachskrinom-chernyi'
    soup = BeautifulSoup(get_html(adress), "html5lib")
    
    new_price = get_price(soup)
    inStock   = get_availability(soup)  

    if(new_price < price):
        output = "🎉СКИДО_ОНЧИК ПОДЪЕХАЛ🎉! Текущая цена: <b>{}</b> рублёу!".format(new_price)
    else:
        output = "Всё ещё <b>{}</b> рублёу... \U0001F610 Ожидаем.".format(new_price)
        
    output +="\n<b>Наличие:</b> "
    output += "\U00002705" if inStock else "\U000026D4"
    return output

def update(new_offset):

    price_bot.get_updates(new_offset)
    last_update = price_bot.get_last_update()
            
    if last_update is not None:
        last_update_id = last_update['update_id']    
        last_chat_id = last_update['message']['chat']['id']
        last_chat_text = last_update['message']['text']

        if last_chat_text in ['/start', "Подписаться"] :
            if last_chat_id not in db.get():
                db.add(last_chat_id)
                price_bot.send_message(last_chat_id, "\U00002705 Вы успешно подписаны на ежедневную рассылку! Информация обновляется в \U0001F559 10 часов 5 минут \U0001F559. Чтобы отписаться от рассылки отправьте \"/stop\"")
                price_bot.send_message(last_chat_id, check_price())
            else:
                price_bot.send_message(last_chat_id, 'Ты уже подписан. Попробуй это: /help')

        elif last_chat_text in ['/stop', "Отписаться"]:
            if last_chat_id in db.get():
                db.remove(last_chat_id)
                price_bot.send_message(last_chat_id, "Вы отписались от рассылки. Пок \U0001F618")

        elif last_chat_text in ['/info', 'Текущая цена']:
            price_bot.send_message(last_chat_id, check_price())

        elif last_chat_text in ['/help', 'Помощь']:
            price_bot.send_message(last_chat_id, 'Возможные команды: /start - подписаться на ежедневную рассылку, /stop - отписаться от рассылки, /info - получить свежую инфу')
            
        new_offset = last_update_id + 1
        return new_offset

def notify():
        now = datetime.datetime.now()
        today = now.day
        hour = now.hour
        minute = now.minute
        if (hour == 17 and minute == 0) or (hour == 7 and minute == 5):
                print("Daily update for {} user(s)".format(len(db.get())))
                text_mes = check_price()
                for chat in db.get():
                    price_bot.send_message(chat, text_mes)

def notify_thread():
    while True:
        time_executer.enter(60,1, notify)
        time_executer.run()

#___________Variables___________
price_bot = BotHandler('401670663:AAELFfb0SSv6qTiTlBTwkzhytSc9bH0cikI')
price = 6000
db = DataBase()
lock = Lock()
time_executer = sched.scheduler(time.time, time.sleep)

#_______________________________

def main():
    new_offset = None
    
    thread = Thread(target = notify_thread)
    thread.start()
    
    while True:
        new_offset = update(new_offset)


if __name__ == '__main__':  
    try:
        main()
    except IndexError:
        print('Index error')
    except KeyError:
        print('KeyError')
    except KeyboardInterrupt:
        print("Goodbye!")
        exit()