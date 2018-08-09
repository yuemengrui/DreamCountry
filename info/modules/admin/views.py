# -*- coding: UTF-8 -*-
import datetime
from flask import abort
from flask import current_app, jsonify
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from sqlalchemy import extract

from info import constants
from info import db
from info.models import User, News, Category
from info.modules.admin import admin_blu
from info.utils.commons import admin_login_required
from info.utils.image_storage import storage
from info.utils.response_code import RET


@admin_blu.route('/login', methods=['GET', 'POST'])
def login():
    """后台管理登录页面"""
    if request.method == 'GET':
        return render_template('admin/login.html')
    else:
        # 进行后台登录判断
        # 1. 接收参数并进行参数校验
        username = request.form.get('username')
        password = request.form.get('password')

        if not all([username, password]):
            flash('参数不足')
            return redirect(url_for('admin.login'))

        # 2. 根据用户名查询管理员信息
        try:
            user = User.query.filter(User.nick_name == username, User.is_admin == True).first()
        except Exception as e:
            current_app.logger.error(e)
            flash('数据查询失败')
            return redirect(url_for('admin.login'))

        if not user:
            flash('管理员不存在')
            return redirect(url_for('admin.login'))

        # 3. 判断管理员的密码是否正确
        if not user.check_passowrd(password):
            flash('登录密码错误')
            return redirect(url_for('admin.login'))

        # 4. 在session中记住用户的登录状态
        session['user_id'] = user.id
        session['nick_name'] = user.nick_name
        session['mobile'] = user.mobile
        session['is_admin'] = True

        # 5. 登录成功
        return redirect(url_for('admin.index'))


@admin_blu.route('/index', methods=['GET', 'POST'])
@admin_login_required
def index():
    """管理后台首页"""
    user = g.user
    return render_template('admin/index.html', user=user)


@admin_blu.route('/logout', methods=['POST'])
def logout():
    """
    管理员退出登录
    清除session中的对应登录之后保存的信息
    """
    session.pop('user_id')
    session.pop('nick_name')
    session.pop('mobile')
    session.pop('is_admin')

    # 返回结果
    return jsonify(errno=RET.OK, errmsg='OK')


@admin_blu.route('/user/count')
@admin_login_required
def user_count():
    """后台管理用户信息统计页面"""
    # 统计网站用户总数
    total_count = User.query.filter(User.is_admin == False).count()

    # 统计当月新增用户数量
    now_date = datetime.datetime.now()
    year = now_date.year
    month = now_date.month
    month_count = db.session.query(User).filter(extract('year', User.create_time) == year,
                                                extract('month', User.create_time) == month).count()

    # 统计当天新增用户数据
    day = now_date.day
    day_count = db.session.query(User).filter(extract('year', User.create_time) == year,
                                              extract('month', User.create_time) == month,
                                              extract('day', User.create_time) == day).count()

    # 统计近31天每天增加的用户的数量
    date_li = []
    day_counts = []
    # 计算今天的前30天是几月几号
    begin_date = now_date - datetime.timedelta(days=30)

    # 遍历近31天每天增加的用户的数量
    for i in range(31):
        cur_date = begin_date + datetime.timedelta(days=i)
        year = cur_date.year
        month = cur_date.month
        day = cur_date.day

    # 统计当天新增的用户数量
    count = db.session.query(User).filter(extract('year', User.create_time) == year,
                                          extract('month', User.create_time) == month,
                                          extract('day', User.create_time) == day).count()

    # 将datetime类型格式化为字符串内容
    begin_date_str = cur_date.strftime("%Y-%m-%d")
    # 将对应日期添加到date_li列表中
    date_li.append(begin_date_str)
    # 将对应日期增加的用户数量添加到days_count列表中
    day_counts.append(count)

    return render_template('admin/user_count.html',
                           total_count=total_count,
                           month_count=month_count,
                           day_count=day_count,
                           date_li=date_li,
                           day_counts=day_counts)


