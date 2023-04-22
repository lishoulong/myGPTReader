import json
import os
from flask import jsonify
from utils.thread import (extract_text_and_links_from_content, insert_space, setup_logger,
                          extract_post_text_and_links_from_content, update_thread_history, dialog_context_keep_latest)
from utils.filesystem import get_file_extension, md5_file_con, index_cache_file_dir
from utils.audio import identify_audio_format, convert_ogg_to_mp3_binary
from utils.rate_limiter import RateLimiter
from utils.ttl_set import TtlSet
from api import MessageApiClient
from event import MessageReceiveEvent, UrlVerificationEvent
from gpt import (get_answer_from_chatGPT, get_answer_from_web_embedding,
                 get_answer_from_file_embedding, get_text_from_whisper)
from config import APP_ID, APP_SECRET, VERIFICATION_TOKEN, LARK_HOST
from daily_hot_news import build_all_news_block
from speak import get_video
# from ocr import image_meme, image_ocr

logger = setup_logger('my_gpt_reader_server')

thread_message_history = {}
message_api_client = MessageApiClient(APP_ID, APP_SECRET, LARK_HOST)

limiter_message_per_user = 50
limiter_time_period = 3600
limiter = RateLimiter(limit=limiter_message_per_user,
                      period=limiter_time_period)

PARENT_WEB_GPT_MAPPING_FILE = index_cache_file_dir / "parent_web_gpt_mapping.json"
# 创建用户 TtlSet 实例字典
user_ttl_sets = {}


def process_file_message(message, thread_id, create_time, open_id):
    filetype_extension_allowed = ['epub', 'pdf', 'text', 'docx', 'markdown']
    file_content = json.loads(message["content"])
    file_key = file_content["file_key"]
    file_name = file_content["file_name"]
    file_ext = get_file_extension(file_name)

    if file_ext not in filetype_extension_allowed:
        message_api_client.reply_text_with_message_id(
            thread_id,
            json.dumps(
                {"text": f'this filetype is not supported, please upload a file with extension [{", ".join(filetype_extension_allowed)}]'}),
            create_time
        )
        return None

    temp_file_path = index_cache_file_dir / open_id
    temp_file_path.mkdir(parents=True, exist_ok=True)
    temp_file_filename = temp_file_path / file_name
    result = download_and_save_file(
        temp_file_filename, thread_id, file_key, create_time)
    # 如果 download_and_save_file 返回 False，表示文件大小超过限制，直接返回 None
    if not result:
        return None
    temp_file_md5 = md5_file_con(temp_file_filename)
    file_md5_name = index_cache_file_dir / (temp_file_md5 + '.' + file_ext)
    if not file_md5_name.exists():
        logger.info(f'=====> Rename file to {file_md5_name}')
        temp_file_filename.rename(file_md5_name)

    return file_md5_name


def process_audio_message(message, thread_id, create_time, open_id):
    file_content = json.loads(message["content"])
    file_key = file_content["file_key"]
    duration = file_content["duration"]

    if duration >= 50000:
        message_api_client.reply_text_with_message_id(
            thread_id,
            json.dumps(
                {"text": f'<@{open_id}>, this audio duration is beyond max time limit of 50s'}),
            create_time
        )
        return None

    temp_file_path = index_cache_file_dir / open_id
    temp_file_path.mkdir(parents=True, exist_ok=True)
    temp_file_filename = temp_file_path / f"{file_key}.mp3"
    download_and_convert_audio(temp_file_filename, thread_id, file_key)

    voicemessage = get_text_from_whisper(temp_file_filename)
    logger.info(f'提取音频文字：{voicemessage}')

    return voicemessage


def download_and_save_file(file_path, thread_id, file_key, create_time):
    response = message_api_client.downLoadFile(thread_id, file_key, 'file')

    # 检查文件大小是否超过 500KB
    file_size_kb = len(response.content) / 1024
    if file_size_kb > 500:
        # 返回提示信息
        message_api_client.reply_text_with_message_id(
            thread_id,
            json.dumps(
                {"text": f'the file size exceeds the limit of 500KB, please upload a smaller file.'}),
            create_time
        )
        return False

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(response.content)
        logger.info(f'=====> Downloaded file to save {file_path}')

    return True


