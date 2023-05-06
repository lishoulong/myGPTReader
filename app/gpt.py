
import os
import json
import openai
import PyPDF2
import time
import traceback
import revChatGPT
from embedding import file2embedding, ask
from revChatGPT.V1 import Chatbot
from utils.thread import setup_logger, format_dialog_messages
from utils.filesystem import get_json_path
from utils.chat_parent_id import write_parent_id, find_key_by_value, get_info_from_file, write_parent_child_id, PARENT_CHILD_MAPPING_FILE, get_parent_id, update_parent_child_id
from utils.fetch_web import get_urls, get_text_from_urls
from config import OPENAI_API_KEY, ACCESS_TOKEN

logging = setup_logger('my_gpt_reader_gpt')
openai.api_key = OPENAI_API_KEY
logging.info(f'OPENAI_API_KEY =>> {OPENAI_API_KEY}')
# use chatgpt web to answer
chatbot = {}
obj = {}


def get_answer_from_web(dialog_messages, parent_thread_id, thread_id):
    try:
        logging.info(
            f'=====> Use chatGPT WEB to answer! conversation_id={thread_id}, parent_id={parent_thread_id}, if equal = {thread_id == parent_thread_id}')
        chatbot = get_chatbot(parent_thread_id, thread_id)
        # thread_id == parent_thread_id 表示飞书新启动一个消息，那么这时候需要把 chatgpt 的 parent_id 清空或者重新获取历史的对应关系
        parent_id = get_parent_id(
            parent_thread_id) if chatbot.parent_id is None or thread_id == parent_thread_id else None
        response = ""
        logging.info(
            f"conversation_mapping-{chatbot.conversation_mapping}, conversation_id - {chatbot.conversation_id}, parent_id - {parent_id}")
        # 适用于重启了程序，在之前的历史记录上重新回复消息，根据飞书的 parent_thread_id 获取到了 chatgpt 的 parent_id
        update_chatbot_conversation_mapping(chatbot, parent_id)
        logging.info("after update_chatbot_conversation_mapping ->>>")
        # 如果出现 gpt4 限流的问题，需要降级到 gpt-3.5-turbo
        # model = ""
        start = time.time()
        # model = "gpt-3.5-turbo"
        # response = ask_chatbot(chatbot, dialog_messages, model, parent_id)
        try:
            model = "gpt-4"
            response = ask_chatbot(chatbot, dialog_messages, model, parent_id)
            end = time.time()
            logging.info(
                f"end get_answer_from_chatGPT(gpt-4) => {response} -> time interval: {end-start}")
        except revChatGPT.typings.Error as e:
            # 429错误处理
            if "model_cap_exceeded" in str(e):
                # 降级到较低版本的API
                model = "gpt-3.5-turbo"
                response = ask_chatbot(
                    chatbot, dialog_messages, model, parent_id)
                logging.info(
                    f"get_answer_from_chatGPT (fallback to gpt-3.5-turbo) => {response} -> time interval: {end-start}")
            else:
                raise e
        # 把 parent_thread_id 和 chatbot.parent_id 对应关系写入文件系统中，下次进来直接从文件系统根据 parent_thread_id 读取这个 parent_id
        write_parent_id(parent_thread_id, chatbot.parent_id)
        update_parent_child_id(chatbot.conversation_id, chatbot.parent_id)
        return f"({model}) {response}"
    except Exception as e:
        logging.error(f"get_answer_from_web error -> {e}")
        traceback.print_exc()
        return str(e)


def get_answer_from_openapi(dialog_messages):
    logging.info(f"start Use chatGPT OPENAPI to answer!->{dialog_messages}")
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": dialog_messages}]
    )
    logging.info(f"end Use chatGPT OPENAPI to answer!->{dialog_messages}")
    return completion.choices[0].message.content


def get_answer_from_chatGPT(messages, parent_thread_id, thread_id, is_use_web_gpt):
    dialog_messages = format_dialog_messages(messages)
    result = ""
    if is_use_web_gpt:
        result = get_answer_from_web(
            dialog_messages, parent_thread_id, thread_id)
    else:
        result = get_answer_from_openapi(dialog_messages)
    return result


