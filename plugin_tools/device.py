#!/usr/bin/env python
# coding: utf-8
'''插件工具：设备。'''

from __future__ import print_function
import os
import sys
import uuid
from functools import wraps
import requests
from .auxiliary import Color
from .env import Env

COLOR = Color()
ENV = Env()
ALLOWED_AXIS_VALUES = ['x', 'y', 'z', 'all']
ALLOWED_MESSAGE_TYPES = [
    'success', 'busy', 'warn', 'error', 'info', 'fun', 'debug']
ALLOWED_MESSAGE_CHANNELS = ['ticker', 'toast', 'email', 'espeak']
ALLOWED_PACKAGES = ['larsen_os', 'arduino_firmware', 'plugin']

def _on_error():
    if ENV.plugin_api_available():
        sys.exit(1)
    return

def _check_celery_script(command):
    try:
        kind = command['kind']
        args = command['args']
    except (KeyError, TypeError):
        _cs_error('celery script', command)
        _on_error()
    else:
        body = command.get('body')
        if body is not None:
            if not isinstance(body, list):
                _cs_error(kind, body)
                _on_error()
        return kind, args, body

def rpc_wrapper(command, rpc_id=None):
    """在'rpc_request'中使用给定的'rpc_id'包装命令。"""
    return {
        'kind': 'rpc_request',
        'args': {'label': rpc_id or str(uuid.uuid4())},
        'body': [command]}

def _device_request(method, endpoint, payload=None):
    '向设备插件API发出请求。'
    try:
        base_url = os.environ['PLUGIN_URL']
        token = os.environ['PLUGIN_TOKEN']
    except KeyError:
        return

    url = base_url + 'api/v1/' + endpoint
    request_kwargs = {}
    request_kwargs['headers'] = {
        'Authorization': 'Bearer ' + token,
        'content-type': 'application/json'}
    if payload is not None:
        request_kwargs['json'] = payload
    response = requests.request(method, url, **request_kwargs)
    if response.status_code != 200:
        log('{} request `{}` error ({})'.format(
            endpoint, payload or '', response.status_code), 'error')
        _on_error()
    return response

def _post(endpoint, payload):
    """将有效负载发布到设备插件API。

    由于唯一可用的端点是'celery_script'，请改用'send_celery_script（command）'。

    参数:
        endpoint (str): 'celery_script'
        payload (dict): 例如, {'kind': 'take_photo', 'args': {}}
    返回：
        请求响应对象
    """
    return _device_request('POST', endpoint, payload)

def _get(endpoint):
    """从设备插件API获取信息。

    由于唯一可用的终结点是'bot/state',请改用`get_bot_state()`。

    参数:
        endpoint (str): 'bot/state'
    返回：
        请求响应对象
    """
    return _device_request('GET', endpoint)

def get_bot_state():
    """获取设备状态。"""
    bot_state = _get('bot/state')
    if bot_state is None:
        _error('Device info could not be retrieved.')
        _on_error()
        return {}
    else:
        return bot_state.json()

