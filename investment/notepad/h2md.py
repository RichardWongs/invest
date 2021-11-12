import logging
import random
import string
import html2text
import os
import requests

path = r"."
if not os.path.exists(path):
    os.makedirs(path)
os.chdir(path)


def internet_request(url, filename=None):
    if not filename:
        filename = "".join(random.sample(string.ascii_uppercase, 6)) + ".html"
    else:
        filename = filename + ".html"
    try:
        response = requests.get(url)
        with open(filename, 'w', encoding="utf-8") as f:
            f.write(response.text)
    except Exception() as e:
        logging.error(e)
    return filename


def html2md(filename):
    with open(filename, 'r', encoding="utf-8") as f:
        content = f.read()
        md_content = html2text.html2text(content)
    filename_md = md_content.split('\n')[0].replace('##  ', '') + ".md"
    with open(filename_md, 'w', encoding="utf-8") as f:
        f.write(md_content)
    os.remove(filename)


def run(url, filename=None):
    filename = internet_request(url, filename=filename)
    html2md(filename)


if __name__ == "__main__":
    urls =[
        "https://mp.weixin.qq.com/s/K1Nar3eNwB_8GQYUUYAXUg",
        "https://mp.weixin.qq.com/s/EnRQPR3CoPdpMbseCslD6w",
        "https://mp.weixin.qq.com/s/hvZBRyplJaUwxU3JLcf9DQ",
    ]
    for url in urls:
        run(url)



