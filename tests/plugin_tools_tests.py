#!/usr/bin/env python
# coding: utf-8
'''插件工具测试。'''

from __future__ import print_function
import sys
import uuid
import json
import time
from getpass import getpass
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import requests
from plugin_tools import device, app, auxiliary, VERSION

COLOR = auxiliary.Color()

try:
    INPUT = raw_input
except NameError:
    INPUT = input

def _decode(_input):
    try:
        return _input.decode()
    except AttributeError:
        return _input

def get_credentials():
    '通过 server, email和 password 获取device_id, token和mqtt_host '
    use_localhost = _decode(INPUT('Use localhost? (Y/n): ') or 'Y')
    if 'y' in use_localhost.lower():
        server = 'http://localhost:3000/'
        email = 'admin@admin.com'
        password = 'password123'
    else:
        server = _decode(INPUT('server: ') or 'https://funfarm.fun/')
        email = _decode(INPUT('account email: '))
        password = getpass('password: ')
    token_headers = {'content-type': 'application/json'}
    user = {'user': {'email': email, 'password': _decode(password)}}
    payload = json.dumps(user)
    response = requests.post(server + 'api/tokens',
                             headers=token_headers, data=payload)
    response.raise_for_status()
    token = response.json()['token']
    return {
        'device_id': token['unencoded']['bot'],
        'token': token['encoded'],
        'mqtt_host': token['unencoded']['mqtt'],
        'url': server + '/api/'}

def send(celery_script, credentials, rpc_id=''):
    '将 Celery 脚本发送到设备以执行。'
    publish.single(
        'bot/{}/from_clients'.format(credentials['device_id']),
        payload=json.dumps(device.rpc_wrapper(celery_script, rpc_id)),
        hostname=credentials['mqtt_host'],
        auth={
            'username': credentials['device_id'],
            'password': credentials['token']})

def subscribe(host, user, password, channel, callback):
    '订阅设备频道。'
    client = mqtt.Client()
    client.username_pw_set(user, password)
    client.on_message = callback
    client.connect(host)
    client.subscribe(channel)
    client.loop_start()
    return client

def _new_uuid(label=''):
    return str(uuid.uuid4())[:-len(label)] + label

LOG_FW_CMD_CONFIG_KEY = 'firmware_output_log'
TIMEOUT_SECONDS = 10

