#!/usr/bin/env python3.8
import re
import logging
from pathlib import Path

whitelist_file = "data//vip_whitelist.txt"
# 初始化文件目录
index_cache_web_dir = Path('/tmp/myGPTReader/cache_web/')

MAX_THREAD_MESSAGE_HISTORY = 10

# 提取普通 text 的文本和链接
def extract_text_and_links_from_content(input_dict):
    input_str = input_dict.get("text", "")
    # 匹配文本中的链接
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    url_match = url_pattern.search(input_str)
    
    if url_match:
        # 提取链接
        link = url_match.group(0)
        
        # 删除链接，提取文案
        text = url_pattern.sub('', input_str).strip()

        return {"text": [text], "link": [link]}
    else:
        return {"text": [input_str], "link": []}

# 提取话题群类型 post 的文本和链接
def extract_post_text_and_links_from_content(input_dict):
    content_list = input_dict.get('content', '[]')

    extracted_text = []
    extracted_links = []
    
    for item in content_list:
        for element in item:
            if element.get('tag') == 'text':
                extracted_text.append(element.get('text'))
            elif element.get('tag') == 'a':
                extracted_links.append(element.get('href'))
    
    return {"text": extracted_text,"link": extracted_links}

def insert_space(text):
	
    # Handling the case between English words and Chinese characters
    text = re.sub(r'([a-zA-Z])([\u4e00-\u9fa5])', r'\1 \2', text)
    text = re.sub(r'([\u4e00-\u9fa5])([a-zA-Z])', r'\1 \2', text)

    # Handling the situation between numbers and Chinese
    text = re.sub(r'(\d)([\u4e00-\u9fa5])', r'\1 \2', text)
    text = re.sub(r'([\u4e00-\u9fa5])(\d)', r'\1 \2', text)

    # handling the special characters
    text = re.sub(r'([\W_])([\u4e00-\u9fa5])', r'\1 \2', text)
    text = re.sub(r'([\u4e00-\u9fa5])([\W_])', r'\1 \2', text)

    text = text.replace('  ', ' ')

    return text

def setup_logger(name, log_level=logging.INFO):
    # 检查是否已经添加了 console handler
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(log_level)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)
    return logger

def is_authorized(user_id: str) -> bool:
    with open(whitelist_file, "r") as f:
        return user_id in f.read().splitlines()
    
# 更新文本、链接和文件，用户建立问题以及向量索引
def update_thread_history(thread_message_history, parent_thread_id, message_str=None, urls=None, file=None, is_use_web_gpt=False):
    if urls is not None:
        thread_message_history[parent_thread_id]['context_urls'].update(urls)
    if file is not None:
        thread_message_history[parent_thread_id]['file'] = file
    if message_str is not None:
        # thread_message_history[parent_thread_id]['dialog_texts'] = message_str
        if parent_thread_id in thread_message_history:
            urls = thread_message_history[parent_thread_id]['context_urls']
            file = thread_message_history[parent_thread_id]['file']
            # is_use_web_gpt 自动利用 gpt 的上下文能力，如果是上传文件或者是 url 模式，直接根据向量相似度匹配回答问题
            if is_use_web_gpt or file is not None or len(urls) > 0:
                thread_message_history[parent_thread_id]['dialog_texts'] = message_str
            else:
                dialog_texts = thread_message_history[parent_thread_id]['dialog_texts']
                dialog_texts = dialog_texts + message_str
                if len(dialog_texts) > MAX_THREAD_MESSAGE_HISTORY:
                    dialog_texts = dialog_texts[-MAX_THREAD_MESSAGE_HISTORY:]
                thread_message_history[parent_thread_id]['dialog_texts'] = dialog_texts
            
        else:
            thread_message_history[parent_thread_id]['dialog_texts'] = message_str

def dialog_context_keep_latest(dialog_texts, max_length=1):
    if len(dialog_texts) > max_length:
        dialog_texts = dialog_texts[-max_length:]
    return dialog_texts

def format_dialog_messages(messages):
    return "\n".join(messages)