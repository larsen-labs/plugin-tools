#!/usr/bin/env python
# coding: utf-8
"""插件工具包设置。"""

import os
from setuptools import setup

with open(os.path.join('plugin_tools', 'VERSION')) as version_file:
    VERSION = version_file.read().strip()

with open('README.md') as f:
    README = f.read()

if __name__ == '__main__':
    setup(name='plugin_tools',
          version=VERSION,
          description='Plugin convenience functions for use in Larsen OS.',
          long_description=README,
          long_description_content_type='text/markdown',
          url='https://gitee.com/zhangyt0906/plugin-tools',
          project_urls={
              'Larsen': 'https://funfarm.fun/'
          },
          author='Larsen Inc.',
          license='MIT',
          author_email='plugin.tools@funfarm.fun',
          packages=['plugin_tools'],
          include_package_data=True,
          classifiers=[
              'Development Status :: 3 - Alpha',
              'License :: OSI Approved :: MIT License',
              'Programming Language :: Python',
              'Programming Language :: Python :: 2',
              'Programming Language :: Python :: 2.7',
              'Programming Language :: Python :: 3',
              'Programming Language :: Python :: 3.7',
          ],
          keywords=['larsen', 'python'])