class Tester(object):
    '测试设备命令。'

    def __init__(self):
        print('输入设备运行测试的帐户凭据:')
        self.login_info = get_credentials()
        self.subscribe()
        self.outgoing = {}  # {'uuid': {'kind': 'wait', 'time': 0}}
        self.incoming = {}  # {'uuid': {'status': 'ok', 'time': 9}}
        self.all_client_comms = {}  # {'uuid': 'kind'}
        self.elapsed = []
        self.response_data = {'logs_string': '', 'status': None}

    def setup(self):
        '预测试配置.'
        print('-' * 50)
        print('测试设置：')
        fw_out_log_opt = app.get_property(
            'lsos_config', LOG_FW_CMD_CONFIG_KEY, get_info=app_login)
        if fw_out_log_opt:
            print('{}`{}`{} option already enabled.'.format(
                COLOR.bold, LOG_FW_CMD_CONFIG_KEY, COLOR.reset))
        else:
            app.put('lsos_config', payload={LOG_FW_CMD_CONFIG_KEY: True},
                    get_info=app_login)
            self.wait_for_log(LOG_FW_CMD_CONFIG_KEY, count_time=False)
        send(device.sync()['command'], self.login_info)
        print('-' * 50)

    def teardown(self):
        '测试后配置。'
        print('-' * 50)
        print('测试拆卸：')
        app.put('lsos_config', payload={LOG_FW_CMD_CONFIG_KEY: False},
                get_info=app_login)
        self.wait_for_log(LOG_FW_CMD_CONFIG_KEY, count_time=False)
        print('-' * 50)

    def test(self, command, expected=None, rpc_id=None):
        '在设备上测试命令。'
        if command is not None:
            kind = command['kind']
            self.response_data['logs_string'] = ''
            rpc_test_id = _new_uuid('test') if rpc_id is None else rpc_id
            send(command, self.login_info, rpc_test_id)
            self.outgoing[rpc_test_id] = {'kind': kind, 'time': time.time()}
            self.wait_for_response(rpc_test_id)
            if expected is not None:
                if expected.get('log') is not None:
                    for expected_log in expected['log']:
                        self.wait_for_log(expected_log)
                if expected.get('status') is not None:
                    for status in expected['status']:
                        self.wait_for_status(status['keys'], status['value'])
        else:
            print('command is {}'.format(command))

    def _get_channel_name(self, topic):
        return 'bot/{}/{}'.format(self.login_info['device_id'], topic)

    def subscribe(self):
        '监听响应'
        user = self.login_info['device_id']
        host = self.login_info['mqtt_host']
        password = self.login_info['token']
        response_channel = self._get_channel_name('from_device')
        subscribe(host, user, password, response_channel, self.add_response)
        client_channel = self._get_channel_name('from_clients')
        subscribe(host, user, password, client_channel, self.add_client_comm)
        log_channel = self._get_channel_name('logs')
        subscribe(host, user, password, log_channel, self.add_log_message)
        status_channel = self._get_channel_name('status')
        subscribe(host, user, password, status_channel, self.update_status)

    def add_response(self, _client, _userdata, message):
        '向列表中添加响应。'
        if 'from_device' in message.topic:
            parsed = json.loads(message.payload.decode())
            kind = parsed['kind']
            if kind in ['rpc_ok', 'rpc_error']:
                rpc_id = parsed['args']['label']
                if rpc_id != 'ping':
                    self.incoming[rpc_id] = {
                        'status': kind.split('_')[-1], 'time': time.time()}
                    if kind == 'rpc_error':
                        try:
                            error_message = parsed['body'][0]['args']['message']
                        except KeyError:
                            pass
                        else:
                            self.incoming[rpc_id]['error'] = error_message

    def add_log_message(self, _client, _userdata, message):
        '向列表中添加日志消息字符串。'
        if 'logs' in message.topic:
            parsed = json.loads(message.payload.decode())
            message = parsed['message']
            self.response_data['logs_string'] += message

    def add_client_comm(self, _client, _userdata, message):
        '将客户端消息添加到列表。'
        if 'from_clients' in message.topic:
            parsed = json.loads(message.payload.decode())
            rpc_id = parsed['args']['label']
            try:
                kind = parsed['body'][0]['kind']
            except (KeyError, TypeError):
                pass
            else:
                self.all_client_comms[rpc_id] = kind

    def update_status(self, _client, _userdata, message):
        '更新最新状态。'
        if 'status' in message.topic:
            parsed = json.loads(message.payload.decode())
            self.response_data['status'] = parsed

    def wait_for_log(self, string, count_time=True):
        '等待特定的日志消息字符串。'
        def _result(outcome, begin_time):
            time_diff = time.time() - begin_time
            print('{}{}{} {}`{}`{} {:.2f}ms'.format(
                COLOR.green if outcome == 'ok' else COLOR.red,
                outcome, COLOR.reset,
                COLOR.bold, string, COLOR.reset, time_diff * 1000))
            return time_diff
        begin = time.time()
        print('期望的日志：'.upper(), end=' ')
        while (time.time() - begin) < TIMEOUT_SECONDS:
            if string in self.response_data['logs_string']:
                time_diff = _result('ok', begin)
                break
        else:
            time_diff = _result('timeout', begin)
        if count_time:
            self.elapsed.append(time_diff)

    def wait_for_status(self, keys, value):
        '等待特定的状态值。'
        key_string = '.'.join(keys)
        def _result(outcome, begin_time):
            time_diff = time.time() - begin_time
            print('{}{}{} {}{} == {}{} {:.2f}ms'.format(
                COLOR.green if outcome == 'ok' else COLOR.red,
                outcome, COLOR.reset,
                COLOR.bold, key_string, repr(value),
                COLOR.reset, time_diff * 1000))
            return time_diff
        def _extract_value(status):
            unwrapped = status
            for key in keys:
                unwrapped = unwrapped.get(key)
            return unwrapped
        begin = time.time()
        print('期望的状态：'.upper(), end=' ')
        while (time.time() - begin) < TIMEOUT_SECONDS:
            if _extract_value(self.response_data['status']) == value:
                time_diff = _result('ok', begin)
                break
        else:
            time_diff = _result('timeout', begin)
        self.elapsed.append(time_diff)

    def wait_for_response(self, rpc_id):
        '等待设备响应。'
        def _result(outcome, begin_time):
            time_diff = time.time() - begin_time
            print('{}{}{} {:.2f}s'.format(
                COLOR.green if outcome == 'ok' else COLOR.red,
                outcome, COLOR.reset, time_diff))
            return time_diff
        begin = time.time()
        print('rpc status:'.upper(), end=' ')
        out = self.outgoing[rpc_id]['time']
        while (time.time() - begin) < TIMEOUT_SECONDS:
            if rpc_id in self.incoming:
                rpc_response = self.incoming[rpc_id]
                status = rpc_response['status']
                time_diff = _result(status, out)
                if rpc_response.get('error') is not None:
                    print(COLOR.error(rpc_response['error']))
                break
        else:
            time_diff = _result('timeout', out)
        self.elapsed.append(time_diff)

    def print_elapsed_time(self):
        '计算总测试时间。'
        print('已用总时间： {:.2f}s'.format(sum(self.elapsed)))

    def _prepare_summary(self):
        summary = {}
        # 为每个RPC响应添加记录
        for rpc_uuid, in_data in self.incoming.items():
            data = {}
            data['uuid'] = rpc_uuid
            try:
                data['kind'] = self.outgoing[rpc_uuid]['kind']
                out_time = self.outgoing[rpc_uuid]['time']
            except KeyError:  # 在传出的RPC中找不到
                try:  # 检查所有客户端RPC
                    data['kind'] = self.all_client_comms[rpc_uuid]
                except KeyError:
                    data['kind'] = ' '
                data['elapsed'] = ' '
            else:
                elapsed_time_float = (in_data['time'] - out_time) * 1000
                data['elapsed'] = str(int(round(elapsed_time_float)))
            data['status'] = in_data['status']
            summary[self.incoming[rpc_uuid]['time']] = data
        # 为缺少的RPC响应添加记录
        for rpc_uuid, out_data in self.outgoing.items():
            if rpc_uuid not in self.incoming.keys():
                data = {}
                data['uuid'] = rpc_uuid
                data['kind'] = out_data['kind']
                data['status'] = 'timeout'
                data['elapsed'] = TIMEOUT_SECONDS * 1000
                summary[out_data['time']] = data
        return summary

    def print_summary(self):
        '打印测试摘要数据表。'
        table = '{:<40}{:<30}{:<10}{:>12}'
        titles = ['uuid', 'kind', 'status', 'elapsed (ms)']
        print(table.format(*titles))
        underline = table.format(*['-' * 7 for _ in titles])
        print(underline)
        summary = self._prepare_summary()
        for _, data in sorted(summary.items()):
            print(table.format(
                data['uuid'], data['kind'], data['status'], data['elapsed']))
        print(underline)
        all_ok = all(d['status'] == 'ok' for u, d in self.incoming.items())
        print(table.format(
            'received/sent:',
            '{}/{}'.format(len(self.incoming), len(self.outgoing)),
            'ok' if all_ok else 'error',
            int(round(sum(self.elapsed) * 1000))))
        print()

