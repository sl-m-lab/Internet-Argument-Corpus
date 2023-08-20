#!/usr/bin/env python3

from setuptools import setup, find_packages


version = '1.0.2'  # make sure a tag is added if uploaded to PyPI!!!!!!!!!
url = 'https://bitbucket.org/nlds_iac/internet-argument-corpus-2'

setup(name='InternetArgumentCorpus',
      version=version,
      description='The Internet Argument Corpus (IAC) version 2 is a collection of corpora for research in political debate on internet forums.',
      url=url,
      download_url=url+'/get/'+version+'.tar.gz',
      license='MIT',
      author='Rob Abbott',
      author_email='abbott@soe.ucsc.edu',
      packages=find_packages(),
      install_requires=['sqlalchemy', 'mysqlclient', 'inflect'],
      extras_require={'html': ['bs4', 'python-dateutil', 'lxml']},
      keywords=['corpus'],
      )
