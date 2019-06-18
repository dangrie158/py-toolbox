from setuptools import setup
from os import path
import re

def read(fname):
    return open(path.join(path.dirname(__file__), fname)).read()

def get_version():
    with open('CHANGELOG.rst') as changelog: 
        for line in changelog: 
            if re.match(r'^\d+\.\d+\.\d+$', line):
                return line

setup(
    name='py-toolbox',
    version=get_version(),
    author='Daniel Grießhaber',
    author_email='dangrie158@gmail.com',
    url='https://github.com/dangrie158/py-toolbox',
    packages=['pytb', 'pytb.test'],
    include_package_data=True,
    license='MIT',
    description='A collection of commonly used python snippets',
    long_description=read('README.rst'),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points = {
        'console_scripts': ['pytb=pytb.__main__:main'],
    }
)
