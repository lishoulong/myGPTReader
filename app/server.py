#!/usr/bin/env python3.8
import requests
import json
from event import EventManager
from flask import Flask, jsonify, request
from flask_apscheduler import APScheduler
from utils.thread import setup_logger
from pytz import utc
import traceback
from config import VERIFICATION_TOKEN, ENCRYPT_KEY
from handlers import request_url_verify_handler, message_receive_event_handler, schedule_news, refine_image, meme_image
from gpt import get_answer_from_web_embedding

logger = setup_logger('my_gpt_reader_server')

app = Flask(__name__)
app.config['SCHEDULER_TIMEZONE'] = utc
scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)

# 获取当前时间
# now = datetime.datetime.now()

# 任务1：5天后执行
# run_date_task1 = now + datetime.timedelta(seconds=5)

# @scheduler.task('date', id='date_task1', run_date=run_date_task1)
# def date_task1():
#     schedule_news()
# 用于注册任务的函数


def register_task(scheduler, task_id, trigger_type, func, **trigger_args):
    scheduler.add_job(id=task_id, func=func,
                      trigger=trigger_type, **trigger_args)


# 注册 schedule_news 任务
register_task(scheduler, 'daily_news_task', 'cron',
              schedule_news, hour=1, minute=30)

event_manager = EventManager()
event_manager.register("url_verification")(request_url_verify_handler)
event_manager.register("im.message.receive_v1")(message_receive_event_handler)


@app.errorhandler
def msg_error_handler(ex):
    logger.error(ex)
    response = jsonify(message=str(ex))
    response.status_code = (
        ex.response.status_code if isinstance(ex, requests.HTTPError) else 500
    )
    return response


@app.route("/api-endpoint", methods=["POST"])
def callback_event_handler():
    # init callback instance and handle
    dict_data = json.loads(request.data)
    # logger.info(f"api-endpoint dict_data->{dict_data}")
    logger.info('=====> api-endpoint !')
    event_handler, event = event_manager.get_handler_with_event(
        VERIFICATION_TOKEN, ENCRYPT_KEY)
    if event_handler is None:
        return jsonify()
    return event_handler(event)


@app.route("/api-summarize", methods=["POST"])
def summarize_handler():
    try:
        # init callback instance and handle
        dict_data = json.loads(request.data)
        # logger.info(f"api-endpoint dict_data->{dict_data}")
        urls = dict_data.get("urls")
        question = dict_data.get("question", [])
        content = dict_data.get("content", "")

        logger.info(f"format_dialog_messages -> {question}")
        if_first_question = True
        if len(question) > 0:
            if_first_question = False
        gpt_response = get_answer_from_web_embedding(
            question, urls, if_first_question, content)
        response = jsonify({'result': gpt_response})
        response.status_code = 200
        return response
    except Exception as e:
        logger.info(f'api-summarize error : {e}')
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route("/api-image-meme", methods=["POST"])
def image_meme_handler():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    buffer = file.read()
    logger.info(f'=====> apiapiapi')

    try:
        answer = meme_image(buffer)
        return jsonify({'result': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api-image-ocr", methods=["POST"])
def image_ocr_handler():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    buffer = file.read()
    logger.info(f'=====> apiapiapi')

    try:
        answer = refine_image(buffer)
        return jsonify({'result': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    # init()
    scheduler.start()
    app.run(host="0.0.0.0", port=80)
