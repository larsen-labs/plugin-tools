#!/usr/bin/env python
# coding: utf-8
'插件工具导入。'

import os
from .device import log, get_bot_state
from .app import request

with open(os.path.join(os.path.dirname(__file__), 'VERSION')) as version_file:
    VERSION = version_file.read().strip()

__version__ = VERSION

def get_config_value(plugin_name, config_name, value_type=int,
                     _get_state=get_bot_state):
    """获取插件配置输入的值。如果找不到，请尝试使用默认值。

    参数:
        plugin_name (str): 插件的名称。
        config_name (str): 插件输入名称。
    """
    # 将插件名称转换为带“_”的形式
    plugin = plugin_name.replace(' ', '_').replace('-', '_').lower()
    namespaced_config = '{}_{}'.format(plugin, config_name)

    # 尝试分两步确定配置的默认值。
    # 如果在任何一步中都找不到默认值，则假定已设置配置值（如果未设置，则会导致键错误）。
    # 步骤1。搜索配置数据。
    try:  # 检索插件清单数据
        manifest = _get_state()['process_info']['plugins'][plugin_name]
    except KeyError:
        log('Plugin manifest for `{}` not found.'.format(plugin_name), 'warn')
        return value_type(os.environ[namespaced_config])
    else:  # 找到配置数据。
        configs = manifest['config']

    # 步骤2。搜索配置名称。
    try:  # 检索默认配置值
        [default] = [c['value'] for c in configs if c['name'] == config_name]
    except ValueError:
        log('Config name `{}` not found.'.format(config_name), 'warn')
        return value_type(os.environ[namespaced_config])

    # 已确定默认值。
    # 搜索设定值。
    try:  # 检索设置配置值
        value = value_type(os.environ[namespaced_config])
    except KeyError:
        log('Using the default value for `{}`.'.format(config_name))
        value = default
    return value
