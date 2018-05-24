from . import api
from flask import jsonify, request, current_app
import pymongo, os
from .computeDis import cal_dis
from qiniu import Auth, put_file, BucketManager
from bson import ObjectId
import json, time, requests

# 连接到mongodb
client = pymongo.MongoClient('127.0.0.1:27017')
# 连接到数据库
db = client["waimai-db"]


# 获取用户location和address
@api.route('/getlocation')
def getlocation():
    ip = request.args.get('ip', '')
    if ip == '':
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        result = {}
        loc_url = 'http://apis.map.qq.com/ws/location/v1/ip'
        add_url = 'http://apis.map.qq.com/ws/geocoder/v1/'
        params_loc = {'key': current_app.config['TENCENT_MAP_KEY'], 'ip': ip}
        loc_res = requests.get(loc_url, params=params_loc)
        location = str(loc_res.json()['result']['location']['lat']) + ',' + str(loc_res.json()['result']['location']['lng'])
        result['location'] = location
        params_add = {'location': location, 'key': current_app.config['TENCENT_MAP_KEY']}
        add_res = requests.get(add_url, params=params_add)
        result['address'] = add_res.json()['result']['address']
        return jsonify({'code': 1, 'data': result})


# 获取定位地址列表建议
@api.route('/getsug')
def getsug():
    keyword = request.args.get('kw', '')
    if keyword == '':
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        sug_url = 'http://apis.map.qq.com/ws/place/v1/suggestion'
        params = {'keyword': keyword, 'key': current_app.config['TENCENT_MAP_KEY']}
        res = requests.get(sug_url, params=params)
        return jsonify({'code': 1, 'data': res.json()})


# 获取店铺（首页及分类页展示）
@api.route('/getshops')
def getshops():
    # 商家类型
    s_type = request.args.get('type', 0)
    page = request.args.get('page', 0)
    user_location = request.args.get('location', 0)
    if not (s_type and page and user_location):
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['shopInfo']
        result = list(db_coll.find({'type': int(s_type)}, projection={'foodtype': False, 'ad': False}).skip((int(page)-1)*4).limit(4))
        for each in result:
            id = each.pop('_id')
            location = each.pop('location')
            lat, lng = user_location.split(',')
            each['distance'] = round(cal_dis(float(lat), float(lng), location[0], location[1]), 1)
            each['dltime'] = round(each['distance'] / 1.5, 1)
            each['_id'] = str(id)
        return jsonify({'code': 1, 'data': result})


# 查询店铺
@api.route('/searchshops')
def searchshops():
    # 获取关键字
    keyword = request.args.get('kw', '')
    user_location = request.args.get('location', '')
    if (keyword == '' or user_location == ''):
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['shopInfo']
        result = list(db_coll.find({'$or': [{'title': keyword}, {'title': {'$regex': keyword}}]}, projection=['title', 'imgUrl', 'location']))
        for each in result:
            id = each.pop('_id')
            location = each.pop('location')
            lat, lng = user_location.split(',')
            each['dltime'] = round(round(cal_dis(float(lat), float(lng), location[0], location[1]), 1) / 1.5, 1)
            each['_id'] = str(id)
        return jsonify({'code': 1, 'data': result})


# 获取店铺详情
@api.route('/getshop')
def getshop():
    s_id = request.args.get('id', '')
    if s_id == '':
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库
        db_coll = db['shopInfo']
        result = db_coll.find_one({'_id': ObjectId(s_id)}, projection={'foodtype': False})
        id = result.pop('_id')
        result['_id'] = str(id)
        return jsonify({'code': 1, 'data': result})

# 获取店铺商品
@api.route('/getgoods')
def getgoods():
    s_id = request.args.get('id', '')
    if s_id == '':
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库
        db_coll = db['shopInfo']
        result = db_coll.find_one({'_id': ObjectId(s_id)}, projection=['foodtype'])
        result.pop('_id')
        return jsonify({'code': 1, 'data': result})


# 查询用户是否注册
@api.route('/getuser')
def getuser():
    # 获取关键字
    u_name = request.args.get('username', '')
    if u_name == '':
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['userInfo']
        result = db_coll.find_one({'name': u_name})
        # 如果已经注册，返回值为1，否则为0
        if result:
            data = 1
        else:
            data = 0
        return jsonify({'code': 1, 'data': data})


