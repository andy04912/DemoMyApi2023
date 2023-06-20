from datetime import datetime
from flask import Flask, jsonify, request,make_response,send_file
import psycopg2
import os
from roboflow import Roboflow
from werkzeug.utils import secure_filename
import random
from line_notify import lineNotifyMessage
import pytz
# 创建Flask应用程序
app = Flask(__name__)
app.config["UPLOADED_PHOTOS_DEST"] = "uploads"
app.config["PREDICT_PHOTOS_DEST"] = "predict"
# PostgreSQL数据库连接配置
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'

Bee_rf = Roboflow(api_key="opSC80eNUj4k5kPC3edb")
Bee_project = Bee_rf.workspace().project("honey-bee-detection-model-zgjnb")
Bee_model = Bee_project.version(2).model

# 创建数据库连接
conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

# 定义API路由
@app.route('/demobee/BeeBoxes', methods=['GET'])
def get_bees():
    # 创建数据库游标
    cursor = conn.cursor()
    
    # 执行查询语句
    cursor.execute("SELECT DISTINCT ON (hiveid) * FROM demobeedb ORDER BY hiveid, CreateTime;")
    
    # 获取查询结果
    results = cursor.fetchall()
    
    # 关闭游标
    cursor.close()
    
    # 将查询结果转换为JSON格式
    bees = []
    for row in results:
        bee = {
            'id': row[0],
            'HiveID': row[1],
            'NumberOfBees': row[2],
            'HasHornets': row[3],
            'CreateTime': row[4]
        }
        bees.append(bee)
    
    # 返回JSON响应
    return jsonify(bees)


# 定义API路由
@app.route('/demobee/BeeBoxes/<string:HiveBoxID>', methods=['GET'])
def getHiveBoxDetail(HiveBoxID):
    # 创建数据库游标
    cursor = conn.cursor()
    
    # 执行查询语句
    cursor.execute("SELECT * FROM demobeedb WHERE HiveID = %s",(HiveBoxID))
    
    # 获取查询结果
    results = cursor.fetchall()
    
    # 关闭游标
    cursor.close()
    
    # 将查询结果转换为JSON格式
    bees = []
    for row in results:
        bee = {
            'id': row[0],
            'HiveID': row[1],
            'NumberOfBees': row[2],
            'HasHornets': row[3],
            'CreateTime': row[4]
        }
        bees.append(bee)
    
    # 返回JSON响应
    return jsonify(bees)

@app.route('/demobee/ReactUpload', methods=['POST'])
def fileUpload():
    if 'file' in request.files:
        file = request.files['file']   
        ID = None  
        if 'ID' in request.files:    
            ID = request.files['ID'] 
            print('test2'+ID)
        filename = "upload.jpg"
        if not os.path.exists(app.config["UPLOADED_PHOTOS_DEST"]):
            os.mkdir(app.config["UPLOADED_PHOTOS_DEST"])
        file.save(app.config["UPLOADED_PHOTOS_DEST"]+"/"+filename)
        return dectectAndNotify("uploads/"+filename,ID)
    else:
        return "Please package the file into an object ['file':source]"
    
def dectectAndNotify(path,ID):
    beens = Bee_model.predict(path, confidence=40, overlap=30).json()
    numberOfBees =  len([x for x in beens['predictions'] if x['class'] == 'bee'])
    
    
    hiveID = ID
    if hiveID is None:
        hiveID = random.randint(1,5)
    # hornets = Hornet_model.predict(path, confidence=40, overlap=30).json()
    hasHornets = 0
    res = "upload success"
    if numberOfBees>0:
        res = AddData(hiveID,numberOfBees,hasHornets)
        Bee_model.predict(path, confidence=40, overlap=30).save(app.config["PREDICT_PHOTOS_DEST"] +"/prediction.jpg")
        lineNotifyMessage('第'+str(hiveID)+'號蜂箱共有'+str(numberOfBees)+'隻蜜蜂',"predict/prediction.jpg",'1PjoEvLBC7DkqV9NERBwVfuzSGHjIquZEImI5PWo8Sn' )
    return send_file(app.config["PREDICT_PHOTOS_DEST"] +"/prediction.jpg",mimetype='image/jpeg')

def AddData(hiveID,numberOfBees,hasHornets):
    try:
        cursor = conn.cursor()

        cursor.execute("select count(*) from demobeedb")
        row_count = cursor.fetchone()[0]+1
        cursor.execute("INSERT INTO demobeedb (id,HiveID, NumberOfBees, HasHornets, CreateTime) VALUES (%s,%s, %s, %s, %s)",
                   (row_count,hiveID,numberOfBees,0,datetime.now(pytz.timezone('GMT'))))
    

        conn.commit()
    

        cursor.close()
    except Exception as e:
        print(e)
        responseObject = {
            'status': 'fail',
            'message': str(e)
        }
        return make_response(jsonify(responseObject)), 500 
    return jsonify(numberOfBees)


# @app.route('/bees', methods=['POST'])


# 启动Flask应用程序
if __name__ == '__main__':
    app.run()