def download_and_convert_audio(file_path, thread_id, file_key):
    with open(file_path, "wb") as f:
        response = message_api_client.downLoadFile(thread_id, file_key, 'file')
        file_ext = identify_audio_format(response.content)
        audio_content = convert_ogg_to_mp3_binary(response.content, file_ext)
        logger.info(
            f'=====> Downloaded file to save {file_path}, file_ext========> {file_ext}')
        f.write(audio_content)


def handle_message_type(message_type, message, thread_id, create_time, open_id):
    file_md5_name = None
    voicemessage = None

    if message_type == 'file':
        file_md5_name = process_file_message(
            message, thread_id, create_time, open_id)
    elif message_type == 'audio':
        voicemessage = process_audio_message(
            message, thread_id, create_time, open_id)
    elif message_type not in ["text", "post"]:
        logger.warning("Other types of messages have not been processed yet")
        message_api_client.reply_text_with_message_id(
            thread_id,
            json.dumps({"text": f'不接受如下类型为：{message["message_type"]}的消息'}),
            create_time
        )
        return jsonify(), None, None

    return file_md5_name, voicemessage


def message_receive_event_handler(req_data: MessageReceiveEvent):
    event = req_data.event
    sender_id = event['event']["sender"]["sender_id"]
    open_id = sender_id["open_id"]
    message = event['event']["message"]
    thread_id = message["message_id"]
    create_time = event['header']["create_time"]
    message_type = message["message_type"]
    if not limiter.allow_request(open_id):
        # 如果用户不在 TtlSet 中，向用户发送提示信息并将用户添加到 TtlSet
        if open_id not in user_ttl_sets:
            user_ttl_sets[open_id] = TtlSet()
        if open_id not in user_ttl_sets[open_id]:
            message_api_client.reply_text_with_message_id(
                thread_id,
                json.dumps(
                    {"text": f'<@{open_id}>, you have reached the limit of {limiter_message_per_user} messages per {limiter_time_period / 3600} hour, please try again later.'}),
                create_time
            )
            user_ttl_sets[open_id].add(open_id, limiter_time_period)
        return jsonify()
    logger.info(f'message_type-{message_type}')
    file_md5_name, voicemessage = handle_message_type(
        message_type, message, thread_id, create_time, open_id)

    # 更新 thread_history
    parent_thread_id = message.get("root_id", thread_id)
    if parent_thread_id not in thread_message_history:
        thread_message_history[parent_thread_id] = {
            'dialog_texts': [], 'context_urls': set(), 'file': None}
    if file_md5_name is not None:
        # 上传文件的话
        update_thread_history(thread_message_history,
                              parent_thread_id, None, None, file_md5_name)
    if voicemessage is not None:
        update_thread_history(thread_message_history,
                              parent_thread_id, [voicemessage])
    # 处理文本和链接
    file_content = json.loads(message["content"])
    result = None
    is_use_web_gpt = False
    if message_type == 'text' and "text" in file_content:
        result = extract_text_and_links_from_content(file_content)
    elif message_type == 'post' and "content" in file_content:
        result = extract_post_text_and_links_from_content(file_content)

    if result is not None:
        item_text = result["text"]
        item_urls = result["link"]
        is_first_message = thread_id == parent_thread_id
        if is_first_message:
            is_use_web_gpt = item_text[0].strip().startswith('/v4')
            # 把 parent_thread_id 对应的 is_use_web_gpt 写入内存以及文件系统中
            write_web_gpt_file(parent_thread_id, is_use_web_gpt)
        else:
            # 非首次，parent_thread_id 如果是 is_use_web_gpt，那么直接延续
            try:
                parent_web_gpt_mapping = get_web_gpt_file()
                is_use_web_gpt = parent_web_gpt_mapping[str(parent_thread_id)]
            except Exception as e:
                # 如果上传文件或者是语音，那么不需要处理 is_use_web_gpt 的情况，后续不会消费这个字段
                err_msg = f'get is_use_web_gpt fail: {e}'
                logger.error(err_msg)
        logger.info(
            f"item_text -> {item_text[0].strip()},is_use_web_gpt -> {is_use_web_gpt}")
        update_thread_history(thread_message_history, parent_thread_id,
                              item_text, item_urls, None, is_use_web_gpt)

    # 处理 GPT 请求
    handle_gpt_request(parent_thread_id, thread_id, create_time,
                       open_id, voicemessage, is_use_web_gpt)

    return jsonify()


