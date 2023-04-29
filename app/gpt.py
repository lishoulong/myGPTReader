
import os
import hashlib
import json
import openai
import revChatGPT
from pathlib import Path
from local_llama_index import GPTSimpleVectorIndex, LLMPredictor, SimpleDirectoryReader, ServiceContext, PromptHelper
from local_llama_index.prompts.prompts import QuestionAnswerPrompt
from local_llama_index.readers.schema.base import Document
from embedding import file2embedding, ask
from langchain.chat_models import ChatOpenAI
from revChatGPT.V1 import Chatbot
from utils import setup_logger
from config import OPENAI_API_KEY_SECOND, ACCESS_TOKEN
from fetch_web_post import get_urls, get_youtube_transcript, scrape_website
from utils import get_youtube_video_id
# , base_url="https://openabc.online/backend-api/"
logging = setup_logger('my_gpt_reader_gpt')
chatbot = Chatbot(config={
  "access_token": ACCESS_TOKEN,
  "paid": True,
}, conversation_id=None, parent_id=None, session_client=None, lazy_loading=False)
# SPEECH_KEY = os.environ.get('SPEECH_KEY')
# SPEECH_REGION = os.environ.get('SPEECH_REGION')
# 将 API 密钥放入列表中
# api_keys = [OPENAI_API_KEY, OPENAI_API_KEY_SECOND, OPENAI_API_KEY_THIRD]
# # 随机选择一个 API 密钥
# chosen_api_key = random.choice(api_keys)
# 将选定的 API 密钥分配给 openai.api_key
openai.api_key = OPENAI_API_KEY_SECOND
print(f'OPENAI_API_KEY_SECOND =>> {OPENAI_API_KEY_SECOND}')

llm_predictor = LLMPredictor(llm=ChatOpenAI(
    temperature=0.2, model_name="gpt-3.5-turbo"))
# define prompt helper
# set maximum input size
max_input_size = 4096
# set number of output tokens
num_output = 1600
# set maximum chunk overlap
max_chunk_overlap = 50
prompt_helper = PromptHelper(max_input_size, num_output, max_chunk_overlap)
# the "mock" llm predictor is our token counter
# mock_llm_predictor = MockLLMPredictor(max_tokens=256)÷=
service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor, prompt_helper=prompt_helper)

index_cache_web_dir = Path('/tmp/myGPTReader/cache_web/')
home_dir = os.path.expanduser("~")
index_cache_file_dir = Path(home_dir, "myGPTReader", "file")

if not index_cache_web_dir.is_dir():
    index_cache_web_dir.mkdir(parents=True, exist_ok=True)

if not index_cache_file_dir.is_dir():
    index_cache_file_dir.mkdir(parents=True, exist_ok=True)
PARENT_ID_MAPPING_FILE = index_cache_file_dir / "parent_id_mapping.json"
PARENT_CHILD_MAPPING_FILE = index_cache_file_dir / "parent_child_mapping.json"

def get_unique_md5(urls):
    urls_str = ''.join(sorted(urls))
    hashed_str = hashlib.md5(urls_str.encode('utf-8')).hexdigest()
    return hashed_str

def format_dialog_messages(messages, prompt="请使用中文回复"):
    messages.insert(0, prompt)
    return f"{prompt}\n" + "\n".join(messages[1:])

def get_document_from_youtube_id(video_id):
    if video_id is None:
        return None
    transcript = get_youtube_transcript(video_id)
    if transcript is None:
        return None
    return Document(transcript)
def get_text_from_youtube_id(video_id):
    if video_id is None:
        return None
    transcript = get_youtube_transcript(video_id)
    if transcript is None:
        return None
    return transcript

def get_parent_id(parent_thread_id):
    if not os.path.exists(PARENT_ID_MAPPING_FILE):
        return None

    with open(PARENT_ID_MAPPING_FILE, 'r') as f:
        parent_id_mapping = json.load(f)

    return parent_id_mapping.get(str(parent_thread_id))

def write_parent_id(parent_thread_id, parent_id):
    parent_id_mapping = {}

    if os.path.exists(PARENT_ID_MAPPING_FILE):
        with open(PARENT_ID_MAPPING_FILE, 'r') as f:
            parent_id_mapping = json.load(f)

    parent_id_mapping[str(parent_thread_id)] = parent_id

    with open(PARENT_ID_MAPPING_FILE, 'w') as f:
        json.dump(parent_id_mapping, f)

