import numpy as np
from PIL import Image, ImageOps
from flask import Flask, request, abort
# from flask_ngrok import run_with_ngrok

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

# from linebot.models.template import *

import json

# import CM_LineBot funtions
from cm_utils.utils import yolov5, naming
# from cm_utils.utils import get_ngrok_url

# 圖片下載與上傳專用
import urllib.request
import os

# 建立日誌紀錄設定檔
# https://googleapis.dev/python/logging/latest/stdlib-usage.html
import logging
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

# 啟用log的客戶端
client = google.cloud.logging.Client()

# 建立line event log，用來記錄line event
bot_event_handler = CloudLoggingHandler(client,name="cmlinebot_event")
bot_event_logger = logging.getLogger('cmlinebot_event')
bot_event_logger.setLevel(logging.INFO)
bot_event_logger.addHandler(bot_event_handler)

# load dialogue dict
file_jd = open('dialogue_dict.json', 'r', encoding='utf-8')
jd = json.load(file_jd)
file_jd.close()



app = Flask(__name__)
# 註冊機器人
line_bot_api = LineBotApi('Channel_Access_Token')
handler = WebhookHandler('Channel_Secret')


# 設定機器人訪問入口
@app.route('/callback', methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    # app.logger.info('Request body: ' + body)

    # 消息整個交給bot_event_logger，請它傳回GCP
    bot_event_logger.info(body)

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
# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     # 請line_bot_api回應，回應用戶講過的話
#     line_bot_api.reply_message(
#         event.reply_token,
#         TextSendMessage(text=event.message.text))


# 新增功能:follow時 取個資
from google.cloud import storage
from google.cloud import firestore
# 監看Follow事件, reply service info
from linebot.models.events import (
    FollowEvent
)

@handler.add(FollowEvent)
def reply_text_and_get_user_profile(event):

    # 取個資
    line_user_profile = line_bot_api.get_profile(event.source.user_id)

    # 跟line 取回照片，並放置在本地端
    file_name = line_user_profile.user_id+'.png'
    urllib.request.urlretrieve(line_user_profile.picture_url, file_name)

    # 設定storage內容
    storage_client = storage.Client()
    bucket_name = "cmlinebot-gcp-storage"
    destination_blob_name = f"{line_user_profile.user_id}/user_pic.png"
    source_file_name = file_name
    
    # 進行上傳
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)

    # 設定用戶資料json
    user_dict={
        "user_id":line_user_profile.user_id,
        "picture_url": f"https://storage.googleapis.com/{bucket_name}/{destination_blob_name}",
        "display_name": line_user_profile.display_name,
        "status_message": line_user_profile.status_message
    }
    # 插入firestore
    db = firestore.Client()
    doc_ref = db.collection(u'line-user').document(user_dict.get("user_id"))
    doc_ref.set(user_dict)

    # line_bot_api.reply_message(
    # event.reply_token,
    # TextSendMessage(text="個資已取"))
    
    # 刪除本地端檔案
    os.remove(file_name)

    # reply service info
    line_bot_api.reply_message(event.reply_token, FlexSendMessage(
              alt_text='介紹',
              contents=jd['p1']
    ))



