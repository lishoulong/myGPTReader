#! /usr/bin/env python3.8
import logging
import requests
import json
from urllib.parse import urlencode
from requests_toolbelt import MultipartEncoder

# const
TENANT_ACCESS_TOKEN_URI = "/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URI = "/open-apis/im/v1/messages"
FILE_URI = "/open-apis/im/v1/files"


class CozeAPIClient:
    def __init__(self, personal_access_token):
        self.base_url = "https://api.coze.cn/open_api/v2/chat"
        self.headers = {
            'Authorization': f'Bearer {personal_access_token}',
            'Content-Type': 'application/json',
            'Accept': '*/*'
        }

    def send_message(self, conversation_id, bot_id, user_id, query, stream=False):
        data = {
            "conversation_id": conversation_id,
            "bot_id": bot_id,
            "user": user_id,
            "query": query,
            "stream": stream
        }
        response = requests.post(
            self.base_url, headers=self.headers, data=json.dumps(data))
        return response


class MessageApiClient(object):
    def __init__(self, app_id, app_secret, lark_host):
        self._app_id = app_id
        self._app_secret = app_secret
        self._lark_host = lark_host
        self._tenant_access_token = ""

    @property
    def tenant_access_token(self):
        return self._tenant_access_token

    def downLoadFile(self, message_id, file_key, type):
        self._authorize_tenant_access_token()
        url = "{}{}/{}/resources/{}?type={}".format(
            self._lark_host, MESSAGE_URI, message_id, file_key, type
        )
        headers = {
            "Authorization": "Bearer " + self.tenant_access_token,
        }
        resp = requests.get(url=url, headers=headers)
        if resp.status_code != 200:
            resp.raise_for_status()
        return resp

    def webhookRequest(self, content):
        # 正式 url
        url = "https://open.feishu.cn/open-apis/bot/v2/hook/35581f8a-d488-47c8-b160-d484970e2ccf"
        # 测试 url
        # url = "https://open.feishu.cn/open-apis/bot/v2/hook/e6be6eb8-6676-4473-a1dc-e23a83963ae7"
        req_body = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": content
                }
            }
        }
        resp = requests.post(url=url, json=req_body)
        print(f'self.reply_message-- {resp}')
        MessageApiClient._check_error_response(resp)
        return resp

    def upload_file(self, files, file_name):
        self._authorize_tenant_access_token()
        url = "{}{}".format(
            self._lark_host, FILE_URI
        )
        headers = {
            "Authorization": "Bearer " + self.tenant_access_token,
        }

        form = {
            "file_type": "opus",
            "file_name": file_name,
            "file": (file_name, files, 'audio/opus')
        }

        multi_form = MultipartEncoder(form)
        headers['Content-Type'] = multi_form.content_type

        resp = requests.post(url=url, headers=headers, data=multi_form)
        MessageApiClient._check_error_response(resp)
        return resp

    def send_text_with_open_id(self, open_id, content, uuid):
        self.send("open_id", open_id, "text", content, uuid)

    def reply_text_with_message_id(self, message_id, content, uuid, message_type="text"):
        self.reply_message(message_id, message_type, content, uuid)

    def reply_message(self, message_id, msg_type, content, uuid):
        # send message to user, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
        self._authorize_tenant_access_token()
        url = "{}{}/{}/reply".format(
            self._lark_host, MESSAGE_URI, message_id
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.tenant_access_token,
        }

        req_body = {
            "content": content,
            "msg_type": msg_type,
            "uuid": uuid
        }
        resp = requests.post(url=url, headers=headers, json=req_body)
        MessageApiClient._check_error_response(resp)

    def send(self, receive_id_type, receive_id, msg_type, content, uuid):
        # send message to user, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
        self._authorize_tenant_access_token()
        url = "{}{}?receive_id_type={}".format(
            self._lark_host, MESSAGE_URI, receive_id_type
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.tenant_access_token,
        }

        req_body = {
            "receive_id": receive_id,
            "content": content,
            "msg_type": msg_type,
            "uuid": uuid
        }
        resp = requests.post(url=url, headers=headers, json=req_body)
        MessageApiClient._check_error_response(resp)

    def _authorize_tenant_access_token(self):
        # get tenant_access_token and set, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/ukTMukTMukTM/ukDNz4SO0MjL5QzM/auth-v3/auth/tenant_access_token_internal
        url = "{}{}".format(self._lark_host, TENANT_ACCESS_TOKEN_URI)
        req_body = {"app_id": self._app_id, "app_secret": self._app_secret}
        response = requests.post(url, req_body)
        MessageApiClient._check_error_response(response)
        self._tenant_access_token = response.json().get("tenant_access_token")

    def maiHire():
        url = "https://api.taou.com/sdk/publish?feed_content_tags=%255B%257B%2522id%2522%253A59709%252C%2522name%2522%253A%2522%25E6%259C%2580%25E9%259A%25BE%25E5%25BF%2598%25E7%259A%2584%25E4%25B8%2580%25E6%25AC%25A1%25E5%258D%2587%25E8%2581%258C%2522%252C%2522text%2522%253A%2522%25E6%259C%2580%25E9%259A%25BE%25E5%25BF%2598%25E7%259A%2584%25E4%25B8%2580%25E6%25AC%25A1%25E5%258D%2587%25E8%2581%258C%2522%257D%255D&fr=friend_feed_guide_normal_v2&container_id=-2001&target=publish_friend_feed&appid=4&access_token=1.10740d756d606d439d8638bcd9f1db85&vc=16.6&version=6.3.6&webviewUserAgent=Mozilla%2F5.0%20%28iPhone%3B%20CPU%20iPhone%20OS%2016_6%20like%20Mac%20OS%20X%29%20AppleWebKit%2F605.1.15%20%28KHTML%2C%20like%20Gecko%29%20Mobile%2F15E148&channel=AppStore&rn_version=0.69.0&sm_did=D2eUVb%2FHEUei69Pl3mYNLY%2F8Mx2GXXw9a3DeeETUoYK3wXf7&net=wifi&session_uuid=899a803d8781438ba421f099609ec51d&push_permit=1&screen_height=2556&launch_uuid=44267ecc9eb6405caaba9b70d5aa3101&density=3&u=225671345&device=iPhone15%2C2&screen_width=1179&udid=f47a1094bf8f4850aa335a48103a4fc6"

        headers = {
            "Cookie": "session=eyJ1IjoiMjI1NjcxMzQ1Iiwic2VjcmV0IjoiWlFUUzRpcmhORDNJRXdHdU56WWNTc2s3IiwiX2V4cGlyZSI6MTY5MTkwMDIyNDExNywiX21heEFnZSI6ODY0MDAwMDB9&session.sig=uZt8N0Z4DmWA70-BMbK6iwc6OkU",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "aigc_rewrite": "0",
            "annoy_type": "0",
            "at_users": "",
            "container_id": "-2001",
            "content": "字节跳动抖音开放平台诚招高级前端和前端专家，工作内容为抖音小程序框架建设和小程序入口及私能力建设，职级2.1~2.2，可base杭州、深圳，有兴趣的小伙伴，抓紧联系起来。",
            "data_id": "",
            "data_str": "",
            "extra_infomation": "{\"feed_content_tags\":\"[]\"}",
            "hash": "28aa0b06d9784440a7567793b3e63aed",
            "imgs": "[]",
            "is_normal_feed": "1",
            "is_original": "0",
            "job_card_data_id": "",
            "job_card_data_str": "",
            "tag_type": "0",
            "target": "publish_friend_feed",
            "template_data": ""
        }

        try:
            response = requests.post(
                url, headers=headers, data=urlencode(data))
            response.raise_for_status()  # Raise an exception for HTTP errors
            logging.info("POST maiHire request successful")
        except requests.exceptions.RequestException as e:
            logging.error(f"POST request error -> {e}")

    @staticmethod
    def _check_error_response(resp):
        # check if the response contains error information
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response content: {resp.content}")
            raise

        response_dict = resp.json()
        code = response_dict.get("code", -1)
        if code != 0:
            logging.error(response_dict)
            raise LarkException(code=code, msg=response_dict.get("msg"))


class LarkException(Exception):
    def __init__(self, code=0, msg=None):
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return "{}:{}".format(self.code, self.msg)

    __repr__ = __str__
