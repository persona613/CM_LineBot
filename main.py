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
from cm_utils.utils import yolov5, naming
from cm_utils.utils import get_ngrok_url


# load dialogue dict
file_jd = open('dialogue_dict.json', 'r', encoding='utf-8')
jd = json.load(file_jd)
file_jd.close()


# 設定server啟用細節 
app = Flask(__name__, static_url_path='/material', static_folder='./material')
# run_with_ngrok(app) # for colab test


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
# for testing linebot
# 當用戶收到文字消息的時候，回傳用戶講過的話
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 請line_bot_api回應，回應用戶講過的話
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))


# 監看Follow事件, reply service info
from linebot.models.events import (
    FollowEvent
)

@handler.add(FollowEvent)
def reply_text_and_get_user_profile(event):
    
    line_bot_api.reply_message(event.reply_token, FlexSendMessage(
              alt_text='介紹',
              contents=jd['p1']
    ))


# 接收圖像, 回傳預測結果字串及圖片
@handler.add(MessageEvent, message=ImageMessage)
def handle_message(event):

    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)

    path = './userimg/'+ event.message.id + '.png'
    with open(path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
    # 圖存於colab機器端

    # model
    model_output = yolov5(path)
    name_output = naming(model_output) # str
    # box_output = boxing(model_output, path) # url 

    # reply image url 
    # ngrok_url = "https://b5ed-35-204-95-221.ngrok.io"
    ngrok_url = get_ngrok_url()
    
    reply_img_url = ngrok_url + "/material/" + event.message.id + ".png"

    # reply box img and cm names of boxes
    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text='圖片辨識結果是...'),
         ImageSendMessage(
             original_content_url=reply_img_url,
             preview_image_url=reply_img_url # img url
             ),
        TextSendMessage(text=name_output)] # name str
    )



# 監看postback中的data
# 用於對話json內容中的按鈕action
@handler.add(PostbackEvent)
def handle_message(event):
    reply_token = event.reply_token
    message = event.postback.data


    if (message == '同意服務條款'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='服務條款', contents = jd['p2']),                        
        ])
    elif (message == '平和、陽虛、陰虛體質症狀'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='平和、陽虛、陰虛體質症狀', contents = jd['p3']),                        
        ])
    elif (message == '氣虛、痰濕、濕熱體質症狀'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='氣虛、痰濕、濕熱體質症狀', contents = jd['p4']),                        
        ])
    elif (message == '血瘀、氣鬱、特稟體質症狀'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='血瘀、氣鬱、特稟體質症狀', contents = jd['p5']),                        
        ])
    elif (message == '平和體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='平和體質建議', contents = jd['p6']),
                        
        ])
    elif (message == '陽虛體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='陽虛體質建議', contents = jd['p7']),
                        
        ])
    elif (message == '陰虛體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='陰虛體質建議', contents = jd['p8']),
                        
        ])
    elif (message == '氣虛體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='氣虛體質建議', contents = jd['p9']),
                        
        ])
    elif (message == '痰濕體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='痰濕體質建議', contents = jd['p10']),
                        
        ])  
    elif (message == '濕熱體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='濕熱體質建議', contents = jd['p11']),
                        
        ])  
    elif (message == '血瘀體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='血瘀體質建議', contents = jd['p12']),
                        
        ])
    elif (message == '氣鬱體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='氣鬱體質建議', contents = jd['p13']),
                        
        ])
    elif (message == '特稟體質建議'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='特稟體質建議', contents = jd['p14']),
                        
        ])


