# -*- coding: UTF-8 -*-
import functools

from flask import abort
from flask import redirect

from info import constants
from info.models import User
from flask import current_app, g, jsonify
from flask import session

from info.utils.response_code import RET


def do_rank_class(index):
    """返回首页新闻排行对应的class"""
    if index < 0 or index >= 3:
        return ''

    rank_class_li = ['first', 'second', 'third']

    return rank_class_li[index]


def login_user_data(view_func):
    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):
        # 尝试从session中获取user_id
        user_id = session.get('user_id')

        user = None
        if user_id:
            try:
                from info.models import User
                user = User.query.get(user_id)
                user.avatar_url_path = constants.QINIU_DOMIN_PREFIX + user.avatar_url if user.avatar_url else ''
            except Exception as e:
                current_app.logger.error(e)

        # 使用g变量临时保存user
        g.user = user

        return view_func(*args, **kwargs)
    return wrapper


def login_required(view_func):
    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):
        # 尝试从session中获取user_id
        user_id = session.get('user_id')

        if not user_id:
            #用户未登录
            return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')

        user = None
        try:

            user = User.query.get(user_id)
            user.avatar_url_path = constants.QINIU_DOMIN_PREFIX + user.avatar_url if user.avatar_url else ''
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='获取用户信息失败')

        # 使用g变量临时保存user
        g.user = user
        return view_func(*args, **kwargs)
    return wrapper


def do_news_status(index):
    """返回发布信息的状态"""
    assert index in (0, 1, -1)

    status_dict = {
        0: '已通过',
        1: '审核中',
        -1: '未通过'
    }
    return status_dict[index]


def admin_login_required(view_func):
    @functools.wraps(view_func)
    def wrapper(*args, **kwargs):
        # 尝试从session中获取user_id
        user_id = session.get('user_id')
        is_admin = session.get('is_admin')

        if not user_id or not is_admin:
            # 登录用户不是管理员或用户未登录，直接跳转到首页
            return redirect('/')

        user = None
        try:
            user = User.query.get(user_id)
            user.avatar_url_path = constants.QINIU_DOMIN_PREFIX + user.avatar_url if user.avatar_url else ''
        except Exception as e:
            current_app.logger.error(e)
            abort(500)

        g.user = user

        return view_func(*args, **kwargs)
    return wrapper