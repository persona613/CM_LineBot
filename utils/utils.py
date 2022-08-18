from PIL import Image



# yolo v5 model, downloan to your personal good drive and connect google drive to colab
def yolov5(img):
    import io
    import torch
    
    # Model
    model = torch.hub.load('/yolov5', model='custom', path='change-hyp24.pt', source='local')
    # 以上兩個位置，前者為模型所需要的設定檔，後為模型檔，
    # 目前從google drive掛載，可改為自行上傳或其他位置，/content/drive/MyDrive/不變，
    # 後面改成模型檔改名v1.pt的位置（資料夾）

    # imgs = ['/content/hongzao_heizao_pengdahai_0008.jpg']  
    # 若無串接line bot，可直接於本機端或其他途徑傳入

    # Inference
    results = model(img)

    # 以下是各種輸出的格式，挑需要的使用
    # results.print()
    # results.save()  # or .show()
    # results.xyxy[0]  # img1 predictions (tensor)
    # results.pandas().xyxy[0]  # img1 predictions (pandas)
    try:
        return results.pandas().xyxy[0].to_json(orient='records', force_ascii=False) 
        # 此處輸出成json，list裡包dict，但機器仍辨識為str，後面讀取需要做格式轉換

    
    finally:
        # updates results.imgs with boxes and labels
        imgs = results.render()
        im = Image.fromarray(imgs[0])
        # take image's file name
        im_name = img.rsplit('/',1)[-1]
        # save image at local
        im_savepath = f'/material/{im_name}'
        im.save(im_savepath)

