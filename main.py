import numpy as np
from PIL import Image, ImageOps
from flask import Flask, request, abort
from flask_ngrok import run_with_ngrok


from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage, PostbackEvent
)
import requests
from linebot.models import (
    ImagemapSendMessage, TextSendMessage, ImageSendMessage, LocationSendMessage, 
    FlexSendMessage, VideoSendMessage, StickerSendMessage, AudioSendMessage
)
from linebot.models.template import (
    ButtonsTemplate, CarouselTemplate, ConfirmTemplate, ImageCarouselTemplate    
)
from linebot.models.template import *

import json

# import CM_LineBot funtions
from utils.utils import yolov5


# load dialogue dict
file_jd = open('dialogue_dict.json', 'r', encoding='utf-8')
jd = json.load(file_jd)


# 設定server啟用細節 
app = Flask(__name__, static_url_path='/material', static_folder='/material')
run_with_ngrok(app)


# line api設定
line_bot_api = LineBotApi('Channel_Access_Token')
handler = WebhookHandler('Channel_Secret')



# Linebot 官方程序，驗證
@app.route('/callback', methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info('Request body: ' + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print('Invalid signature. Please check your channel access token/channel secret.')
        abort(400)

    return 'OK'


# ====== handle linebot events ======
# 
# 測試 linebot
# 當用戶收到文字消息的時候，回傳用戶講過的話
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 請line_bot_api回應，回應用戶講過的話
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))

        
# 監看Follow事件
from linebot.models.events import (
    FollowEvent
)

@handler.add(FollowEvent)
def reply_text_and_get_user_profile(event):
    
    line_bot_api.reply_message(event.reply_token, FlexSendMessage(
              alt_text='介紹',
              contents=jd['p1']
    ))









if __name__ == "__main__":
    app.run()

