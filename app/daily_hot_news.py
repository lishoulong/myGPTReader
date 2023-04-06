import json
import os
from datetime import date
import logging
import feedparser
import html2text
import concurrent.futures

from gpt import get_answer_from_llama_web
# 获取当前文件的绝对路径
current_file_path = os.path.abspath(__file__)
# 获取当前文件所在的目录
current_dir = os.path.dirname(current_file_path)
# 构建 data/hot_news_rss.json 的绝对路径
data_file_path = os.path.join(current_dir, "data", "hot_news_rss.json")
with open(data_file_path, "r") as f:
    rss_urls = json.load(f)

TODAY = today = date.today()
MAX_DESCRIPTION_LENGTH = 300
MAX_POSTS = 5
gpt_keys = ['trendings']

def cut_string(text):
    words = text.split()
    new_text = ""
    count = 0
    for word in words:
        if len(new_text + word) > MAX_DESCRIPTION_LENGTH:
            break
        new_text += word + " "
        count += 1

    return new_text.strip() + '...'

def get_summary_from_gpt_thread(url):
    news_summary_prompt = '请用中文简短概括这篇文章的内容。'
    return str(get_answer_from_llama_web([news_summary_prompt], [url]))

def get_summary_from_gpt(url):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(get_summary_from_gpt_thread, url)
        return future.result(timeout=300)

def get_description(news_key, entry):
    gpt_answer = None
    if news_key in gpt_keys:
        try:
            gpt_answer = get_summary_from_gpt(entry.link)
        except Exception as e:
            logging.error(e)
    if gpt_answer is not None:
        summary = 'AI: ' + gpt_answer
    else:
        summary = cut_string(get_text_from_html(entry.summary))
    return summary

def get_text_from_html(html):
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    text_maker.ignore_tables = False
    text_maker.ignore_images = True
    return text_maker.handle(html)

def get_post_urls_with_title(news_key, rss_url):
    feed = feedparser.parse(rss_url)
    updated_posts = []
    for entry in feed.entries:
        published_time = entry.published_parsed if 'published_parsed' in entry else None
        # published_date = date(published_time.tm_year,
        #                       published_time.tm_mon, published_time.tm_mday)
        updated_post = {}
        updated_post['title'] = entry.title
        # updated_post['summary'] = entry.title
        updated_post['summary'] = get_description(news_key, entry)
        updated_post['url'] = entry.link
        updated_post['publish_date'] = published_time
        updated_posts.append(updated_post)
        if len(updated_posts) >= MAX_POSTS:
            break
        
    return updated_posts

def build_slack_blocks(title, news):
    items = {
        "title": title
    }
    blocks = []
    for index, news_item in enumerate(news, start=1):
        news_block = [
            {
                "tag": "text",
                "text": f"{index}. 标题：*{news_item['title']}*",
            },
            {
                "tag": "text",
                "text": f"\n简介：{news_item['summary']}",
            },
            {
                "tag": "a",
                "href": news_item['url'],
                "text": f"\n原文链接：<{news_item['url']}>"
            },
            {
                "tag": "text",
                "text": f"\n更新时间：{news_item['publish_date']}",
            }
        ]
        blocks.append(news_block)
    items["content"] = blocks
    return items

def build_hot_news_blocks(news_key):
    rss = rss_urls[news_key]['rss']['hot']
    print(f"rssrss=====>>>{rss}")
    hot_news = get_post_urls_with_title(news_key, rss['url'])
    hot_news_blocks = build_slack_blocks(
        rss['name'], hot_news)
    return hot_news_blocks

def build_all_news_block():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 使用字典推导式来创建一个包含所有 rss 任务的字典
        rss_tasks = {key: executor.submit(build_hot_news_blocks, key) for key in rss_urls}

        # 使用列表推导式来获取所有任务的结果
        all_news_blocks = [task.result() for task in rss_tasks.values()]

        return all_news_blocks