def _send(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        '将Celery脚本发送到设备。'
        rpc_id = kwargs.pop('rpc_id', None)
        if not isinstance(rpc_id, str):
            return send_celery_script(function(*args, **kwargs))
        else:
            return send_celery_script(function(*args, **kwargs), rpc_id=rpc_id)
    return wrapper

def send_celery_script(command, rpc_id=None):
    """发送Celery脚本命令。"""
    kind, args, body = _check_celery_script(command)
    temp_no_rpc_kinds = ['read_pin', 'write_pin', 'set_pin_io_mode', 'update_plugin']
    no_rpc = kind in temp_no_rpc_kinds and not ENV.lsos_at_least(7, 0, 1)
    if kind == 'rpc_request' or no_rpc:
        rpc = command
    else:
        rpc = rpc_wrapper(command, rpc_id=rpc_id)
    response = _post('celery_script', rpc)
    if response is None:
        print(COLOR.colorize_celery_script(kind, args, body))
    return {
        'command': command,
        'sent': rpc,
        }

def log(message, message_type='info', channels=None, rpc_id=None):
    """发送'发送消息'命令以将日志发布到Web应用程序。

    参数:
        message (str): 日志消息内容
        message_type (str, optional): ALLOWED_MESSAGE_TYPES之一。默认为 'info'.
        channels (list, optional): ALLOWED_MESSAGE_CHANNELS之一。默认为 None.
    """
    return send_message(message, message_type, channels, rpc_id=rpc_id)

def _assemble(kind, args, body=None):
    '装配celery脚本指令'
    if body is None:
        return {'kind': kind, 'args': args}
    else:
        return {'kind': kind, 'args': args, 'body': body}

def _error(error_text):
    if ENV.plugin_api_available():
        log(error_text, 'error')
    else:
        print(COLOR.error(error_text))

def _cs_error(kind, arg):
    if ENV.plugin_api_available():
        log('Invalid arg `{}` for `{}`'.format(arg, kind), 'error')
    else:
        print(COLOR.error('Invalid input `{arg}` in `{kind}`'.format(
            arg=arg, kind=kind)))

def _check_arg(kind, arg, accepted):
    '命令参数无效时出错并退出。'
    arg_ok = True
    if arg not in accepted:
        _cs_error(kind, arg)
        _on_error()
        arg_ok = False
    return arg_ok

def assemble_coordinate(coord_x, coord_y, coord_z):
    """从x、y和z组装一个celery脚本的坐标节点。"""
    return {
        'kind': 'coordinate',
        'args': {'x': coord_x, 'y': coord_y, 'z': coord_z}}

def _assemble_channel(name):
    '组装一个通道主体项（用于`send_message`）。'
    return {
        'kind': 'channel',
        'args': {'channel_name': name}}

def assemble_pair(label, value):
    """组装`键值对`celery脚本节点（用作body项）。"""
    return {
        'kind': 'pair',
        'args': {'label': label, 'value': value}}

def _check_coordinate(coordinate):
    coordinate_ok = True
    try:
        coordinate_ok = coordinate['kind'] == 'coordinate'
        coordinate_ok = sorted(coordinate['args'].keys()) == ['x', 'y', 'z']
    except (KeyError, TypeError):
        coordinate_ok = False
    if not coordinate_ok:
        _cs_error('coordinate', coordinate)
        _on_error()
    return coordinate_ok

@_send
def send_message(message, message_type, channels=None):
    """发送命令：发送消息。

    参数:
        message (str): 日志消息内容
        message_type (str, optional): ALLOWED_MESSAGE_TYPES之一，默认为 'info'.
        channels (list, optional): ALLOWED_MESSAGE_CHANNELS之一，默认为 None.
    """
    kind = 'send_message'
    args_ok = _check_arg(kind, message_type, ALLOWED_MESSAGE_TYPES)
    if channels is not None:
        for channel in channels:
            args_ok = _check_arg(kind, channel, ALLOWED_MESSAGE_CHANNELS)
    if args_ok:
        if channels is None:
            return _assemble(
                kind, {'message': message, 'message_type': message_type})
        else:
            return _assemble(
                kind,
                args={'message': message, 'message_type': message_type},
                body=[_assemble_channel(channel) for channel in channels])

@_send
def calibrate(axis):
    """发送命令：校准。

    参数:
        axis (str): ALLOWED_AXIS_VALUES之一
    """
    kind = 'calibrate'
    args_ok = _check_arg(kind, axis, ALLOWED_AXIS_VALUES)
    if args_ok:
        return _assemble(kind, {'axis': axis})

@_send
def check_updates(package):
    """发送命令：检查更新。

    参数:
        package (str): ALLOWED_PACKAGES之一
    """
    kind = 'check_updates'
    args_ok = _check_arg(kind, package, ALLOWED_PACKAGES)
    if args_ok:
        return _assemble(kind, {'package': package})

@_send
def emergency_lock():
    """发送命令：急停。"""
    kind = 'emergency_lock'
    return _assemble(kind, {})

@_send
def emergency_unlock():
    """发送命令：急停解锁。"""
    kind = 'emergency_unlock'
    return _assemble(kind, {})

@_send
def execute(sequence_id):
    """发送命令：执行。

    参数:
        sequence_id (int): Web应用程序序列ID。
            序列必须在执行之前同步到Larsen OS。
    """
    kind = 'execute'
    return _assemble(kind, {'sequence_id': sequence_id})

@_send
def execute_script(label, inputs=None):
    """发送命令：执行脚本（运行插件）。

    参数:
        label (str): 要执行的插件的名称。必须已经安装。
        inputs (dict, optional): 插件配置, 例如, {'input_0': 0}。默认为 None.
    """
    kind = 'execute_script'
    args = {'label': label}
    if inputs is None:
        return _assemble(kind, args)
    else:
        plugin = label.replace(' ', '_').replace('-', '_').lower()
        body = []
        for key, value in inputs.items():
            if key.startswith(plugin):
                input_name = key
            else:
                input_name = '{}_{}'.format(plugin, key)
            body.append(assemble_pair(input_name, value))
        return _assemble(kind, args, body)

def _set_docstring_for_execute_script_alias(func):
    func.__doc__ = execute_script.__doc__
    return func

@_set_docstring_for_execute_script_alias
def run_plugin(label, inputs=None, rpc_id=None):
    """`execute_script`的别名"""
    return execute_script(label, inputs, rpc_id=rpc_id)

@_send
def factory_reset(package):
    """发送命令：恢复出厂设置。

    参数:
        package (str): ALLOWED_PACKAGES之一。
    """
    kind = 'factory_reset'
    args_ok = _check_arg(kind, package, ALLOWED_PACKAGES)
    if args_ok:
        return _assemble(kind, {'package': package})

@_send
def find_home(axis):
    """发送命令：查找零点。

    参数:
        axis (str): ALLOWED_AXIS_VALUES之一。
    """
    kind = 'find_home'
    args_ok = _check_arg(kind, axis, ALLOWED_AXIS_VALUES)
    if args_ok:
        return _assemble(kind, {'axis': axis})

@_send
def home(axis):
    """发送命令：归零。

    参数:
        axis (str): ALLOWED_AXIS_VALUES之一。
    """
    kind = 'home'
    args_ok = _check_arg(kind, axis, ALLOWED_AXIS_VALUES)
    if args_ok:
        return _assemble(kind, {'axis': axis})

@_send
def install_plugin(url):
    """发送命令：安装插件。

    参数:
        url (str): 插件清单的URL。
    """
    kind = 'install_plugin'
    return _assemble(kind, {'url': url})

@_send
def install_first_party_plugin():
    """发送命令：安装内置插件"""
    kind = 'install_first_party_plugin'
    return _assemble(kind, {})

@_send
def move_absolute(location, speed, offset):
    """发送命令：移动到“绝对位置”。

    Celery 脚本的 'coordinate' 节点可以使用
    `assemble_coordinate(coord_x, coord_y, coord_z)`组装。

    参数:
        location (dict): Celery 脚本 'coordinate' 节点。
        speed (int): 最大速度的百分比。
        offset (dict): Celery 脚本 'coordinate' 节点。
    """
    kind = 'move_absolute'
    args_ok = _check_coordinate(location)
    args_ok = _check_coordinate(offset)
    args_ok = _check_arg(kind, speed, range(1, 101))
    if args_ok:
        return _assemble(kind, {'location': location,
                                'speed': speed,
                                'offset': offset})

@_send
def move_relative(x, y, z, speed):
    """发送命令：相对移动。

    参数:
        x (int): 距离。
        y (int): 距离。
        z (int): 距离。
        speed (int): 最大速度的百分比。
    """
    kind = 'move_relative'
    args_ok = _check_arg(kind, speed, range(1, 101))
    if args_ok:
        return _assemble(kind, {'x': x,
                                'y': y,
                                'z': z,
                                'speed': speed})

@_send
def power_off():
    """发送命令：关闭电源。"""
    kind = 'power_off'
    return _assemble(kind, {})

@_send
def read_pin(pin_number, label, pin_mode):
    """发送命令：读取pin。

    参数:
        pin_number (int): Arduino pin (0到69）。
        label (str): 字符串。
        pin_mode (int): 0（数字）或1（模拟）。
    """
    kind = 'read_pin'
    args_ok = _check_arg(kind, pin_number, range(0, 70))
    args_ok = _check_arg(kind, pin_mode, [0, 1])
    if args_ok:
        return _assemble(kind, {'pin_number': pin_number,
                                'label': label,
                                'pin_mode': pin_mode})

@_send
def read_status():
    """发送命令：读取状态。"""
    kind = 'read_status'
    return _assemble(kind, {})

@_send
def reboot():
    """发送命令：重新启动。"""
    kind = 'reboot'
    return _assemble(kind, {})

@_send
def register_gpio(sequence_id, pin_number):
    """发送命令：注册gpio (已弃用)。

    已弃用。使用`app.post('pin_bindings', {'sequence_id': 0, 'pin_num': 0})`替换。

    参数:
        sequence_id (int): Web应用程序序列ID。
            序列必须在注册前同步到Larsen OS。
        pin_number (int): 树莓派GPIO BCM 针脚号。
    """
    kind = 'register_gpio'
    args_ok = _check_arg(kind, pin_number, range(1, 30))
    if args_ok:
        return _assemble(kind, {'sequence_id': sequence_id,
                                'pin_number': pin_number})

@_send
def remove_plugin(package):
    """发送命令：删除插件。

    参数:
        package (str): 要卸载的插件的名称。
    """
    kind = 'remove_plugin'
    return _assemble(kind, {'package': package})

@_send
def set_pin_io_mode(pin_io_mode, pin_number):
    """发送命令：设置pin模式。

    参数:
        pin_io_mode (int): 0（输入）、1（输出）或2（输入上拉）
        pin_number (int): Arduino pin （0到69）。
    """
    kind = 'set_pin_io_mode'
    args_ok = _check_arg(kind, pin_io_mode, [0, 1, 2])
    args_ok = _check_arg(kind, pin_number, range(0, 70))
    if args_ok:
        return _assemble(kind, {'pin_io_mode': pin_io_mode,
                                'pin_number': pin_number})

@_send
def set_servo_angle(pin_number, pin_value):
    """发送命令：设置伺服角度。

    参数:
        pin_number (int): Arduino伺服pin （4、5、6或11）。
        pin_value (int): 伺服角度（0到180）。
    """
    kind = 'set_servo_angle'
    args_ok = _check_arg(kind, pin_number, [4, 5, 6, 11])
    args_ok = _check_arg(kind, pin_value, range(0, 181))
    if args_ok:
        return _assemble(kind, {'pin_number': pin_number,
                                'pin_value': pin_value})

@_send
def set_user_env(key, value):
    """发送命令：设置用户环境变量。

    参数:
        key (str): 键
        value (str): 值
    """
    kind = 'set_user_env'
    body = [assemble_pair(key, value)]
    return _assemble(kind, {}, body)

@_send
def sync():
    """发送命令：同步。"""
    kind = 'sync'
    return _assemble(kind, {})

@_send
def take_photo():
    """发送命令：拍照。"""
    kind = 'take_photo'
    return _assemble(kind, {})

@_send
def toggle_pin(pin_number):
    """发送命令：切换pin。

    参数:
        pin_number (int): Arduino pin （0到69）。
    """
    kind = 'toggle_pin'
    args_ok = _check_arg(kind, pin_number, range(0, 70))
    if args_ok:
        return _assemble(kind, {'pin_number': pin_number})

@_send
def unregister_gpio(pin_number):
    """发送命令：注销GPIO（已弃用）。

    已弃用。使用`app.delete('pin_bindings', _id=0)`替换。

    参数:
        pin_number (int): Arduino pin （0到69）。
    """
    kind = 'unregister_gpio'
    args_ok = _check_arg(kind, pin_number, range(0, 70))
    if args_ok:
        return _assemble(kind, {'pin_number': pin_number})

@_send
def update_plugin(package):
    """发送命令：更新插件。

    参数:
        package (str): 要更新的插件的名称。
    """
    kind = 'update_plugin'
    return _assemble(kind, {'package': package})

@_send
def wait(milliseconds):
    """发送命令：等待。

    参数:
        milliseconds (int): 等待时间（毫秒）
    """
    kind = 'wait'
    return _assemble(kind, {'milliseconds': milliseconds})

@_send
def write_pin(pin_number, pin_value, pin_mode):
    """发送命令：写入pin。

    参数:
        pin_number (int): Arduino pin （0到69）。
        pin_value (int): 写入pin的值。
        pin_mode (int): 0（数字）或1（模拟）。
    """
    kind = 'write_pin'
    args_ok = _check_arg(kind, pin_number, range(0, 70))
    args_ok = _check_arg(kind, pin_mode, [0, 1])
    if args_ok:
        return _assemble(kind, {'pin_number': pin_number,
                                'pin_value': pin_value,
                                'pin_mode': pin_mode})

@_send
def zero(axis):
    """发送命令：零点。

    参数:
        axis (str): ALLOWED_AXIS_VALUES之一。
    """
    kind = 'zero'
    args_ok = _check_arg(kind, axis, ALLOWED_AXIS_VALUES)
    if args_ok:
        return _assemble(kind, {'axis': axis})

def get_current_position(axis='all', _get_bot_state=get_bot_state):
    """获取当前位置。

    参数:
        axis (str, optional): ALLOWED_AXIS_VALUES之一。 默认为 'all'.
    返回：
        'all': Larsen position, 例如, {'x': 0.0, 'y': 0.0, 'z': 0.0}
        'x', 'y', or 'z': Larsen 轴位置, 例如, 0.0
    """
    args_ok = _check_arg('get_current_position', axis, ALLOWED_AXIS_VALUES)
    if args_ok:
        if axis in ['x', 'y', 'z']:
            try:
                return _get_bot_state()['location_data']['position'][axis]
            except KeyError:
                _error('Position `{}` value unknown.'.format(axis))
        else:
            return _get_bot_state()['location_data']['position']

def get_pin_value(pin_number, _get_bot_state=get_bot_state):
    """从pin获取值。

    参数:
        pin_number (int): Arduino pin （0到69）。
    """
    try:
        value = _get_bot_state()['pins'][str(pin_number)]['value']
    except KeyError:
        _error('Pin `{}` value unknown.'.format(pin_number))
    else:
        return value

if __name__ == '__main__':
    send_celery_script({'kind': 'read_status', 'args': {}})
    log('Hello World!')
    send_message('Hello World!', 'success')
    # calibrate('x')
    check_updates('larsen_os')
    emergency_lock()
    emergency_unlock()
    execute(1)
    execute_script('take-photo')
    # factory_reset('larsen_os')
    find_home('x')
    home('all')
    URL = 'https://coding.net/u/zhangyt0906/p/plugin_manifests/git/raw/' \
        'master/packages/take-photo/manifest.json'
    install_plugin(URL)
    install_first_party_plugin()
    COORD = assemble_coordinate(0, 0, 0)
    move_absolute(COORD, 100, COORD)
    move_relative(0, 0, 0, 100)
    # power_off()
    read_pin(1, 'label', 0)
    read_status()
    # reboot()
    # register_gpio(1, 1)
    remove_plugin('plugin')
    set_pin_io_mode(0, 47)
    set_servo_angle(4, 1)
    sync()
    take_photo()
    toggle_pin(1)
    # unregister_gpio(1)
    update_plugin('take-photo')
    wait(100)
    write_pin(1, 1, 0)
    zero('z')
    # 记录位置的首选方法
    log('At position: ({{x}}, {{y}}, {{z}})')
    # 获取计算位置
    POSITION = get_current_position()
    log('At position: ({}, {}, {})'.format(
        POSITION['x'], POSITION['y'], POSITION['z']))
    # 记录pin值的首选方法
    log('pin 13 value: {{pin13}}')
    # 获取用于计算的pin值
    VALUE = get_pin_value(13)
    log('pin 13 value: {}'.format(VALUE))
