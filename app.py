#-*- encoding: utf-8 -*-

from flask import jsonify, request, render_template, url_for, redirect
from models import Trash, Can, app, db
import json
import os

import torch
import torchvision
import torchvision.transforms as transforms
import torchvision.models as models
import torch.nn as nn
import torch.nn.functional as F

from PIL import Image
from pathlib import Path

app.config['UPLOAD_FOLDER'] = os.getcwd() + '/uploads'
app.config['JSON_AS_ASCII'] = False

transformations = transforms.Compose([transforms.Resize(256),
                                    transforms.CenterCrop(224),
                                    transforms.ToTensor(),
                                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])

def predict_image(img):
    xb = img.unsqueeze(0).to(device)
    yb = model(xb)
    prob, preds = torch.max(yb, dim=1)
    print(prob,preds)
    print(preds[0].item(), type(preds[0].item()))
    return classes_dict[str(preds[0].item())]

class OurModel(nn.Module):
    def forward(self, xb):
        return torch.softmax(self.backbone(xb), dim=1)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = torch.load('_static/resnext50_32x4d.pt', map_location = device)
model.eval()
classes_dict = json.load(open('_static/trash_class_index.json', encoding='cp949'))
print(f'current device = {device}')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET','POST'])
def search():
    if request.method == 'GET':
        return render_template('search.html')
    else: # POST
        print(f'/search - POST called.')
        found_trash = Trash.query.filter_by(trash_name=request.form['trash_name']).first()
        return f'tid = {found_trash.tid}, 이름 = {found_trash.trash_name}, 종류 = {found_trash.trash_type}'

@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')
    else: # POST
        print(f'/upload - POST called.')
        if request.files:
            try:
                os.stat(app.config['UPLOAD_FOLDER'])
            except:
                os.mkdir(app.config['UPLOAD_FOLDER'])
                
            img = request.files['inputimg']
            img.save(os.path.join(app.config['UPLOAD_FOLDER'] , img.filename))

            img = transformations(Image.open(os.path.join(app.config['UPLOAD_FOLDER'] , img.filename)))
            class_id, class_name = predict_image(img)
            print(class_id, class_name)
            
            found_trash = Trash.query.filter_by(trash_name=class_name).first()
            resultJson = jsonify({'tid': found_trash.tid, 'name': found_trash.trash_name, 'type': found_trash.trash_type, 'howto': found_trash.trash_howto_desc, 'howtoid': found_trash.trash_howto_id})
            return resultJson
        return redirect(url_for('upload'))

@app.route('/can', methods=['GET'])
def can():
    if request.method == 'GET':
        print('can - GET called.')
        trash_type = request.args.get("trash_type")
        city = request.args.get("city")

        found_can = Can.query.filter_by(trash_type=trash_type, city=city).all()

        resultJson = []
        for can in found_can:
            resultJson.append(can.dict())

        return jsonify(resultJson)

if __name__ == "__main__":
    db.create_all()
    app.run(host='0.0.0.0', port= 3654)
