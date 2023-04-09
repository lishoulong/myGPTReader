#! /usr/bin/env python3.8
import logging
import requests

# const
TENANT_ACCESS_TOKEN_URI = "/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URI = "/open-apis/im/v1/messages"
FILE_URI = "/open-apis/im/v1/files"


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
        url = "https://open.feishu.cn/open-apis/bot/v2/hook/35581f8a-d488-47c8-b160-d484970e2ccf"
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
    # def upload_file(self, file):
    #     self._authorize_tenant_access_token()
    #     url = "{}/{}".format(
    #         self._lark_host, FILE_URI
    #     )
    #     print(f'self.tenant_access_token--{self.tenant_access_token}')
    #     headers = {
    #         "Content-Type": "multipart/form-data; boundary=---7MA4YWxkTrZu0gW",
    #         "Authorization": "Bearer " + self.tenant_access_token,
    #     }
    #     req_body = {
    #         "file_type": content,
    #         "file_name": msg_type,
    #         "duration": uuid,
    #         "file": files
    #     }
    #     resp = requests.post(url=url, headers=headers, json=req_body)
    #     MessageApiClient._check_error_response(resp)

    def send_text_with_open_id(self, open_id, content, uuid):
        self.send("open_id", open_id, "text", content, uuid)

    def reply_text_with_message_id(self, message_id, content, uuid):
        self.reply_message(message_id, "text", content, uuid)

    def reply_message(self, message_id, msg_type, content, uuid):
        # send message to user, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
        self._authorize_tenant_access_token()
        url = "{}{}/{}/reply".format(
            self._lark_host, MESSAGE_URI, message_id
        )
        print(f'self.tenant_access_token--{self.tenant_access_token}')
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
        print(f'self.reply_message--')
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

    @staticmethod
    def _check_error_response(resp):
        # check if the response contains error information
        if resp.status_code != 200:
            resp.raise_for_status()
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