# 接收圖像, 回傳預測結果字串及圖片
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):

    # 取出照片
    image_blob = line_bot_api.get_message_content(event.message.id)
    temp_file_path=f"""{event.message.id}.png"""

    with open(temp_file_path, 'wb') as fd:
        for chunk in image_blob.iter_content():
            fd.write(chunk)

    # 上傳 待預測圖片至cloud storage
    storage_client = storage.Client()
    bucket_name = "cmlinebot-gcp-storage"
    destination_blob_name = f'{event.source.user_id}/image/{event.message.id}.png'
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(temp_file_path)

    # model
    model_output = yolov5(temp_file_path)
    name_output = naming(model_output) # str
    # box_output = boxing(model_output, path) # url 
    
    # 上傳預測結果 renderout 圖片到cloud storage
    # yolov5函式輸出時 已覆蓋本地端 初始圖片temp_file_path
    storage_client = storage.Client()
    # bucket_name = "cmlinebot-gcp-storage"
    destination_blob_name = f'{event.source.user_id}/image/{event.message.id}'+'_out.png'
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(temp_file_path)

    # ready for access token
    import google.auth
    credentials, proj_id = google.auth.default()

    # Perform a refresh request to get the access token of the current credentials (Else, it's None)
    from google.auth.transport import requests
    r = requests.Request()
    credentials.refresh(r)    

    # prepare for generate reply img url
    storage_client = storage.Client()
    bucket_name = "cmlinebot-gcp-storage"
    destination_blob_name = f'{event.source.user_id}/image/{event.message.id}'+'_out.png'
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.get_blob(destination_blob_name) 
    # set signed url expiration time
    from datetime import datetime, timedelta 
    expires = datetime.now() + timedelta(minutes=15)

    # In case of user credential use, define manually the service account to use (for development purpose only)
    # service_account_email = "YOUR DEV SERVICE ACCOUNT"
    # If you use a service account credential, you can use the embedded email
    if hasattr(credentials, "service_account_email"):
        service_account_email = credentials.service_account_email
    
    # generate reply img url
    reply_img_url = blob.generate_signed_url(
        expiration=expires, 
        version='v4',
        method='GET',
        service_account_email=service_account_email, 
        access_token=credentials.token
    )
        
    
    # reply img url from cloud storage setting public
    # url_base = "https://storage.googleapis.com/"
    # url_path= f"{bucket_name}/{event.source.user_id}/image/{event.message.id}"+"_out.png"
    # reply_img_url = url_base + url_path


    # reply image url 
    # ngrok_url = "https://b5ed-35-204-95-221.ngrok.io"
    # ngrok_url = get_ngrok_url()    
    # reply_img_url = ngrok_url + "/material/" + event.message.id + ".png"

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

    # 移除本地端圖片
    os.remove(temp_file_path)


# 監看postback中的data
# 用於對話json內容中的按鈕action
@handler.add(PostbackEvent)
def handle_postback_message(event):
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
"""deprecated    
    # postback data of game
    elif (message == '留在地球'):
    
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='留在地球', contents = jd['g4']),                        
        ]) 
    elif (message == '進入外太空'):
    
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='進入外太空', contents = jd['g3']),
                        FlexSendMessage(alt_text='進入外太空', contents = jd['g5'])                        
        ])  
    elif (message == '我準備好了'):
    
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='我準備好了', contents = jd['g6']),                        
        ]) 
    elif (message == '易有口臭'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g11']),
                        FlexSendMessage(alt_text='我準備好了', contents = jd['g6']),                    
        ]) 
    elif (message == '易長痘痘濕疹'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g11']),
                        FlexSendMessage(alt_text='我準備好了', contents = jd['g6']),
        ]) 
    elif (message == '易口渴'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g11']),
                        FlexSendMessage(alt_text='我準備好了', contents = jd['g6']),                    
        ]) 
    elif (message == '易噁心嘔吐'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g11']),
                        FlexSendMessage(alt_text='我準備好了', contents = jd['g6']),                    
        ]) 
    elif (message == '以上皆是'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g14']),
                        FlexSendMessage(alt_text='以上皆是', contents = jd['g8']),                  
        ])
    elif (message == '八味帶下方'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g7']),
                        FlexSendMessage(alt_text='八味帶下方', contents = jd['g9']),                    
        ]) 
    elif (message == '清肺湯'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g11']),
                        FlexSendMessage(alt_text='以上皆是', contents = jd['g8']),                    
        ]) 
    elif (message == '十全大補湯'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g11']),
                        FlexSendMessage(alt_text='以上皆是', contents = jd['g8']),                    
        ]) 
    elif (message == '尋找夥伴'):
    
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='尋找夥伴', contents = jd['10']),                    
        ]) 
    elif (message == '單打獨鬥'):
    
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text=jd['g12']),                    
        ]) 
"""

# 監看message event
# 部分選單功能與使用者輸入(關鍵字)
@handler.add(MessageEvent)
def handle_keyword_message(event):
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
    elif (message == '影像辨識'):
        
        line_bot_api.reply_message(reply_token, [
                        TextSendMessage(text='拍照或上傳相片。請用白色或淺色背景，置放於中央。若是多樣藥材，勿重疊。辨識與回傳結果約10秒。'),                        
                        TextSendMessage(text='若須測試圖片，連結如下：https://drive.google.com/drive/folders/1WVoHNW6SeEtGjOHwuFocya6NH-TfY5ho?usp=sharing'),                        
        ])
"""deprecated
    elif (message == '進入遊戲'):
        
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='進入遊戲', contents = jd['g1']),                        
        ])
    elif (message == '遊戲開始'):
    
        line_bot_api.reply_message(reply_token, [
                        FlexSendMessage(alt_text='遊戲開始', contents = jd['g2']),                        
        ])       
"""
      

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