# 注册用户
@api.route('/register')
def register():
    # 获取关键字
    u_name = request.args.get('username', '')
    u_pwd = request.args.get('password', '')
    if (u_name == '' or u_pwd == ''):
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['userInfo']
        user = {'name': u_name, 'password': u_pwd, 'avatar': 'http://i.waimai.meituan.com/static/img/default-avatar.png'}
        db_coll.insert_one(user)
        user.pop('_id')
        return jsonify({'code': 1, 'data': user})


# 登录用户
@api.route('/login')
def login():
    # 获取关键字
    u_name = request.args.get('username', '')
    u_pwd = request.args.get('password', '')
    if (u_name == '' or u_pwd == ''):
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['userInfo']
        result = db_coll.find_one({'name': u_name, 'password': u_pwd}, projection={'_id': False})
        if result:
            return jsonify({'code': 1, 'data': result})
        else:
            return jsonify({'code': 0, 'error': '密码错误!'})


# 上传用户头像
@api.route('/uploadavatar', methods=['POST'])
def uploadavater():
    imgfile = request.files.get('file', None)
    u_name = request.form.get('username', '')
    if imgfile == None:
       return jsonify({'code': 0, 'err': '未成功获取文件,上传失败!'})
    elif u_name == '':
        return jsonify({'code': 0, 'err': '未发送用户名,上传失败!'})
    else:
        filename = imgfile.filename
        if '.' in filename and filename.split('.')[1] in current_app.config['ALLOWED_EXTENSIONS']:
            access_key = current_app.config['QINIU_ACCESS_KEY']
            secret_key = current_app.config['QINIU_SECRET_KEY']
            q = Auth(access_key, secret_key)
            bucket_name = 'blogimage'
            key = filename
            token = q.upload_token(bucket_name, key, 3600)
            with open(filename, 'wb') as f:
                f.write(imgfile.read())
            localfile = filename
            # 如果用户修改过头像，则删除之前的头像文件，否则进行上传并修改数据
            db_coll = db['userInfo']
            result = db_coll.find_one({'name': u_name})
            if result['avatar'] != 'http://i.waimai.meituan.com/static/img/default-avatar.png':
                bucket = BucketManager(q)
                delete_key = result['avatar'].split('/')[-1]
                bucket.delete(bucket_name, delete_key)
            put_file(token, key, localfile)
            os.remove(filename)
            new_avatar = "http://oq39ef5bt.bkt.clouddn.com/%s" % filename
            db_coll.update_one({'name': u_name}, {'$set': {'avatar': new_avatar}})
            user = db_coll.find_one({'name': u_name}, projection={'_id': False})
            return jsonify({'code': 1, 'data': user})
        else:
            return jsonify({'code': 0, 'err': '上传图片格式不正确!'})


# 获取用户信息
@api.route('/getuserInfo')
def getuserinfo():
    u_name = request.args.get('username', '')
    if u_name == '':
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['userInfo']
        result = db_coll.find_one({'name': u_name}, projection={'_id': False})
        return jsonify({'code': 1, 'data': result})


# 获取用户收货地址信息api
@api.route('/getRaddress')
def getraddress() :
    u_name = request.args.get('username', '')
    if u_name == '':
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['userInfo']
        user = db_coll.find_one({'name': u_name}, projection={'_id': False})
        result = user['r_address']
        return jsonify({'code': 1, 'data': result})


# 设置用户默认收货地址
@api.route('/setdefault')
def setdefault():
    u_name = request.args.get('username', '')
    default_index = request.args.get('index', '')
    if u_name == '' or default_index == '':
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['userInfo']
        user = db_coll.find_one({'name': u_name}, projection={'_id': False})
        r_address = user['r_address']
        for i in range(len(r_address)):
            if i == int(default_index):
                r_address[i]['default'] = True
            else:
                if r_address[i]['default']:
                    r_address[i]['default'] = False
                else:
                    continue
        db_coll.update_one({'name': u_name}, {'$set': {'r_address': r_address}})
        result = db_coll.find_one({'name': u_name}, projection={'_id': False})
        return jsonify({'code': 1, 'data': result})