def find_key_by_value(value: str, input_dict: dict) -> str:
    for key, val in input_dict.items():
        if val == value:
            return key
    return None

def write_parent_child_id(conversation_mapping):
    with open(PARENT_CHILD_MAPPING_FILE, 'w') as f:
        json.dump(conversation_mapping, f)

def get_info_from_file():
    with open(PARENT_CHILD_MAPPING_FILE, 'r') as f:
        return json.load(f)

def update_parent_child_id(conversation_id, parent_id):
    conversation_mapping = {}
    if os.path.exists(PARENT_CHILD_MAPPING_FILE):
        conversation_mapping = get_info_from_file()
    conversation_mapping[conversation_id] = parent_id
    write_parent_child_id(conversation_mapping)
    
def get_answer_from_web(dialog_messages, parent_thread_id, thread_id):
    logging.info(f'=====> Use chatGPT WEB to answer! conversation_id={thread_id}, parent_id={parent_thread_id}, if equal = {thread_id == parent_thread_id}')
    parent_id = None
    # thread_id == parent_thread_id 表示飞书新启动一个消息，那么这时候需要把 chatgpt 的 parent_id 清空或者重新获取历史的对应关系
    if chatbot.parent_id is None or thread_id == parent_thread_id:
        logging.info(
        f'=====> chatbot.parent_id is None or thread_id == parent_thread_id '
        f'parent_id={parent_thread_id}, if equal = {thread_id == parent_thread_id}'
    )
        parent_id = get_parent_id(parent_thread_id)
    response = ""
    logging.info(f"conversation_mapping-{chatbot.conversation_mapping}, conversation_id - {chatbot.conversation_id}, parent_id - {parent_id}")
    if chatbot.conversation_id is None and parent_id is not None:
        # 如果 PARENT_CHILD_MAPPING_FILE 不存在就走创建写入逻辑
        if not os.path.exists(PARENT_CHILD_MAPPING_FILE):
            chatbot._Chatbot__map_conversations()
            # 把对话信息写入文件系统
            write_parent_child_id(chatbot.conversation_mapping)
        else:
            # 提取文件内容
            chatbot.conversation_mapping = get_info_from_file()
        logging.info(f"conversation_mapping1111- conversation_mapping {chatbot.conversation_mapping }")
        chatbot.conversation_id = find_key_by_value(parent_id, chatbot.conversation_mapping)
        logging.info(f"conversation_mapping222- conversation_id {chatbot.conversation_id }")
    # 如果出现 gpt4 限流的问题，需要降级到 gpt-3.5-turbo
    model = ""
    try:
        model = "gpt-4"
        for data in chatbot.ask(
            prompt=dialog_messages,
            conversation_id=chatbot.conversation_id,
            parent_id=parent_id,
            model=model
        ):
            response = data["message"]
        print(f"get_answer_from_chatGPT => {response}")
    except revChatGPT.typings.Error as e:
        # 429错误处理
        if "model_cap_exceeded" in str(e):
            # 降级到较低版本的API
            model = "gpt-3.5-turbo"
            for data in chatbot.ask(
                prompt=dialog_messages,
                conversation_id=chatbot.conversation_id,
                parent_id=chatbot.parent_id,
                model=model
            ):
                response = data["message"]
            print(f"get_answer_from_chatGPT (fallback to gpt-3.5-turbo) => {response}")
        else:
            raise e
    # 把 parent_thread_id 和 chatbot.parent_id 对应关系写入文件系统中，下次进来直接从文件系统根据 parent_thread_id 读取这个 parent_id
    write_parent_id(parent_thread_id, chatbot.parent_id)
    update_parent_child_id(chatbot.conversation_id, chatbot.parent_id)
    return f"({model}) {response}"

def get_answer_from_openapi(dialog_messages):
    logging.info('=====> Use chatGPT OPENAPI to answer!')
    logging.info(dialog_messages)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": dialog_messages}]
    )
    return completion.choices[0].message.content

def get_answer_from_chatGPT(messages, parent_thread_id, thread_id, is_use_web_gpt):
    dialog_messages = format_dialog_messages(messages)
    result = ""
    if is_use_web_gpt:
        result = get_answer_from_web(dialog_messages, parent_thread_id, thread_id)
    else:
        result = get_answer_from_openapi(dialog_messages, parent_thread_id, thread_id)
    return result


QUESTION_ANSWER_PROMPT_TMPL = (
    "Context information is below. \n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "{query_str}\n"
)
QUESTION_ANSWER_PROMPT = QuestionAnswerPrompt(QUESTION_ANSWER_PROMPT_TMPL)


