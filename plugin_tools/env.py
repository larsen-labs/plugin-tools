#!/usr/bin/env python
# coding: utf-8
'''插件工具：环境变量。'''

import os

# Larsen API ENV variables
LARSEN_API_PREFIX = 'LARSEN_API_V2_'
REQUEST_PIPE = os.getenv(LARSEN_API_PREFIX + 'REQUEST_PIPE')
RESPONSE_PIPE = os.getenv(LARSEN_API_PREFIX + 'RESPONSE_PIPE')
# Larsen OS 环境变量
LARSEN_OS_PREFIX = 'LARSEN_OS_'
IMAGES_DIR = os.getenv(LARSEN_OS_PREFIX + 'IMAGES_DIR')
LEGACY_IMAGES_DIR = os.getenv('IMAGES_DIR')
LSOS_VERSION = os.getenv(LARSEN_OS_PREFIX + 'VERSION', '0')
BOT_STATE_DIR = os.getenv(LARSEN_OS_PREFIX + 'STATE_DIR')
# Larsen API 环境变量
LARSEN_API_PREFIX = 'LARSEN_API_'
TOKEN = os.getenv(LARSEN_API_PREFIX + 'TOKEN')
LEGACY_TOKEN = os.getenv('API_TOKEN')

class Env(object):
    '插件环境变量。'

    def __init__(self):
        self.request_pipe = REQUEST_PIPE
        self.response_pipe = RESPONSE_PIPE
        self.images_dir = IMAGES_DIR or LEGACY_IMAGES_DIR
        self.lsos_version = LSOS_VERSION
        self.bot_state_dir = BOT_STATE_DIR
        self.token = TOKEN or LEGACY_TOKEN

    @staticmethod
    def get_version_parts(version_string):
        '从版本字符串中获取major、minor和patch.'
        major_minor_patch = version_string.lower().strip('v').split('-')[0]
        return [int(part) for part in major_minor_patch.split('.')]

    def lsos_at_least(self, major, minor=None, patch=None):
        '确定当前LSOS版本是否满足版本要求。'
        current_version = self.get_version_parts(self.lsos_version)
        required_version = [int(p) for p in [major, minor, patch] if p is not None]
        for part, required_version_part in enumerate(required_version):
            if current_version[part] != required_version_part:
                # 版本不相等。检查是否符合要求。
                return current_version[part] > required_version_part
            # 版本是相等的。
            if required_version_part == required_version[-1]:
                # 没有其他可比较部分。版本相同。
                return True

    def use_v2(self):
        'Determine if the v2 API should be used.'
        return self.lsos_at_least(8)

    def plugin_api_available(self):
        '确定插件API是否可用。'
        if self.use_v2():
            return self.request_pipe is not None and self.response_pipe is not None
        return os.getenv('LARSEN_URL') is not None and self.token is not None