@admin_blu.route('/user/list')
@admin_login_required
def user_list():
    """后台管理用户列表信息页面"""
    # 1. 获取参数并进行校验
    page = request.args.get('p', 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    # 2. 获取所有普通用户信息并进行分页
    try:
        pagination = User.query.filter(User.is_admin == False). \
            order_by(User.create_time.desc()). \
            paginate(page, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        users = pagination.items
        total_page = pagination.pages
        current_page = pagination.page
    except Exception as e:
        current_app.logger.error(e)
        abort(500)

    return render_template('admin/user_list.html',
                           users=users,
                           total_page=total_page,
                           current_page=current_page)


@admin_blu.route('/news/review')
@admin_login_required
def news_review():
    """后台管理新闻审核页面"""
    # 1.获取参数并进行校验
    page = request.args.get('p', 1)
    key = request.args.get('key')

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    # 2. 获取所有`待审核`或`审核未通过`新闻信息并进行分页
    filters = [News.status != 0]
    if key:
        filters.append(News.title.contains(key))
    try:
        pagination = News.query.filter(*filters). \
            order_by(News.create_time.desc()). \
            paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        news_li = pagination.items
        total_page = pagination.pages
        current_page = pagination.page
    except Exception as e:
        current_app.logger.error(e)
        abort(500)

    return render_template('admin/news_review.html',
                           news_li=news_li,
                           total_page=total_page,
                           current_page=current_page)


@admin_blu.route('/news/review/<int:news_id>', methods=['GET', 'POST'])
@admin_login_required
def news_review_detail(news_id):
    """后台管理获取审核新闻详情信息"""
    # 1. 根据新闻id获取新闻详情信息
    if request.method == 'GET':
        try:
            news = News.query.get(news_id)
            # 给news对象增加属性index_image，保存当前新闻的索引图片信息
            news.index_image = news.index_image_url
        except Exception as e:
            current_app.logger.error(e)
            abort(500)

        if not news:
            abort(404)

        return render_template('admin/news_review_detail.html',
                               news=news)
    else:
        # 执行审核操作
        # 1. 获取参数并进行参数校验
        req_dict = request.json
        if not req_dict:
            return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

        action = req_dict.get('action')

        if not action:
            return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

        if action not in ('accept', 'reject'):
            return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

        # 2. 根据`news_id`查询新闻信息
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='查询新闻信息失败')

        if not news:
            return jsonify(errno=RET.NODATA, errmsg='新闻信息不存在')

        # 3. 根据action执行不同的操作
        if action == 'accept':
            news.status = 0
        else:
            reason = req_dict.get('reason')
            if not reason:
                return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

            news.reason = reason
            news.status = -1

        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='操作失败')

        return jsonify(errno=RET.OK, errmsg='审核成功')


@admin_blu.route('/news/edit')
@admin_login_required
def news_edit():
    """后台管理新闻编辑页面"""
    # 1. 获取参数并进行校验
    page = request.args.get('p', 1)
    key = request.args.get('key')

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    # 2. 获取所有新闻信息
    filters = []

    if key:
        filters.append(News.title.contains(key))

    try:
        pagination = News.query.filter(*filters). \
            order_by(News.create_time.desc()). \
            paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)
        news_li = pagination.items
        total_page = pagination.pages
        current_page = pagination.page
    except Exception as e:
        current_app.logger.error(e)
        abort(500)

    return render_template('admin/news_edit.html',
                           news_li=news_li,
                           total_page=total_page,
                           current_page=current_page)


@admin_blu.route('/news/edit/<int:news_id>', methods=['GET', 'POST'])
@admin_login_required
def news_edit_detail(news_id):
    """后台管理新闻详情编辑页面"""
    # 1. 根据`news_id`查询新闻信息
    try:
        news = News.query.get(news_id)
        news.index_image_path = constants.QINIU_DOMIN_PREFIX + news.index_image_url
    except Exception as e:
        current_app.logger.error(e)
        abort(500)

    if not news:
        abort(404)

    # 2. 获取新闻分类信息
    if request.method == 'GET':
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            abort(500)

        return render_template('admin/news_edit_detail.html',
                               news=news,
                               categories=categories)
    else:
        # 执行编辑处理
        #　１．接收参数并进行参数校验
        title = request.form.get("title")
        digest = request.form.get("digest")
        content = request.form.get("content")
        index_image = request.files.get("index_image")
        category_id = request.form.get("category_id")

        if not all([title, digest, content, category_id]):
            return jsonify(errno=RET.PARAMERR, errmsg='参数不完整1')

        try:
            category_id = int(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

        # 2. 将索引图片上传至七牛云
        if index_image:
            try:
                key = storage(index_image.read())
            except Exception as e:
                current_app.logger.error(e)
                return jsonify(errno=RET.THIRDERR, errmsg='上传文件到七牛云失败')

        # 3. 设置新闻的信息
        news.title = title
        news.digest = digest
        news.content = content
        news.category_id = category_id
        if index_image:
            news.index_image_url = key

        # 4. 将修改信息添加进数据库
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='保存新闻信息失败')

        return jsonify(errno=RET.OK, errmsg='编辑成功')


@admin_blu.route('news/types')
@admin_login_required
def news_types():
    """后台管理新闻分类页面"""
    # 1. 获取`新闻分类`信息
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
        abort(500)

    # 去除`最新`分类
    categories.pop(0)

    return render_template('admin/news_type.html',
                           categories=categories)


@admin_blu.route('/news/types/edit', methods=['POST'])
@admin_login_required
def news_type_edit():
    """增加分类或编辑分类"""
    # 1. 接收参数并进行校验
    req_dict = request.json

    if not req_dict:
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

    category_id = req_dict.get('id')
    name = req_dict.get('name')

    if not name:
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

    if category_id:
        try:
            category_id = int(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='查询分类信息失败')

        if not category:
            return jsonify(errno=RET.NODATA, errmsg='分类信息不存在')

    # 2. 执行｀添加｀或｀编辑｀分类操作
    if category_id:
        # 编辑分类
        category.name = name
    else:
        # 添加分类
        category = Category()
        category.name = name

    try:
        db.session.add(category)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存分类信息失败')

    return jsonify(errno=RET.OK, errmsg='操作成功')