if __name__ == '__main__':
    print('python {}'.format(sys.version.split(' ')[0]))
    print('plugin_tools {}'.format(VERSION))
    LOGIN_INFO = False
    def app_login():
        '返回应用程序登录信息。'
        mqtt_login = TEST.login_info
        return {
            'token': mqtt_login['token'],
            'url': mqtt_login['url'],
            'verbose': True}
    def run_test(category):
        '提示运行测试类别。'
        run = INPUT('Run {} tests? (Y/n) '.format(category)) or 'y'
        if run.lower() == 'q':
            sys.exit(0)
        if run.lower() == 'y':
            return True

    # 设备测试
    if run_test('device'):
        if not LOGIN_INFO:
            TEST = Tester()
            LOGIN_INFO = True
        import device_tests
        device_tests.run_tests(TEST, app_login)

    # 应用程序测试
    if run_test('app'):
        if not LOGIN_INFO:
            TEST = Tester()
            LOGIN_INFO = True
        import app_tests
        app_tests.run_tests(app_login)

    # 其他测试
    def _print_header(text):
        print()
        print(text)
        print('-' * 35)

    if run_test('other'):
        _print_header('plugin_tools.get_config_value():')
        import get_config_value_tests
        get_config_value_tests.run_tests()

        import device_state_tests
        _print_header('device.get_current_position():')
        device_state_tests.run_position_tests()
        _print_header('device.get_pin_value():')
        device_state_tests.run_pin_value_tests()

        import device_requests_tests
        _print_header('device requests tests:')
        device_requests_tests.run_device_requests_tests()

        _print_header('env.Env().lsos_at_least():')
        import env_tests
        env_tests.run_tests()
    print()
    print('测试完成。')
