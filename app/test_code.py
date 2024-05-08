import requests
import json
import base64
from utils.thread import setup_logger

logging = setup_logger('my_gpt_reader_gpt')


class DouyinQRCodeClient:
    def __init__(self):
        self.url = 'https://open.douyin.com/api/apps/v1/qrcode/create/'
        self.access_url = 'https://developer.toutiao.com/api/apps/v2/token'
        self.client_url = 'https://open.douyin.com/oauth/client_token/'
        self.appid = 'tt704606fbef7a40ee01'
        self.secret = '08210c202c01e47da5b825e361d4b99c37dc3be3'

    def create_qrcode(self, app_name, access_token, width, line_color, set_icon, is_circle_code):
        payload = {
            "app_name": app_name,
            "appid": self.appid,
            "width": width,
            "line_color": line_color,
            "set_icon": set_icon,
            "is_circle_code": is_circle_code
        }
        headers = {
            'Content-Type': 'application/json',
            'access-token': access_token
        }

        logging.info(f'payload =>> {payload}')
        response = requests.post(
            self.url, headers=headers, data=json.dumps(payload))
        return response

    def get_access_token(self):
        payload = {
            "appid": self.appid,
            "grant_type": 'client_credential',
            "secret": self.secret,
        }
        headers = {
            'Content-Type': 'application/json',
        }
        response = requests.post(
            self.access_url, headers=headers, data=json.dumps(payload))
        access_token = response.json().get('data').get('access_token')

        logging.info(f'access_token 111 =>> {access_token}')
        return access_token

    def get_client_token(self):
        payload = {
            "client_key": self.appid,
            "grant_type": 'client_credential',
            "client_secret": self.secret,
        }
        headers = {
            'Content-Type': 'application/json',
        }
        response = requests.post(
            self.client_url, headers=headers, data=json.dumps(payload))
        access_token = response.json().get('data').get('access_token')

        logging.info(f'access_token 111 =>> {access_token}')
        return access_token


class WeixinQRCodeClient:
    def __init__(self):
        self.url = 'https://api.weixin.qq.com/cgi-bin/wxaapp/createwxaqrcode'
        self.access_url = 'https://api.weixin.qq.com/cgi-bin/token'
        self.appid = 'wxf27c811b98b76735'
        self.secret = 'd26deeed26568ac7f3dd0db297c688be'

    def create_qrcode(self, access_token):
        payload = {
            "path": "pages/index/index?abcd=12345",
            "width": 280  # 修正键名
        }
        headers = {
            'Content-Type': 'application/json',
        }
        url = f'{self.url}?access_token={access_token}'  # 修正字符串插值
        response = requests.post(url, headers=headers,
                                 json=payload)  # 使用json参数直接传递字典
        return response

    def get_access_token(self):
        # f-string插值
        url = f'{self.access_url}?grant_type=client_credential&appid={self.appid}&secret={self.secret}'
        response = requests.get(url)
        if response.status_code == 200:
            access_token = response.json().get('access_token')
            logging.info(
                f'Access token retrieved from Weixin => {access_token}')
            return access_token
        else:
            # 应该处理错误的情况，可能抛出异常或返回错误信息
            logging.error('Failed to get access token')
            return None

    def get_base64_encoded_image(self, image_buffer):
        base64_encoded_result = base64.b64encode(image_buffer)  # 编码图片buffer
        base64_encoded_string = base64_encoded_result.decode(
            'utf-8')  # bytes to string
        # 根据图片数据类型增加相应的前缀，这里假设图片为PNG类型
        return f'data:image/png;base64,{base64_encoded_string}'


def write_image_to_html_file(base64_string, html_file_path):
    with open(html_file_path, 'w') as html_file:
        # 使用HTML5文档类型，确保兼容性
        html_file.write('<!DOCTYPE html>\n')
        html_file.write('<html lang="en">\n')
        html_file.write('<head>\n')
        html_file.write('<meta charset="UTF-8">\n')
        html_file.write(
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n')
        html_file.write('<title>QR Code Image</title>\n')
        html_file.write('</head>\n')
        html_file.write('<body>\n')
        # 添加图像
        html_file.write(f'<img src="{base64_string}" alt="QR Code Image">\n')
        html_file.write('</body>\n')
        html_file.write('</html>\n')


# 使用例子
if __name__ == "__main__":
    client = DouyinQRCodeClient()
    access_token = client.get_client_token()
    response = client.create_qrcode(
        app_name="douyin",
        access_token=access_token,
        width=500,
        line_color={"r": 0, "g": 0, "b": 0},
        set_icon=True,
        is_circle_code=True
    )
    # logging.info(f'base64_encoded_image =>> {response.content}')
    content = json.loads(response.content)
    img_data = content['data']['img']
    if response.status_code == 200:
        logging.info('QR code created successfully.')
        # 将二进制图像数据编码为base64字符串，并加上适当的前缀
        base64_encoded_image = 'data:image/png;base64,' + img_data
        # 决定HTML文件的保存位置
        html_file_path = 'qr_code.html'
        # 写入HTML文件
        write_image_to_html_file(base64_encoded_image, html_file_path)
        logging.info(f'QR code HTML page is written to {html_file_path}')
    else:
        logging.error(
            f'Failed to create QR code. Status Code: {response.status_code}')
    # 微信小程序二维码可用
    # client = WeixinQRCodeClient()
    # access_token = client.get_access_token()
    # response = client.create_qrcode(access_token)
    # logging.info(f'response =>> {response}')
    # base64_encoded_image = client.get_base64_encoded_image(
    #     image_buffer=response.content)
    # # return base64_encoded_image
    # logging.info(f'base64_encoded_image =>> {base64_encoded_image}')
