
# coding: utf-8

# In[ ]:

import requests
import json
import random
from time import sleep
import re


class FsspWebService():

    def __init__(self, token):
        self._token = token
        self._base_url = 'https://api-ip.fssprus.ru/api/v1.0/'
        self._tasks_in_work = dict()
        self._TAG_RE = re.compile(r'<[^>]+>')
        
    #метод фссп    
    def _search_physical(self, region, first_name, second_name, last_name, birth_date):
        '''Выполняет запрос и возвращает номер и статус задачи по поиску физика'''
        path = 'search/physical'
        payload = {'region': region, 'firstname': first_name, 'secondname': second_name, 
                   'lastname':last_name, 'birthdate':birth_date}
        full_path = self._base_url + path
        
        response_text = self._send_request(full_path, payload)
        response = json.loads(response_text)
        
        task_id = response['response']['task']
        status_code = response['code']
        
        return task_id, status_code
        
    #метод фссп       
    def _status(self, tid):
        '''Возвращает статус по задаче (Код)'''
        path = 'status'
        payload = {'task': tid}
        full_path = self._base_url + path
        
        response_text = self._send_request(full_path, payload)
        response_json = json.loads(response_text)
        status_code = response_json['response']['status']
        
        return status_code
    tmp = None                                   
    #метод фссп      
    def _result(self, tid):
        '''Возвращает ответ по выполненой задаче (Код 0)'''
        path = 'result'
        payload = {'task': tid}
        full_path = self._base_url + path
        response_text = self._send_request(full_path, payload)
        response_json = json.loads(response_text)
        return response_json['response']['result'][0]['result']
        #return self.remove_html_tags(str(response_json['response']['result'][0]['result']))
    
    #метод фссп   
    def _send_request(self, path, payload, method = 'GET'):
        payload['token'] = self._token
        if method == 'GET':
            #заглушка пока нет сети
            #rnd = str(random.randint(a=1, b=1000))
            #rnd_code = str(random.randint(a=0,b=1))
            #return '{"status": "success", "code": ' + rnd_code + ', "exception": "", "response": {"task": "my_task_id_' + rnd + '"}}'
#             print(path)
#             print(payload)
            return requests.get(path,params=payload).text
        if method == 'POST':
            return requests.post(path,params=payload)
        
        
    def check_user_request(self, user):
        '''Проверить наличие запросов пользователя'''
        if user in self._tasks_in_work:
            #вытаскиваем список ожидающих результата задач пользователя
            user_tasks = self._tasks_in_work[user]
            finished_user_tasks = list()
            finished_tasks_to_delete = list()
            for user_task in user_tasks:
                #проверяем текущий статус по задаче
                actual_status_code = self._status(user_task)
                if actual_status_code == 0:
                    #Если задача готова - запрашиваем результат
                    finished_task = self._result(user_task)
                    for element in finished_task:
                        #добавляем результат в список выполненых задач
                        finished_user_tasks.append(element)
                    user_tasks[user_task] = 0
                    finished_tasks_to_delete.append(user_task)
            for finished_task_to_delete in finished_tasks_to_delete:
                del user_tasks[finished_task_to_delete]
                
            return(finished_user_tasks, user_tasks)
        else:
            return None
        
        
  
    def get_person_info(self, user, region=12, first_name='Anton', second_name='', last_name='Stasenok', birth_date='12.05.1999'):
        #проверяем, есть ли по текущему пользователю список задач в работе, если нет - создаём
        if user not in self._tasks_in_work:
            self._tasks_in_work[user] = dict()
        
        
        # получаем номер задачи и статус
        task_id, status_code = self._search_physical(region, first_name, second_name, last_name, birth_date)
        # если всё ок
        if status_code == 0:
            #ждём, чтобы даь время ФССП обработать запрос
            sleep(1)
            #проверяем статус
            actual_status_code = self._status(task_id)
            if actual_status_code == 0:
                #Если задача готова - запрашиваем результат
                finished_task = self._result(task_id)
                #возвращаем задачу
                return self.remove_html_tags(str(finished_task))
            else: # иначе добавляем в список задач в работе пользователя добавляем результат ответа - номер задачи и статус
                self._tasks_in_work[user][task_id] = status_code
                return task_id
        else: # если что-то пошло не так
            return None
        
    
        
    def remove_html_tags(self, text):
        return self._TAG_RE.sub(' ', text)
        


# In[ ]:

#from WebService import FsspWebService
from flask import Flask, flash, redirect, render_template, request, session, abort, Response, Session, send_file
from functools import wraps

tokens = {'d8642de0a269dac8c95d49782939dcb9': 'Element Leasing'}


app = Flask(__name__)
sess = Session()
#УСТАНОВКА ТОКЕНА ДОСТУПА К ФССП
ws = FsspWebService('Yx9OoERdpr3p')

TAG_RE = re.compile(r'<[^>]+>')

def remove_html_tags(text):
        return TAG_RE.sub(' ', text)

#Wrappers
def require_api_token(func):
    '''Check auth token'''
    @wraps(func)
    def check_token(*args, **kwargs):
        user_token = request.headers.get('auth_token')
        if user_token not in tokens:
            return Response('Access denied', 401)
        else:
            user_name = tokens[user_token]
            sess['user_name'] = user_name
            return func(*args, **kwargs)
    return check_token



#API Methods
@app.route("/")
def index():
    return 'Leasing API is running'

@app.route("/fssp/get", methods=["get"])
@require_api_token
def fssp_get():
    region = request.args.get('region')
    first_name = request.args.get('firstname')
    second_name = request.args.get('secondname')
    last_name = request.args.get('lastname')
    birth_date = request.args.get('birthdate')
    user = sess['user_name'] 
    
    info = ws.get_person_info(user, region, first_name, second_name, last_name, birth_date)
    if info is None:
        return Response('Task is pending', 201)
    else:
        return info

@app.route("/fssp/check", methods=["get"])
@require_api_token
def fssp_check():
    
    user = sess['user_name'] 
    pending_tasks = ws.check_user_request(user)
    
    if pending_tasks is None:
        return Response('No tasks pending',204)
    else:
        return remove_html_tags(str(pending_tasks))


@app.route("/fssp", methods=["post"])
@require_api_token
def fssp_post():
    if 'agreement' not in request.files:
        return Response('No agreement attached. You can send GET request without agreement', 400)
    
    #uploaded agreement file
    agreement_file = request.files['agreement']
    
    return ws.get_person_info()




if __name__ == "__main__":
    app.seckret_key = '23df833be15d3ab59ba66172bcfb78a0'
    app.run(host='127.0.0.1',port=5000)


# In[ ]:

print(rndhttp://127.0.0.1:5000/fssp?region=64&firstname=Артём&secondname&lastname=Дергунов&birthdate=23.01.1987


# In[ ]:

ws.tmp is None

