#!/usr/bin/env python3

# -*- coding: utf8 -*-

import sys
import requests
import re

MAX_DEPTH = 12 # максимальный уровень вложенности каталогов веб-сервера репозитория
MAX_RETRIES = 5

REPOS_LIST = [
    # --- Rosa12 ---
    {
        "name": "rosa12",
        "extensions_only": [".rpm"], # если не пустой массив, то составить список файлов только с этими расширениями
        "extensions_skip": [], # не помещать в итоговый список файлв с этими расширениями
        "dirs_skip": ["___REMOVED", "SRPMS"], # не заходить в эти каталоги
        "urls": [
            "http://mirror.rosalab.ru/rosa/rosa2021.1/repository/",
            "-http://mirror.rosalab.ru/rosa/rosa2021.1/iso", # url-ы начинающиеся с минуса не рассматривать
            "-http://mirror.rosalab.ru/rosa/rosa2021.1",
            "-http://mirror.rosalab.ru/rosa/rosa2021.1/repository/aarch64/main"
        ]
    },

    # --- Ubuntu ---
    {
        "name": "ubuntu",
        "extensions_only": [".deb"],
        "extensions_skip": [],
        "dirs_skip": [],
        "urls": [
            "http://archive.ubuntu.com/ubuntu/pool/main"
        ]
    },

    # --- Astra Orel ---
    {
        "name": "astra-orel",
        "extensions_only": [".deb"],
        "extensions_skip": [],
        "dirs_skip": [],
        "urls": [
            "https://dl.astralinux.ru/astra/stable/orel/repository/pool/main"
        ]
    },

    # --- OpenSuse ---
    {
        "name": "opensuse-15.4",
        "extensions_only": [".rpm"],
        "extensions_skip": [],
        "dirs_skip": [],
        "urls": [
            "https://download.opensuse.org/distribution/leap/15.4/repo"
        ]
    },

    # --- Debian ---
    {
        "name": "debian",
        "extensions_only": [".deb"],
        "extensions_skip": [],
        "dirs_skip": [],
        "urls": [
            "http://ftp.debian.org/debian/pool/main/"
        ]
    }
]

def parse_page(url, f, extensions_only, extensions_skip, dirs_skip, processed_dirs, depth = 0):
    if not len(url) > 0:
        return # url - пустая строка
    if url[0] == "-":
        return # не обрабатывать адрес начинающийся с -
    if MAX_DEPTH >= 0 and depth > MAX_DEPTH:
        return # достигнут максимальный уровень вложенности
    if url[-1] != "/":
        url += "/" # если url не заканчивается на слеш - добавить его
    if url in processed_dirs:
        return # этот каталог уже обрабатывался
    processed_dirs.append(url) # добавить новый каталог в список обработанных каталогов

    space = ""
    for _ in range(depth):
        space += "  "
    print("{}Enter to {}" . format(space, url))
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    req = session.get(url)
    if req.status_code != 200:
        print("ERROR! Cannot request page [{}]" . format(url))
        return
    s = req.text
    matches = re.findall(r"<a href=\"(.*?)\"", s, re.MULTILINE | re.IGNORECASE)
    new_dirs_list = []
    for one_match in matches:
      if len(one_match) <= 1:
          continue
      if one_match[0] == "?":
          continue
      if one_match[0] == "/":
          continue
      if one_match.startswith("."):
          continue
      #if one_match.startswith(".."):
      #    continue
      if one_match.startswith("http://"):
          continue
      if one_match.startswith("https://"):
          continue

      inner_url = url + one_match
      if one_match[-1] == "/":
          # заканчивается на слеш - это каталог
          if one_match in dirs_skip:
              continue
          new_dirs_list.append(inner_url)
      else:
          # файл
          if skip_file(one_match, extensions_only, extensions_skip):
              continue
          f.write(inner_url + "\n")
    for url in new_dirs_list:
        # переход в следующие подкаталоги
        parse_page(url, f, extensions_only, extensions_skip, dirs_skip, processed_dirs, depth+1)


#-------------- Проверить необходимость добавления этого файла в список файлов на основе его расширения ------------------
def skip_file(filename, extensions_only, extensions_skip):
    if len(extensions_only) > 0:
        # задан список принимаемых расширений, файл должен иметь расширение из этого списка, иначе он не добавляется в список файлов
        for one_extension in extensions_only:
            if filename.endswith(one_extension):
                return False # расширение файла совпадает с одним из тех, которые принимаются - нельзя игнорировать этот файл
        return True # расширение файла не совпадает ни с одним из допустимых расширений - игнорировать этот файл
    # не задан список допустимых расширений
    for one_extension in extensions_skip:
        if filename.endswith(one_extension):
            return True # расширение файла совпадает с одним из исключаемых - игнорировать этот файл
    return False


#------------------------------main-----------------------------
if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Repository name is not specified. Available:")
        for rep in REPOS_LIST:
            print("\t" + rep["name"])
        exit(0)
    REPO = None
    for one_repo in REPOS_LIST:
        if one_repo["name"] == sys.argv[1]:
            REPO = one_repo
            break
    if REPO == None:
        print("Unknown repository name: \"{}\"" . format(sys.argv[1]))
        exit(1)

    filename = REPO["name"] + ".txt";
    print("-------------------------------------------")
    print("Files will be stored to {}. MaxDepth={}" . format(filename, MAX_DEPTH))
    print("-------------------------------------------")
    f = open(filename, "wt")

    # добавить слеш в конце каждого исколючаемого каталога, если его там нет
    for i in range(len(REPO["dirs_skip"])):
        if REPO["dirs_skip"][i][-1] != "/":
            REPO["dirs_skip"][i] += "/"

    processed_dirs = []
    for url in REPO["urls"]:
        parse_page(url, f, REPO["extensions_only"], REPO["extensions_skip"], REPO["dirs_skip"], processed_dirs)
    f.write("\n-------------------- Directories: ------------------------------\n\n");

    # список каталогов тоже записать в файл с результатами
    processed_dirs.sort()
    for dirname in processed_dirs:
        f.write(dirname + "\n")
    f.close()
    print("--------------- complete ------------------")