# 删除用户收货地址
@api.route('/delRaddress')
def delraddress():
    u_name = request.args.get('username', '')
    del_str = request.args.get('del', '')
    if u_name == '' or del_str == '':
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['userInfo']
        user = db_coll.find_one({'name': u_name}, projection={'_id': False})
        r_address = user['r_address']
        length_list = list(range(len(r_address)))
        for each in del_str:
            length_list.remove(int(each))
        new_address = []
        for each in length_list:
            new_address.append(r_address[each])
        db_coll.update_one({'name': u_name}, {'$set': {'r_address': new_address}})
        result = db_coll.find_one({'name': u_name}, projection={'_id': False})
        return jsonify({'code': 1, 'data': result})


# 新增用户收货地址
@api.route('/addReceive', methods=['POST'])
def addreceive():
    u_name = request.form.get('username', '')
    name = request.form.get('rname', '')
    sex = request.form.get('sex', '')
    number = request.form.get('number', '')
    address = request.form.get('raddress', '')
    if (u_name == '' or name == '' or sex == '' or number == '' or address == ''):
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['userInfo']
        result = db_coll.find_one({'name': u_name})
        old_address = result.get('r_address', None)
        if old_address:
            add = {
                'name': name,
                'sex': sex,
                'number': number,
                'address': address,
                'default': False,
            }
            old_address.append(add)
            db_coll.update_one({'name': u_name}, {'$set': {'r_address': old_address}})
        else:
            add = [{
                'name': name,
                'sex': sex,
                'number': number,
                'address': address,
                'default': False,
            }]
            db_coll.update_one({'name': u_name}, {'$set': {'r_address': add}})
        user = db_coll.find_one({'name': u_name}, projection={'_id': False})
        return jsonify({'code': 1, 'data': user})


# 获取订单信息
@api.route('/getOrderInfo')
def getorder():
    order_id = request.args.get('id', '')
    if order_id == '':
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        db_coll = db['orderInfo']
        result = db_coll.find_one({'_id': ObjectId(order_id)})
        result.pop('_id')
        return jsonify({'code': 1, 'data': result})


# 新增订单
@api.route('/pushOrder', methods=['POST'])
def pushorder():
    shop_id = request.form.get('s_id', '')
    goods_list = request.form.get('goods', '')
    total_price = request.form.get('total', '')
    r_address = request.form.get('addressInfo', '')
    u_name = request.form.get('username', '')
    if (shop_id == '' or goods_list == '' or total_price == '' or r_address == '' or u_name == ''):
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['orderInfo']
        new_order = {
            'username': u_name,
            'shop_id': shop_id,
            'total_price': total_price,
            'r_address': json.loads(r_address),
            'goods': json.loads(goods_list),
        }
        db_coll.insert_one(new_order)
        order_id = str(new_order.pop('_id'))
        return jsonify({'code': 1, 'data': order_id})


# 删除订单
@api.route('/deleteOrder')
def deleteorder():
    order_id = request.args.get('id', '')
    if order_id == '':
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        db_coll = db['orderInfo']
        db_coll.delete_one({'_id': ObjectId(order_id)})
        return jsonify({'code': 1})


# 支付成功修改订单状态
@api.route('/editOrder')
def editorder():
    order_id = request.args.get('id', '')
    pay_type = request.args.get('paytype', '')
    pay_way = request.args.get('payway', '')
    if order_id == '' or pay_type == '' or pay_way == '':
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        db_coll = db['orderInfo']
        infoObj = [
            {
                '1': '支付宝',
                '2': '微信'
            },
            {
                '1': '扫码支付',
                '2': 'APP支付'
            },
        ]
        newAttri = {
            'pay_type': infoObj[0][pay_type],
            'pay_way': infoObj[1][pay_way],
            'hasComment': False,
            'date': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }
        db_coll.update_one({'_id': ObjectId(order_id)}, {'$set': newAttri})
        return jsonify({'code': 1})


# 获取用户所有订单信息
@api.route('/getUserOrders')
def get_user_orders():
    u_name = request.args.get('username', '')
    if u_name == '':
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        order_coll = db['orderInfo']
        shop_coll = db['shopInfo']
        order_info_list = ['shop_id', 'total_price', 'hasComment', 'date']
        user_orders = list(order_coll.find({'username': u_name}, projection=order_info_list).sort('_id', -1))
        for i in range(len(user_orders)):
            shop_info = shop_coll.find_one({'_id': ObjectId(user_orders[i]['shop_id'])})
            id = user_orders[i].pop('_id')
            user_orders[i]['id'] = str(id)
            user_orders[i]['shop_img'] = shop_info['imgUrl']
            user_orders[i]['shop_name'] = shop_info['title']
        return jsonify({'code': 1, 'data': user_orders})