# 監看message event
# 部分選單功能與使用者輸入(關鍵字)
@handler.add(MessageEvent)
def handle_message(event):
    reply_token = event.reply_token
    message = event.message.text

    # 湯
    if ('補中益氣湯' in message):
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='補中益氣湯', contents = jd['補中益氣湯']),                        
        ])

    elif ('八珍湯' in message):         
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='八珍湯(丸)', contents = jd['s4']),                        
        ]) 

    elif ('六君子' in message):         
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='六君子湯(丸)', contents = jd['s2']),                        
        ])

     
    elif ('人參養榮湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='人參養榮湯', contents = jd['s3']),                        
        ])

    elif ('黃耆五物湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='黃耆五物湯', contents = jd['s5']),                        
        ])

    elif ('當歸四逆湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='當歸四逆湯', contents = jd['s6']),                        
        ])

    elif ('當歸六黃湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='當歸六黃湯', contents = jd['s7']),                        
        ])

    elif ('養心湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='養心湯', contents = jd['s8']),                        
        ])

    elif ('四君子湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='四君子湯', contents = jd['s9']),                        
        ])

    elif ('歸脾湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='歸脾湯', contents = jd['s10']),                        
        ])

    elif ('十全大補湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='十全大補湯', contents = jd['s11']),                        
        ])

    elif ('炙甘草湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='炙甘草湯', contents = jd['s12']),                        
        ])

    elif ('百合固金湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='百合固金湯', contents = jd['s13']),                        
        ])

    elif ('半夏天麻白朮湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='半夏天麻白朮湯', contents = jd['s15']),                        
        ])

    elif ('清肺湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='清肺湯', contents = jd['s14']),                        
        ])

    elif ('益氣聰明湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='益氣聰明湯', contents = jd['s16']),                        
        ])

    elif ('八味帶下方' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='八味帶下方', contents = jd['s17']),                        
        ])

    elif ('溫清飲' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='溫清飲', contents = jd['s18']),                        
        ])

    elif ('調經丸' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='調經丸', contents = jd['s19']),                        
        ])

    elif ('疏經活血湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='疏經活血湯', contents = jd['s20']),                        
        ])

    elif ('桃紅四物湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='桃紅四物湯', contents = jd['s21']),                        
        ])

    elif ('溫經湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='溫經湯', contents = jd['s22']),                        
        ])

    elif ('桂枝湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='桂枝湯', contents = jd['s23']),                        
        ])

    elif ('葛根湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='葛根湯', contents = jd['s24']),                        
        ])

    elif ('三痹湯' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='三痹湯', contents = jd['s25']),                        
        ])

    # 藥材
    elif ('沒藥' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='沒藥', contents = jd['m1']),                        
        ])
    elif ('紅耆' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='紅耆', contents = jd['m2']),                        
        ])
 
    elif ('黃耆' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='棉黃耆', contents = jd['m3']),
                        TextSendMessage(text='藥材也用於：補中益氣湯、人參養榮湯、黃耆五物湯、當歸六黃湯、歸脾湯、十全大補湯、半夏天麻白朮湯、益氣聰明湯，輸入湯藥名，可以知道更多...'),                      
        ])

    elif ('桂枝' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='桂枝', contents = jd['m4']),
                        TextSendMessage(text='藥材也用於：黃耆五物湯、當歸四逆湯、炙甘草湯、溫經湯、桂枝湯、葛根湯，輸入湯藥名，可以知道更多...'),
        ])
    elif ('川芎' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='川芎', contents = jd['m5']),
                        TextSendMessage(text='藥材也用於：八珍湯(丸)、養心湯、十全大補湯、百合固金湯、益氣聰明湯、溫清飲(解毒四物湯)、調經丸、疏經活血湯、桃紅四物湯、溫經湯、桂枝湯、葛根湯、三痹湯，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('白芍' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='白芍', contents = jd['m6']),
                        TextSendMessage(text='藥材也用於：人參養榮湯、八珍湯(丸)、黃耆五物湯、當歸四逆湯、十全大補湯、百合固金湯、益氣聰明湯、溫清飲、解毒四物湯)、調經丸、疏經活血湯、桃紅四物湯、溫經湯、桂枝湯、葛根湯、三痹湯，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('紅棗' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='紅棗', contents = jd['m7']),
                        TextSendMessage(text='藥材也用於：補中益氣湯、六君子湯(丸)、人參養榮湯、八珍湯(丸)、黃耆五物湯、當歸四逆湯、養心湯、四君子湯、歸脾湯、十全大補湯、炙甘草湯、清肺湯、桂枝湯、葛根湯、三痹湯，輸入湯藥名，可以知道更多...'),
        ])
    elif ('黑棗' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='黑棗', contents = jd['m8']),                        
        ])
    elif ('黨蔘' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='黨蔘', contents = jd['m9']),                        
        ])
    elif (message == '當歸'): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='當歸', contents = jd['m10']),
                        TextSendMessage(text='藥材也用於：補中益氣湯、人參養榮湯、八珍湯(丸)、當歸四逆湯、當歸六黃湯、養心湯、歸脾湯、十全大補湯、百合固金湯、清肺湯、八味帶下方、溫清飲(解毒四物湯)、調經丸、疏經活血湯、桃紅四物湯、溫經湯、三痹湯，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('當歸尾' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='當歸尾', contents = jd['m11']),                        
        ])
    elif ('人蔘' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='人蔘片', contents = jd['m12']),
                        TextSendMessage(text='藥材也用於：補中益氣湯、六君子湯(丸)、人參養榮湯、八珍湯(丸)、養心湯、四君子湯、歸脾湯、十全大補湯、炙甘草湯、半夏天麻白朮湯、益氣聰明湯、溫經湯，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('膨大海' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='膨大海', contents = jd['m13']),                        
        ])
    elif ('珠貝' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='珠貝', contents = jd['m14']),
                        TextSendMessage(text='藥材也用於：百合固金湯、清肺湯，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('枸杞' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='枸杞', contents = jd['m15']),
                        TextSendMessage(text='藥材也用於：杞菊地黃丸，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('熟地' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='熟地', contents = jd['m16']),
                        TextSendMessage(text='藥材也用於：人參養榮湯、八珍湯(丸)、當歸六黃湯、十全大補湯、百合固金湯、溫清飲(解毒四物湯)、桃紅四物湯、杞菊地黃丸，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('杜仲' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='杜仲', contents = jd['m17']),
                        TextSendMessage(text='藥材也用於：調經丸，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('一條根' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='一條根', contents = jd['m18']),                        
        ])
    elif ('陳皮' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='陳皮', contents = jd['m19']),
                        TextSendMessage(text='藥材也用於：補中益氣湯、六君子湯(丸)、人參養榮湯、清肺湯、八味帶下方、調經丸、疏經活血湯，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('雞血藤' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='雞血藤', contents = jd['m20']),                        
        ])
    elif ('狗脊' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='狗脊', contents = jd['m21']),                        
        ])
    elif ('黃精' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='黃精', contents = jd['m22']),                        
        ])
    elif ('三七' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='三七', contents = jd['m23']),                        
        ])
    elif ('菊花' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='菊花', contents = jd['m24']),
                        TextSendMessage(text='藥材也用於：杞菊地黃丸，輸入湯藥名，可以知道更多...'),                        
        ])
    elif ('肉蓯蓉' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='肉蓯蓉', contents = jd['m25']),                        
        ])
    elif ('肉桂' in message): 
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='肉桂(桂皮)', contents = jd['m26']), 
                        TextSendMessage(text='藥材也用於：養心湯、十全大補湯，輸入湯藥名，可以知道更多...'),                       
        ])    
    # 功能
    elif (message == '功能介紹'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='功能介紹', contents = jd['p1']),
        ])

    elif (message == '濕熱體質'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='外星人濕熱體質症狀', contents = jd['p4']),                        
        ])
    elif (message == '藥材清單'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='外星人濕熱體質症狀', contents = jd['p16']),                        
        ])









if __name__ == "__main__":
    app.run()

