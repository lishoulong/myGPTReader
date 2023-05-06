import unittest
from app.handlers import message_receive_event_handler
import sys
import os

# 将以下路径替换为实际的 "app" 目录路径
path_to_your_app_directory = '/Users/lishoulong/Documents/toutiao/lib/openai/second/myGPTReader/app'
sys.path.insert(0, os.path.abspath(path_to_your_app_directory))

class TestHandlers(unittest.TestCase):
    def test_message_receive_event_handler(self):
        # create a mock event object
        event = {
            'event': {
                'sender': {'sender_id': {'open_id': 'test_user'}},
                'message': {'message_id': 'test_message_id', 'message_type': 'text'},
                'header': {'create_time': 'test_create_time'}
            }
        }
        req_data = {'event': event}

        # call the function and check the output
        result = message_receive_event_handler(req_data)
        self.assertEqual(result.status_code, 200)

if __name__ == '__main__':
    unittest.main()