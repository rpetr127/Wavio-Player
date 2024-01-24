import os
import re
from pprint import pprint

import urllib.request


class Datas(object):
    def __init__(self, files=None, urls=None, content=''):
        self.files = files
        self.urls = urls
        if self.files:
            self.files = Files(files)
        if self.urls:
            self.urls = Urls(urls)
            self.content = content
        else:
            self.urls = None
            self.content = None


class Files:
    def __init__(self, files=None):
        self.files = files

    def __getitem__(self, item):
        cls = FileMetadata(self.files[item])
        return cls
    
    def __len__(self):
        return len(self.files)

class Urls:
    def __init__(self, urls=None):
        self.urls = urls

    def __getitem__(self, item):
        cls = StreamMetadata(self.urls[item])
        return cls


class FileMetadata:
    def __init__(self, item=None):
        # if "\n" in item:
        #     self.item = item.split('\n')
        # else:
        self.item = item

    @property
    def path(self):
        # if len(self.item) >= 2:
        #     self._path = self.item[1]
        # else:
        self._path = self.item
        return self._path

    @property
    def name(self):
        self._name = os.path.split(self.path)[-1]
        return(self._name)

    @property
    def title(self):
        if len(self.item) >= 2:
            self._title = self.item[0].split(',')[1]
        else:
            self._title = None
        return self._title

    @property
    def duration(self):
        self._duration = self.item[0].split(',')[0]
        return self._duration

    @path.setter
    def file(self, value):
        self._file = ''

    @title.setter
    def title(self, value):
        self._title = ''

    @duration.setter
    def duration(self, value):
        self._duration = ''


class StreamMetadata:
    def __init__(self, item=None):
        self.item = item

    @property
    def picture(self):
        match = re.search(r'\"(https?:\/\/[\w\.\/:]+)\"', self.item)
        if match:
            self._picture = match.group(1)
            return self._picture

    @property
    def title(self):
        self._title = self.item.split('\n')[0].split(',')[1]
        return self._title


    @property
    def url(self):
        match = re.search(r'(https?:\/\/[\w\-\.\/:]*)', self.item)
        if match:
            self._url = match.group(0)
            print(self._url)
            return self._url


    @url.setter
    def url(self, value):
        self._url = ''

    @picture.setter
    def picture(self, value):
        self._picture = ''


def load(url=None, filepath=None):
    if url:
        response = urllib.request.urlopen(url)
        metadata = response.read()
    else:
        file = open(filepath, 'r', encoding='utf-8', errors='ignore')
        metadata = file.read()
    return split(metadata)


def split(metadata):
    files = None
    urls = None
    if re.search("#EXTM3U", metadata):
        lst = re.split(r'((?<=\#EXTM3U\n)(\#EXTINF\:)*)', metadata)
    else:
        lst = re.split(r"\n", metadata)
    if not re.search(r'https?', lst[0]):
        files = lst
    if re.search(r'https?', lst[0]):
        urls = lst
    data = Datas(files, urls)
    return data