# 上传评价图片
@api.route('/uploadImg', methods=['POST'])
def upload_img():
    imgfile = request.files.get('file', None)
    if imgfile == None:
        return jsonify({'code': 0, 'err': '未成功获取文件,上传失败!'})
    else:
        filename = imgfile.filename
        if '.' in filename and filename.split('.')[1] in current_app.config['ALLOWED_EXTENSIONS']:
            access_key = current_app.config['QINIU_ACCESS_KEY']
            secret_key = current_app.config['QINIU_SECRET_KEY']
            q = Auth(access_key, secret_key)
            bucket_name = 'blogimage'
            key = filename
            token = q.upload_token(bucket_name, key, 3600)
            with open(filename, 'wb') as f:
                f.write(imgfile.read())
            localfile = filename
            put_file(token, key, localfile)
            os.remove(filename)
            img_url = "http://oq39ef5bt.bkt.clouddn.com/%s" % filename
            return jsonify({'code': 1, 'data': img_url})
        else:
            return jsonify({'code': 0, 'err': '上传图片格式不正确!'})


# 删除评价图片
@api.route('/deleteImg')
def delete_img():
    filename = request.args.get('filename', '')
    if filename == '':
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        access_key = current_app.config['QINIU_ACCESS_KEY']
        secret_key = current_app.config['QINIU_SECRET_KEY']
        q = Auth(access_key, secret_key)
        bucket_name = 'blogimage'
        bucket = BucketManager(q)
        delete_key = filename
        bucket.delete(bucket_name, delete_key)
        return jsonify({'code': 1})


# 提交评价
@api.route('/uploadComment', methods=['POST'])
def upload_comment():
    order_id = request.form.get('id', '')
    u_name = request.form.get('username', '')
    avatar = request.form.get('avatar', '')
    d_rate = request.form.get('drate', '')
    s_rate = request.form.get('srate', '')
    content = request.form.get('content', '')
    img_list = request.form.get('imglist', '')
    if (order_id == '' or d_rate == '' or s_rate == '' or content == '' or u_name == '' or avatar == '' or img_list == ''):
        return jsonify({'code': 0, 'err': '请求类型不正确'})
    else:
        order_coll = db['orderInfo']
        shop_coll = db['shopInfo']
        order_coll.update_one({'_id': ObjectId(order_id)}, {'$set': {'hasComment': True}})
        order = order_coll.find_one({'_id': ObjectId(order_id)})
        shop_id = order['shop_id']
        new_obj = {
            'name': u_name,
            'avatar': avatar,
            'd_rate': d_rate,
            's_rate': s_rate,
            'content': content,
            'date': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            'img': json.loads(img_list)
        }
        shop = shop_coll.find_one({'_id': ObjectId(shop_id)})
        shop_comments = shop.get('comments', None)
        if shop_comments:
            shop_comments.append(new_obj)
            shop_coll.update_one({'_id': ObjectId(shop_id)}, {'$set': {'comments': shop_comments}})
        else:
            new_obj = [
                {
                    'name': u_name,
                    'avatar': avatar,
                    'd_rate': d_rate,
                    's_rate': s_rate,
                    'content': content,
                    'date': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    'img': json.loads(img_list)
                }
            ]
            shop_coll.update_one({'_id': ObjectId(shop_id)}, {'$set': {'comments': new_obj}})
        return jsonify({'code': 1})


# 拉取商家评论
@api.route('/getcomments')
def get_comments():
    # 商家类型
    shop_id = request.args.get('id', '')
    page = request.args.get('page', '')
    if shop_id == '' or page == '':
        return jsonify({'code': 0, 'error': '请求类型不正确'})
    else:
        # 连接到数据库表
        db_coll = db['shopInfo']
        result = db_coll.find_one({'_id': ObjectId(shop_id)}, projection=['comments'])
        result.pop('_id')
        comments = result['comments'][(int(page)-1)*10:int(page)*10]
        return jsonify({'code': 1, 'data': comments})