#!/usr/bin/env python
# coding: utf-8
'''插件工具测试：get_config_value'''

from __future__ import print_function
import os
from plugin_tools import get_config_value

def _test_get_config(plugin, config, type_, expected):
    def _get_state():
        return {'process_info': {'plugins': {
            'Plugin Name': {'config': [{'name': 'twenty', 'value': 20}]}}}}
    if type_ is None:
        received = get_config_value(plugin, config, _get_state=_get_state)
    else:
        received = get_config_value(plugin, config, type_, _get_state=_get_state)
    assert received == expected, 'expected {}, received {}'.format(
        repr(expected), repr(received))
    print('get_config_value result {} == {}'.format(
        repr(received), repr(expected)))

def run_tests():
    '运行get_config_value测试。'
    os.environ['plugin_name_int_input'] = '10'
    os.environ['plugin_name_str_input'] = 'ten'
    _test_get_config('plugin_name', 'int_input', None, 10)
    _test_get_config('Plugin Name', 'int_input', int, 10)
    _test_get_config('plugin-name', 'int_input', str, '10')
    _test_get_config('plugin_name', 'str_input', str, 'ten')
    _test_get_config('Plugin Name', 'twenty', None, 20)  # default value
    os.environ['plugin_name_twenty'] = 'twenty'
    _test_get_config('Plugin Name', 'twenty', str, 'twenty')  # set value

if __name__ == '__main__':
    run_tests()
