from distutils.core import setup

setup(
    name='py-toolbox',
    version='0.1.2',
    author='Daniel Grießhaber',
    author_email='dangrie158@gmail.com',
    url='https://github.com/dangrie158/py-toolbox',
    packages=['pytb', 'pytb.test'],
    license='MIT',
    description='A collection of commonly used python snippets',
    long_description=open('README.md').read(),
    classifiers=[
        'Development Status :: 1 - Planning',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
    ],
)