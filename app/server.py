#!/usr/bin/env python3.8
import requests
from event import EventManager
from flask import Flask, jsonify
from flask_apscheduler import APScheduler
from utils import setup_logger
from config import VERIFICATION_TOKEN, ENCRYPT_KEY
from handlers import request_url_verify_handler, message_receive_event_handler, schedule_news

logger = setup_logger('my_gpt_reader_server')

app = Flask(__name__)

scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)

# # 获取当前时间
# now = datetime.datetime.now()

# # 任务1：5天后执行
# run_date_task1 = now + datetime.timedelta(seconds=5)

# @scheduler.task('date', id='date_task1', run_date=run_date_task1)
# def date_task1():
#     schedule_news()
# 用于注册任务的函数
def register_task(scheduler, task_id, trigger_type, func, **trigger_args):
    scheduler.add_job(id=task_id, func=func, trigger=trigger_type, **trigger_args)

# 注册 schedule_news 任务
register_task(scheduler, 'daily_news_task', 'cron', schedule_news, hour=1, minute=30)

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
    logger.info('=====> api-endpoint !')
    event_handler, event = event_manager.get_handler_with_event(VERIFICATION_TOKEN, ENCRYPT_KEY)
    if event_handler is None:
        return jsonify()
    return event_handler(event)


if __name__ == "__main__":
    # init()
    scheduler.start()
    app.run(host="0.0.0.0", port=5000)