def get_answer_from_embedding(messages, file_dict, is_first_message=False):
    dialog_messages = format_dialog_messages(messages)
    print(f'get_answer_from_embedding dialog_messages -> {dialog_messages}')
    answer = "已经建立索引，请继续提问"
    if dialog_messages.strip():
        print(f'dialog_messages 为空-> {dialog_messages.strip()}')
        answer = ask(dialog_messages,
                     file_dict['embeddings'], file_dict['sources'])
    summarizes = file_dict['summarizes']
    formatted_answer = answer
    if is_first_message and summarizes:
        formatted_answer = f"{answer}\n\n文章内容总结如下:\n{summarizes}"
    return formatted_answer


def get_answer_from_file_embedding(messages, file, is_first_message=False):
    logging.info(f'=====> Use llama file with chatGPT to answer!')
    json_path = get_json_path(str(file))
    file_dict = {}
    if not (json_path).exists():
        documents = get_text_from_path(file)
        file_dict = file2embedding(json_path, documents)
    else:
        with open(json_path, 'r', encoding='utf-8') as f:
            file_dict = json.load(f)
    return get_answer_from_embedding(messages, file_dict, is_first_message)


def get_answer_from_web_embedding(messages, urls, is_first_message=False):
    logging.info('=====> Use llama web with chatGPT to answer!')
    combained_urls = get_urls(urls)
    logging.info(combained_urls)
    json_path = get_json_path(''.join(sorted(urls)))

    file_dict = {}
    if not (json_path).exists():
        documents = get_text_from_urls(combained_urls)
        file_dict = file2embedding(json_path, documents)
    else:
        with open(json_path, 'r', encoding='utf-8') as f:
            file_dict = json.load(f)
    return get_answer_from_embedding(messages, file_dict, is_first_message)


def get_text_from_whisper(voice_file_path):
    with open(voice_file_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript.text


def get_text_from_path(path: str) -> str:
    documents = []
    with open(path, "rb") as f:
        pdf_reader = PyPDF2.PdfReader(f)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        documents.append(text)
    return documents


def get_chatbot(parent_thread_id, thread_id):
    # 飞书重新启动一个消息，就需要相应的重新初始化 chatbot，需要维护 parent_thread_id 和 chatbot 的对应关系
    if thread_id == parent_thread_id:
        chatbot = Chatbot(config={
            "access_token": ACCESS_TOKEN,
            "paid": True,
        }, conversation_id=None, parent_id=None, session_client=None, lazy_loading=False)
        obj[parent_thread_id] = chatbot
    else:
        # 如果重新启动服务，这是内存中也没有 obj 了
        try:
            chatbot = obj[parent_thread_id]
        except KeyError as e:
            logging.info('=====> get_chatbot error {e}, initialize chatbot')
            chatbot = Chatbot(config={
                "access_token": ACCESS_TOKEN,
                "paid": True,
            }, conversation_id=None, parent_id=None, session_client=None, lazy_loading=False)
            obj[parent_thread_id] = chatbot
    return chatbot


def update_chatbot_conversation_mapping(chatbot, parent_id):
    if chatbot.conversation_id is None and parent_id is not None:
        # 如果 PARENT_CHILD_MAPPING_FILE 不存在就走创建写入逻辑
        if not os.path.exists(PARENT_CHILD_MAPPING_FILE):
            chatbot._Chatbot__map_conversations()
            # 把对话信息写入文件系统
            write_parent_child_id(chatbot.conversation_mapping)
        else:
            # 提取文件内容
            chatbot.conversation_mapping = get_info_from_file()
        # logging.info(
        #     f"conversation_mapping1111- conversation_mapping {chatbot.conversation_mapping }")
        chatbot.conversation_id = find_key_by_value(
            parent_id, chatbot.conversation_mapping)
        # logging.info(
        #     f"conversation_mapping222- conversation_id {chatbot.conversation_id }")


def ask_chatbot(chatbot, dialog_messages, model, parent_id):
    response = ""
    for data in chatbot.ask(
        prompt=dialog_messages,
        conversation_id=chatbot.conversation_id,
        parent_id=parent_id,
        model=model
    ):
        response = data["message"]
    return response
