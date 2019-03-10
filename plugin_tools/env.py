#!/usr/bin/env python

'''插件工具：环境变量。'''

import os

# Larsen OS 环境变量
LARSEN_OS_PREFIX = 'LARSEN_OS_'
IMAGES_DIR = os.getenv('IMAGES_DIR')
LSOS_VERSION = os.getenv(LARSEN_OS_PREFIX + 'VERSION', '0')

# Larsen API 环境变量
TOKEN = os.getenv('API_TOKEN')

class Env(object):
    '插件环境变量。'

    def __init__(self):
        self.images_dir = IMAGES_DIR
        self.lsos_version = LSOS_VERSION
        self.token = TOKEN

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

    def plugin_api_available(self):
        '确定插件API是否可用。'
        return os.getenv('PLUGIN_URL') is not None and self.token is not None
