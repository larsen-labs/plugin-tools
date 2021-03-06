#!/usr/bin/env python
# coding: utf-8
'''插件工具：Web应用。'''

from __future__ import print_function
import sys
import time
import json
import base64
import requests
from .auxiliary import Color
from .env import Env

COLOR = Color()
ENV = Env()

def _get_required_info():
    '获取向Funfarm Web应用程序发送HTTP请求所需的信息。'
    token = ENV.token
    encoded_payload = token.split('.')[1]
    encoded_payload += '=' * (4 - len(encoded_payload) % 4)
    json_payload = base64.b64decode(encoded_payload).decode('utf-8')
    server = json.loads(json_payload)['iss']
    url = 'http{}:{}/api/'.format('s' if ':443' in server else '', server)
    return {'token': token, 'url': url}

def _error(message):
    if ENV.plugin_api_available():
        log(message, 'error')
        sys.exit(1)
    else:
        print(COLOR.error(message))

def _simplify_text_response(text, code):
    'Reduce API text response content to relevant error string.'
    relevant_tags = ['h1', 'h2']
    to_strip = [' ', '<h1>', '</h1>', '<h2>', '</h2>']
    def _strip_strings(from_string):
        for strip_string in to_strip:
            from_string = from_string.strip(strip_string)
        return from_string

    try:
        if len(text) < 10000:
            return text
        shortened = text.split('\n')[100:300]
        relevant = [t for t in shortened if any(s in t for s in relevant_tags)]
        cleaned = [_strip_strings(t).replace('&quot;', '\'') for t in relevant]
        simple_error_string = ': '.join([t for t in cleaned if len(t) > 0])
    except Exception as exception:
        return 'Unable to reduce text response due to {!r}'.format(exception)
    else:
        return '({}) {}'.format(code, simple_error_string)

def request(raw_method, endpoint, _id=None, payload=None, return_dict=False,
            get_info=_get_required_info):
    """向Funfarm Web应用程序发送HTTP请求。

    参数:
        raw_method (str): HTTP请求方法 ('POST', 'GET', etc.)
        endpoint (str): Web应用程序终结点 ('sequences', 'logs', etc.)
        _id (int, optional): Web应用资源ID。默认为None.
        payload (dict, optional): 例如 {'name': 'new tool'}
    """
    method = raw_method.upper()
    full_endpoint = endpoint
    if _id is not None:
        full_endpoint += '/{}'.format(_id)
    request_string = '{} /api/{} {}'.format(
        method, full_endpoint,
        payload if payload is not None else '')
    try:
        api = get_info()
    except:
        print(request_string)
        if return_dict:
            return {'json': json.dumps(request_string), 'status_code': 0}
        return request_string

    try:  # 测试时详细输出
        if api['verbose']:
            verbose = True
    except KeyError:
        verbose = False

    url = api['url'] + full_endpoint
    request_kwargs = {}
    request_kwargs['headers'] = {
        'Authorization': 'Bearer ' + api['token'],
        'content-type': 'application/json'}
    if payload is not None:
        request_kwargs['json'] = payload
    response = requests.request(method, url, **request_kwargs)
    status_code = response.status_code
    colorized_status_code = COLOR.colorize_response_code(status_code)
    bold_request_string = COLOR.make_bold(request_string)
    request_details = '{}: {}'.format(colorized_status_code, bold_request_string)
    if verbose:
        print()
        print(request_details)
    try:
        json_response = response.json()
        text_response = response.text
    except:
        text_response = _simplify_text_response(response.text, status_code)
        json_response = json.dumps(text_response)
    if status_code != 200 and not verbose:
        print(request_details)
        print(text_response)
    if return_dict:
        return {'json': json_response, 'status_code': status_code}
    return json_response

def post(endpoint, payload, return_dict=False, get_info=_get_required_info):
    """向Funfarm Web应用程序发送Post HTTP请求。

    参数:
        endpoint (str): 应用程序终结点。
        payload (dict): 例如, {'name': 'new tool'}
    """
    kwargs = {
        'payload': payload,
        'return_dict': return_dict,
        'get_info': get_info
        }
    return request('POST', endpoint, **kwargs)

def get(endpoint, _id=None, return_dict=False, get_info=_get_required_info):
    """向Funfarm Web应用程序发送Get HTTP请求。

    参数:
        endpoint (str): 应用程序终结点。
        _id (int, optional): 资源的ID。 默认为None。
    """
    kwargs = {
        '_id': _id,
        'payload': payload,
        'return_dict': return_dict,
        'get_info': get_info
        }
    return request('GET', endpoint, **kwargs)

def patch(endpoint, _id=None, payload=None, return_dict=False,
          get_info=_get_required_info):
    """
    参数:
        endpoint (str): 应用程序终结点。
        _id (int, optional): 资源的ID。 默认为None。
        payload (dict, optional): 默认为None。
    """
    kwargs = {
        '_id': _id,
        'payload': payload,
        'return_dict': return_dict,
        'get_info': get_info
        }
    return request('PATCH', endpoint, **kwargs)

