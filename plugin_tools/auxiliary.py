#!/usr/bin/env python
# coding: utf-8
'''插件工具：辅助实用程序。'''

from __future__ import print_function
import re
from string import punctuation

class Color(object):
    """终端输出的颜色代码。"""

    def __init__(self):
        self.green = self.get_color_code('green')
        self.red = self.get_color_code('red')
        self.yellow = self.get_color_code('yellow')
        self.magenta = self.get_color_code('magenta')
        self.cyan = self.get_color_code('cyan')
        self.blue = self.get_color_code('blue')
        self.bold = self.get_color_code('bold')
        self.reset = self.get_color_code('reset')

    color_number = {
        'green': 32,
        'red': 31,
        'yellow': 33,
        'magenta': 35,
        'cyan': 36,
        'blue': 34,
        'reset': 0,
        'bold': 1,
        }

    def get_color_code(self, string):
        """获取要在字符串中使用的颜色代码。

        参数:
            string (str): 颜色名称 (color_number的键).
        """
        return '\033[{}m'.format(self.color_number[string])

    def colorize_celery_script(self, kind, args, body=None):
        """Celery 脚步的终端打印颜色

        参数:
            kind (str): Celery 脚本类。
            args (dict): Celery 脚本参数
            body (list, optional): Celery 脚本正文。默认为 None。
        """
        colorized_kind = "'kind': '{magenta}{kind}{reset}'".format(
            magenta=self.magenta, kind=kind, reset=self.reset)
        colorized_args = ", 'args': {cyan}{args}{reset}".format(
            cyan=self.cyan, args=args, reset=self.reset)
        colorized_body = ", 'body': {blue}{body}{reset}".format(
            blue=self.blue, body=body, reset=self.reset)
        to_print = "{{{kind}{args}{body}}}".format(
            kind=colorized_kind,
            args=colorized_args,
            body=colorized_body if body is not None else '')
        return to_print

    def error(self, text):
        """使错误文本变为红色。

        参数:
            text (str): 文本变为红色。
        """
        return '{red}{text}{reset}'.format(
            red=self.red, text=text, reset=self.reset)

    def make_bold(self, text):
        """使文本变为粗体。

        参数:
            text (str): 要加粗的文本。
        """
        return '{bold}{text}{reset}'.format(
            bold=self.bold, text=text, reset=self.reset)

    def colorize_response_code(self, status_code):
        """为HTTP响应状态代码上色。

        参数:
            status_code (int): HTTP状态代码。
                4xx -> 红
                2xx -> 绿
                other -> 粗
        """
        if str(status_code).startswith('4'):
            color = self.red
        elif str(status_code).startswith('2'):
            color = self.green
        else:
            color = self.bold
        return '{color}{status_code}{reset}'.format(
            color=color, status_code=status_code, reset=self.reset)

def snake_case(string):
    '将字符串转换为 snake_case.'
    string = re.sub('(.)([A-Z][a-z])', r'\1_\2', string)  # *Aa -> *_Aa
    string = re.sub('(.)([0-9]+)', r'\1_\2', string)  # *00 -> *_00
    string = string.replace('-', '_')  # A-B -> A_B
    string = ''.join(c for c in string if c not in punctuation.replace('_', ''))
    string = string.replace(' ', '_').strip('_').lower()  # _A B -> a_b
    string = re.sub('_+', '_', string)  # a__b -> a_b
    return string

if __name__ == '__main__':
    COLOR = Color()
    for color_name, number in COLOR.color_number.items():
        print(u'{color}  {block}{bold}{block}{color}' \
        ' {label} {bold}(bold){reset}'.format(
            color=COLOR.get_color_code(color_name),
            bold=COLOR.bold,
            label=color_name,
            block=u'\u2588' * 2,
            reset=COLOR.reset))
    print()
    print(COLOR.colorize_celery_script('kind', '{}'))
    print(COLOR.colorize_response_code(200))
    print(COLOR.colorize_response_code(300))
    print(COLOR.colorize_response_code(400))
    print(COLOR.make_bold('bold'))
    ERROR = COLOR.error('ERROR')
    print(ERROR)
    OK = COLOR.green + 'OK' + COLOR.reset
    print(OK)
    print()
    STRING = snake_case("ABCd12-34's A_BC-D")
    print(STRING, end=' ')
    print(OK if STRING == "ab_cd_12_34s_a_bc_d" else ERROR)
