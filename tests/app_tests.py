#!/usr/bin/env python
# coding: utf-8
'''插件工具测试：web应用程序'''

from __future__ import print_function
import time
from plugin_tools import app

def run_tests(app_login):
    '运行应用程序测试。'
    TIMESTAMP = str(int(time.time()))
    print(app.log('hi', get_info=app_login))
    print(app.request('GET', 'tools', get_info=app_login))
    print(app.request('GET', 'tools', return_dict=True, get_info=app_login))
    print(app.get('sensors', get_info=app_login))
    print(app.search_logs({'type': 'warn'}, get_info=app_login))
    print(app.get('sensors', return_dict=True, get_info=app_login))
    print(app.get('invalid_endpoint', get_info=app_login))
    print(app.post('tools', payload='invalid payload', get_info=app_login))
    TOOL = app.post('tools', payload={'name': 'test_tool_' + TIMESTAMP},
                    get_info=app_login)
    print(TOOL)
    TOOL_ID = TOOL['id']
    print(app.put('tools', TOOL_ID,
                  payload={'name': 'test_tool_edit_' + TIMESTAMP},
                  get_info=app_login))
    print(app.delete('tools', TOOL_ID, get_info=app_login))
    print(app.search_points({'pointer_type': 'Plant'}, get_info=app_login))
    print(app.get_points(get_info=app_login))
    print(app.get_plants(get_info=app_login))
    print(app.get_toolslots(get_info=app_login))
    print(app.get_property('device', 'name', get_info=app_login))
    print(app.download_plants(get_info=app_login))
    PLANT = app.add_plant(x=100, y=100, get_info=app_login)
    print(PLANT)
    PLANT_ID = PLANT['id']
    print(app.delete('points', PLANT_ID, get_info=app_login))
    PLANT2 = app.add_plant(x=10, y=20, z=30, radius=10, planting_slug='mint',
                           name='test', get_info=app_login)
    print(PLANT2)
    print(app.delete('points', PLANT2['id'], get_info=app_login))
    app.post('sequences', {'name': 'test', 'body': []}, get_info=app_login)
    app.post('sequences', {'name': u'test \u2713', 'body': []},
             get_info=app_login)
    print(app.find_sequence_by_name(name=u'test \u2713', get_info=app_login))
    print(app.find_sequence_by_name(name='test', get_info=app_login))
    print()
