# -*- coding: UTF-8 -*-
import random
import re
from os import abort
from flask import make_response, jsonify
from flask import current_app
from flask import request
from flask import session

from info import constants, db
from info import redis_store
from info.libs.yuntongxun.sms import CCP
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from . import passport_blu
from info.models import User
from datetime import datetime


@passport_blu.route('/image_code')
def get_image_code():
    """产生图片验证码"""

    # 1. 获取验证码图片标识
    image_code_id = request.args.get('image_code_id')
    if not image_code_id:
        # abort(400)
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')
    # 2. 产生验证码图片
    # 图片名称 验证码文本 验证码图片内容
    name, text, content = captcha.generate_captcha()
    current_app.logger.info("图片验证码内容为：%s" % text)

    # 3. 在redis中保存图片验证码文本
    try:
        redis_store.set("imagecode:%s" % image_code_id, text, constants.IMAGE_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存图片验证码失败')

    # 4. 创建响应对象
    response = make_response(content)
    # 设置响应数据类型
    response.headers['Content-Type'] = 'image/jpg'

    return response


@passport_blu.route('/sms_code', methods=['POST'])
def send_sms_code():
    """发送短信验证码"""
    # 1. 获取参数(手机号,图片验证码,图片验证码id)并进行参数校验
    req_dict = request.json
    if not req_dict:
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

    mobile = req_dict.get('mobile')
    image_code = req_dict.get('image_code')
    image_code_id = req_dict.get('image_code_id')

    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

    if not re.match(r'^1[3578]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式不正确')

    # 2. 根据image_code_id获取对应的图片验证码文本
    try:
        real_image_code = redis_store.get('imagecode:%s' % image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取图片验证码失败')

    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg='图片验证码已过期')

    # 3. 对应图片验证码
    if real_image_code.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg='图片验证码错误')

    # 4. 产生随机6位的短信验证码内容
    sms_code = '%06d' % random.randint(0, 999999)
    current_app.logger.info("短信验证码内容为：%s" % sms_code)

    # 5. 在redis中保存短信验证码
    try:
        redis_store.set('smscode:%s' % mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.looger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存图片验证码失败')

    # 6. 给用户的手机发送短信验证码
    try:
        res = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES/60], 1)
    except Exception as e:
        current_app.looger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='发送短信验证码失败')
    #
    if res != 0:
        return jsonify(errno=RET.THIRDERR, errmsg='发送短信验证码失败')

    # 7. 返回应答，发送短信成功
    return jsonify(errno=RET.OK, errmsg='发送短信验证码成功')


@passport_blu.route('/register', methods=['POST'])
def register():
    """用户注册"""
    # 1.获取参数(手机号，密码，短信验证码)并进行参数校验
    # 2.获取redis中保存的短信验证码
    # 3.对比短信验证码，如果一致
    # 4.创建User对象并保存注册用户信息
    # 5.将注册用户信息添加进数据库
    # 6.返回应答，注册成功

    # 1.获取参数(手机号，密码，短信验证码)并进行参数校验
    req_dict = request.json
    if not req_dict:
        return jsonify(errno=RET.PARAMERR, errmsg="缺少参数")

    mobile = req_dict.get('mobile')
    sms_code = req_dict.get('sms_code')
    password = req_dict.get('password')

    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

    if not re.match(r'^1[3578]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式不正确')

    # 2.获取redis中保存的短信验证码
    try:
        real_sms_code = redis_store.get('smscode:%s' % mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取短信验证码失败')

    if not sms_code:
        return jsonify(errno=RET.NODATA, errmsg='短信验证码已过期')

    # 3.对比短信验证码，如果一致
    if real_sms_code != sms_code:
        return jsonify(errno=RET.DATAERR, errmsg='短信验证码错误')

    # 4.创建User对象并保存注册用户信息
    user = User()
    user.mobile = mobile
    user.nick_name = mobile
    user.password = password

    # 5.将注册用户信息添加进数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存注册用户信息失败')

    # 6.返回应答，注册成功
    return jsonify(errno=RET.OK, errmsg='注册成功')


@passport_blu.route('/login', methods=['POST'])
def login():
    """
       用户登录:
       1. 获取参数(手机号，密码)并进行参数校验
       2. 根据手机号查询用户信息
       3. 判断用户密码是否正确
       4. 记住用户的登录状态，在session中保存登录用户的信息
       5. 记录用户的最后一次登录时间
       6. 返回应答，登录成功
    """

    # 1.获取参数(手机号，密码)并进行参数校验
    req_dict = request.json
    if not req_dict:
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

    mobile = req_dict.get('mobile')
    password = req_dict.get('password')

    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

    if not re.match(r'^1[3578]\d{9}$', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg='手机号格式不正确')

    # 2.根据手机号查询用户信息
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户信息失败')

    if not user:
        return jsonify(errno=RET.NODATA, errmsg='用户不存在')

    # 3.判断用户密码是否正确
    if not user.check_passowrd(password):
        return jsonify(errno=RET.PWDERR, errmsg='登录密码错误')

    # 4.记住用户的登录状态，在session中保存登录用户的信息
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile

    # 5.记录用户的最后一次登录时间
    user.last_login = datetime.now()

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)

    # 6.返回应答，登录成功
    return jsonify(errno=RET.OK, errmsg='登陆成功')


@passport_blu.route('/logout', methods=['POST'])
def logout():
    """退出登陆"""
    # 请求session中用户的登陆状态信息
    session.pop('user_id')
    session.pop('mobile')
    session.pop('nick_name')

    # 返回应答，退出登录成功
    return jsonify(errno=RET.OK, errmsg='退出登录成功')