def write_web_gpt_file(parent_thread_id, is_use_web_gpt=True):
    parent_web_gpt_mapping = get_web_gpt_file()
    parent_web_gpt_mapping[str(parent_thread_id)] = is_use_web_gpt

    with open(PARENT_WEB_GPT_MAPPING_FILE, 'w') as f:
        json.dump(parent_web_gpt_mapping, f)


def get_web_gpt_file():
    parent_web_gpt_mapping = {}
    if os.path.exists(PARENT_WEB_GPT_MAPPING_FILE):
        with open(PARENT_WEB_GPT_MAPPING_FILE, 'r') as f:
            parent_web_gpt_mapping = json.load(f)
    return parent_web_gpt_mapping


def handle_gpt_request(parent_thread_id, thread_id, create_time, open_id, voicemessage, is_use_web_gpt):
    urls = thread_message_history[parent_thread_id]['context_urls']
    file = thread_message_history[parent_thread_id]['file']
    text = thread_message_history[parent_thread_id]['dialog_texts']

    logger.info('=====> Current thread conversation messages are:')
    logger.info(thread_message_history[parent_thread_id])
    is_first_message = thread_id == parent_thread_id
    try:
        if file is not None:
            gpt_response = get_answer_from_file_embedding(
                dialog_context_keep_latest(text), file, is_first_message)
        elif len(urls) > 0:
            gpt_response = get_answer_from_web_embedding(
                text, list(urls), is_first_message)
        else:
            gpt_response = get_answer_from_chatGPT(
                text, parent_thread_id, thread_id, is_use_web_gpt)

        update_thread_history(thread_message_history, parent_thread_id, [
                              'AI: %s' % insert_space(f'{gpt_response}')])
        logger.info(f"请求成功-接下来调用接口发送消息")
        # message_api_client.reply_text_with_message_id(thread_id, json.dumps({"text": f'{str(gpt_response)}'}), create_time)
        # 如果问题是通过语音问的，那么回话也可以使用语音，否则使用文字
        if voicemessage is None:
            message_api_client.reply_text_with_message_id(
                thread_id, json.dumps({"text": f'{str(gpt_response)}'}), create_time)
        else:
            voice_file_path, duration = get_video(str(gpt_response))
            file_name = os.path.basename(voice_file_path)
            logger.info(f'=====> Voice file path is {voice_file_path}')
            # Read the file content as binary data
            with open(voice_file_path, 'rb') as file:
                file_content = file.read()
            # 把音频文件上传得到 file_key
            resp = message_api_client.upload_file(
                files=file_content, file_name=file_name)
            response_dict = resp.json()
            data = response_dict.get("data", {})
            file_key = data.get("file_key", "")
            print(f"file_keyfile_key => {file_key}")
            # 回复消息内容体为 file_key
            message_api_client.reply_text_with_message_id(thread_id, json.dumps(
                {"file_key": file_key}), create_time, message_type="audio")
    except Exception as e:
        err_msg = f'Task failed with error: {e}'
        print(err_msg)
        message_api_client.reply_text_with_message_id(
            thread_id, json.dumps({"text": f'<@{open_id}>, {err_msg}'}), create_time)

    return

# 授权 url 的验证


def request_url_verify_handler(req_data: UrlVerificationEvent):
    # url verification, just need return challenge
    if req_data.event.token != VERIFICATION_TOKEN:
        raise Exception("VERIFICATION_TOKEN is invalid")
    return jsonify({"challenge": req_data.event.challenge})

# 推送消息


def schedule_news():
    logger.info("=====> Start to send daily news!")
    all_news_blocks = build_all_news_block()
    for news_item in all_news_blocks:
        try:
            # 发起网络请求
            result = message_api_client.webhookRequest(news_item)
            logger.info(f"schedule_news ->>>>>>>>>>>>>>>>>{result}")
        except Exception as e:
            logger.error(f"schedule_news error -> {e}")


def refine_image(buffer):
    try:
        # 把 buffer 转化为文案
        print(f"refine_image")
        # str_list = image_ocr(buffer)
        # news_summary_prompt = '请用中文简短概括这篇文章的内容。'
        # str_list.append(news_summary_prompt)
        # answer = get_answer_from_chatGPT(str_list)
        # return answer
    except Exception as e:
        error = f"refine_image error -> {e}"
        logger.error(error)
        return error


def meme_image(buffer):
    try:
        print(f"meme_image")
        # answer = image_meme(buffer)
        # # 把文字转化为 midjourney prompt
        # return answer
    except Exception as e:
        error = f"refine_image error -> {e}"
        logger.error(error)
        return error