def get_index_from_web_cache(name):
    web_cache_file = index_cache_web_dir / name
    if not web_cache_file.is_file():
        return None
    # index = GPTSimpleVectorIndex.load_from_disk(web_cache_file, service_context=service_context)
    logging.info(
        f"=====> Get index from web cache: {web_cache_file}")
    return web_cache_file


def get_index_from_file_cache(name):
    file_cache_file = index_cache_file_dir / name
    if not file_cache_file.is_file():
        return None
    index = GPTSimpleVectorIndex.load_from_disk(file_cache_file, service_context=service_context)
    logging.info(
        f"=====> Get index from file cache: {file_cache_file}")
    return index

# def get_documents_from_urls(urls):
#     documents = []
#     for url in urls['page_urls']:
#         document = Document(scrape_website(url))
#         documents.append(document)
#     if len(urls['youtube_urls']) > 0:
#         for url in urls['youtube_urls']:
#             video_id = get_youtube_video_id(url)
#             document = get_document_from_youtube_id(video_id)
#             if (document is not None):
#                 documents.append(document)
#             else:
#                 documents.append(Document(f"Can't get transcript from youtube video: {url}"))
#     return documents

def get_text_from_urls(urls):
    documents = []
    for url in urls['page_urls']:
        document = scrape_website(url)
        documents.append(document)
    if len(urls['youtube_urls']) > 0:
        for url in urls['youtube_urls']:
            video_id = get_youtube_video_id(url)
            document = get_text_from_youtube_id(video_id)
            if (document is not None):
                documents.append(document)
            else:
                documents.append(Document(f"Can't get transcript from youtube video: {url}"))
    return documents

def get_answer_from_llama_web(messages, urls):
    dialog_messages = format_dialog_messages(messages, "请用中文详细总结这篇文章的内容")
    logging.info('=====> Use llama web with chatGPT to answer!')
    # logging.info(dialog_messages)
    combained_urls = get_urls(urls)
    logging.info(combained_urls)
    index_file_name = get_unique_md5(urls)
    index = get_index_from_web_cache(index_file_name)
    documents = get_text_from_urls(urls)
    abc = file2embedding(index, documents)
    answer = ask(dialog_messages, abc.embeddings)
    # if index is None:
    #     logging.info(f"=====> Build index from web!")
    #     documents = get_documents_from_urls(combained_urls)
    #     index = GPTSimpleVectorIndex.from_documents(documents, service_context=service_context)
    #     logging.info(
    #         f"=====> Save index to disk path: {index_cache_web_dir / index_file_name}")
        
    #     index.save_to_disk(index_cache_web_dir / index_file_name)
    # answer = index.query(dialog_messages, text_qa_template=QUESTION_ANSWER_PROMPT)
    # logging.info(
    #         f"=====> get_answer_from_llama_web GPTSimpleVectorIndex query tokens: {llm_predictor.last_token_usage}")
    return answer
def get_index_name_from_file(file: str):
    file_md5_with_extension = str(Path(file).relative_to(index_cache_file_dir).name)
    file_md5 = file_md5_with_extension.split('.')[0]
    return file_md5 + '.json'

def get_answer_from_llama_file(messages, file):
    dialog_messages = format_dialog_messages(messages)
    logging.info(f'=====> Use llama file with chatGPT to answer! => {dialog_messages == ""}')
    # logging.info(dialog_messages)
    index_name = get_index_name_from_file(file)
    index = get_index_from_file_cache(index_name)
    if index is None:
        logging.info(f"=====> Build index from file!")
        documents = SimpleDirectoryReader(input_files=[file]).load_data()
        index = GPTSimpleVectorIndex.from_documents(documents, service_context=service_context)
        logging.info(
            f"=====> Save index to disk path: {index_cache_file_dir / index_name}, get_answer_from_llama_file documents last_token_usage is {llm_predictor.last_token_usage}")
        index.save_to_disk(index_cache_file_dir / index_name)
    if dialog_messages == '':
        logging.info(f"=====> dialog_messages is empty, just build file index!")
        return "没有输入内容，已经根据文件建立索引，请在此消息后回复对于文件的问题"
    answer = index.query(dialog_messages, text_qa_template=QUESTION_ANSWER_PROMPT)
    return answer

def get_text_from_whisper(voice_file_path):
    with open(voice_file_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript.text

def remove_prompt_from_text(text):
    return text.replace('AI:', '').strip()