def put(endpoint, _id=None, payload=None, return_dict=False,
        get_info=_get_required_info):
    """向Funfarm Web应用程序发送Put HTTP请求。

    参数:
        endpoint (str): 应用程序终结点。
        _id (int, optional): 资源的ID。 默认为None。
        payload (dict, optional): 默认为None。
    """
    kwargs = {
        '_id': _id,
        'payload': payload,
        'return_dict': return_dict,
        'get_info': get_info
        }
    return request('PUT', endpoint, **kwargs)

def delete(endpoint, _id=None, return_dict=False, get_info=_get_required_info):
    """向Funfarm Web应用程序发送Delete HTTP请求。

    参数:
        endpoint (str): 应用程序终结点。
        _id (int, optional): 资源的ID。 默认为None。
    """
    kwargs = {
        '_id': _id,
        'return_dict': return_dict,
        'get_info': get_info
        }
    return request('DELETE', endpoint, **kwargs)

def log(message, message_type='info', get_info=_get_required_info):
    """将日志消息发布到Web应用程序。

    警告：在刷新之前，浏览器中可能不会显示。请尽可能使用“device.log”。

    参数:
        message (str): 记录消息内容。
        message_type (str, optional): device.ALLOWED_MESSAGE_TYPES 之一，默认为'info'
    """
    payload = {'message': message, 'type': message_type}
    return post('logs', payload=payload, get_info=get_info)

def search_logs(search_payload, get_info=_get_required_info):
    """使用搜索词从Web应用程序中获取日志。

    参数:
        search_payload (dict): 例如, {'x': 5}
           允许的关键字包括:
                verbosity, type, message, x, y, z
    """
    return get('logs/search', payload=search_payload, get_info=get_info)
def search_points(search_payload, get_info=_get_required_info):
    """使用关键词从Web应用程序获取过滤后的点。

    参数:
        search_payload (dict): 例如, {'x': 5}
            允许的关键字包括:
                name, pointer_type, plant_stage, planting_slug, meta,
                radius, x, y, z
    """
    return post('points/search', payload=search_payload, get_info=get_info)

def download_plants(get_info=_get_required_info):
    """从Web应用程序获取作物数据。"""
    search_payload = {'pointer_type': 'Plant'}
    return search_points(search_payload, get_info)

def get_points(get_info=_get_required_info):
    """从Web应用程序获取通用点数据。"""
    search_payload = {'pointer_type': 'GenericPointer'}
    return search_points(search_payload, get_info)

def get_plants(get_info=_get_required_info):
    """从Web应用程序获取作物数据。"""
    return download_plants(get_info)

def get_toolslots(get_info=_get_required_info):
    """从Web应用程序获取工具槽数据。"""
    search_payload = {'pointer_type': 'ToolSlot'}
    return search_points(search_payload, get_info)

def get_property(endpoint, field, _id=None, get_info=_get_required_info):
    """G获取Web应用记录的特定属性字段的值。

    参数:
        endpoint (str): 应用程序终结点。
        field (str): 资源属性键名。
        _id (int, optional): 资源ID。 默认为None。
    """
    record = get(endpoint, _id=_id, get_info=get_info)
    try:
        return record[field]
    except (KeyError, TypeError):
        _error('{} not found.'.format(field))

def add_plant(x, y, get_info=_get_required_info, **kwargs):
    """在花园地图上添加植物。

    参数:
        x (int): X坐标。
        y (int): Y坐标。
        **kwargs: name, planting_slug, radius, z, planted_at, plant_stage
    """
    new_plant = {'pointer_type': 'Plant', 'x': x, 'y': y}
    for key, value in kwargs.items():
        if value is not None:
            new_plant[key] = value
    return post('points', payload=new_plant, get_info=get_info)

def find_sequence_by_name(name, get_info=_get_required_info):
    """查找给定序列名的序列ID。

    参数:
        name (str): 序列名称。
    """
    sequences = get('sequences', get_info=get_info)
    if not isinstance(sequences, list):
        _error('Error retrieving sequences.')
        sequences = []
    sequence_lookup = {s['name']: s['id'] for s in sequences}
    try:
        uname = name.decode('utf-8')
    except (UnicodeEncodeError, AttributeError):
        uname = name
    try:
        sequence_id = sequence_lookup[uname]
    except KeyError:
        _error(u'Sequence `{}` not found.'.format(uname))
    else:
        return sequence_id

if __name__ == '__main__':
    TIMESTAMP = str(int(time.time()))
    log('Hello World!', message_type='success')
    request('GET', 'tools')
    get('sensors')
    TOOL = post('tools', payload={'name': 'test_tool_' + TIMESTAMP})
    ID = TOOL['id']
    put('tools', ID, payload={'name': 'test_tool_edit_' + TIMESTAMP})
    delete('tools', ID)
    search_points({'pointer_type': 'Plant'})
    download_plants()
    get_points()
    get_plants()
    get_toolslots()
    get_property('device', 'name')
    add_plant(x=100, y=100)
    add_plant(x=10, y=20, z=30, radius=10, planting_slug='mint', name='test')
    find_sequence_by_name('test')
