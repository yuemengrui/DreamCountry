from flask import abort
from flask import current_app
from flask import g, jsonify
from flask import render_template
from flask import request
from flask import session

from info import db
from info.modules.profile import profile_blu
from info.utils.commons import login_required, login_user_data
from info.utils.response_code import RET
from info.utils.image_storage import storage
from info import constants
from info.models import News, User
from info.models import Category
from info.constants import QINIU_DOMIN_PREFIX


@profile_blu.route('/')
@login_required
def get_user_profile():
    """获取用户信息"""
    user = g.user
    return render_template('news/user.html', user=user)


@profile_blu.route('/basic', methods=['GET', 'POST'])
@login_required
def user_basic_info():
    """用户的基本信息"""
    user = g.user
    if request.method == 'GET':
        return render_template('news/user_base_info.html', user=user)
    else:
        # 设置用户的基本信息
        # 1. 接收参数并进行参数校验
        req_dict = request.json
        if not req_dict:
            return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

        signature = req_dict.get('signature')
        nick_name = req_dict.get('nick_name')
        gender = req_dict.get('gender')

        if not all([signature, nick_name, gender]):
            return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

        if gender not in ('MAN', 'WOMAN'):
            return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

        # 2. 设置用户的基本信息
        user.nick_name = nick_name
        user.signature = signature
        user.gender = gender

        # 3. 将修改信息更新到数据库
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='保存用户基本信息失败')

        # 4. 设置session中保存的nick_name
        session['nick_name'] = nick_name
        return jsonify(errno=RET.OK, errmsg='修改成功')


@profile_blu.route('/avatar', methods=['GET', 'POST'])
@login_required
def user_avatar_info():
    """用户头像信息"""
    user = g.user
    if request.method == 'GET':
        return render_template("news/user_pic_info.html", user=user)
    else:
        # 上传用户个人头像信息
        # 1. 获取上传的用户头像文件对象
        file = request.files.get('avatar')
        if not file:
            return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

        # 2. 将用户个人头像图片上传至七牛云系统
        try:
            key = storage(file.read())
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg='上传用户头像失败')

        # 3. 保存用户的上传头像记录
        user.avatar_url = key
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='保存用户头像记录失败')

        # 4. 返回应答，上传头像成功

        avatar_url = constants.QINIU_DOMIN_PREFIX + key
        return jsonify(errno=RET.OK, errmsg='上传头像成功', avatar_url=avatar_url)


@profile_blu.route('/password', methods=['GET', 'POST'])
@login_required
def user_password_info():
    """用户密码修改"""
    if request.method == 'GET':
        return render_template("news/user_pass_info.html")
    else:
        # 修改用户个人密码
        user = g.user
        # 1. 获取参数并进行参数校验
        req_dict = request.json
        if not req_dict:
            return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

        old_password = req_dict.get('old_password')
        new_password = req_dict.get('new_password')

        if not all([old_password, new_password]):
            return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

        # 2. 校验用户的原始密码是否正确
        if not user.check_passowrd(old_password):
            return jsonify(errno=RET.PWDERR, errmsg='原密码错误')

        # 3. 设置用户新密码
        user.password = new_password

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='保存新密码失败')

        # 4. 返回应答，设置新密码成功
        return jsonify(errno=RET.OK, errmsg='设置新密码成功')


@profile_blu.route('/collection')
@login_required
def user_collection_news():
    """用户收藏新闻信息"""
    # 1. 接收参数并进行参数校验
    page = request.args.get('p', 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(ernno=RET.PARAMERR, errmsg='参数错误')

    # 2. 获取用户收藏的新闻信息并进行分页
    # 获取登录用户
    user = g.user
    try:
        pagination = user.collection_news.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        collection_news = pagination.items
        total_page = pagination.pages
        current_page = pagination.page
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户收藏新闻信息失败')

    return render_template('news/user_collection.html',
                           collection_news=collection_news,
                           total_page=total_page,
                           current_page=current_page)


@profile_blu.route('/release', methods=['GET', 'POST'])
@login_required
def user_news_release():
    """新闻发布"""
    if request.method == 'GET':
        # 获取新闻分类信息
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            abort(500)

        # 去除最新分类
        categories.pop(0)

        return render_template('news/user_news_release.html', categories=categories)
    else:
        # 新闻发布
        # 1. 接收参数并进行参数校验
        title = request.form.get('title')
        category_id = request.form.get('category_id')
        digest = request.form.get('digest')
        content = request.form.get('content')
        file = request.files.get('index_image')

        if not all([title, category_id, digest, content, file]):
            return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

        # 2. 将新闻的索引图片上传至七牛云
        try:
            key = storage(file.read())
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg='保存新闻索引图片失败')

        # 3. 创建News对象并保存发布新闻信息

        news = News()
        news.title = title
        news.source = '个人发布'
        news.category_id = category_id
        news.digest = digest
        news.content = content
        news.index_image_url = QINIU_DOMIN_PREFIX + key
        news.user_id = g.user.id
        news.status = 1

        # 4. 将新闻信息添加进数据库
        try:
            db.session.add(news)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='保存发布新闻信息失败')

        # 5. 返回应答，新闻发布成功
        return jsonify(errno=RET.OK, errmsg='新闻发布成功')


@profile_blu.route('/news')
@login_required
def user_news_list():
    """获取用户发布新闻信息"""
    # 1. 接收参数并进行参数校验
    page = request.args.get('p', 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 2. 获取用户收藏的新闻信息并进行分页
    # 获取登录用户
    user = g.user
    try:
        pagination = News.query.filter(News.user_id == user.id).paginate(page, constants.USER_COLLECTION_MAX_NEWS,
                                                                         False)
        release_news = pagination.items
        total_page = pagination.pages
        current_page = pagination.page
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户收藏新闻信息失败')

    return render_template('news/user_news_list.html',
                           release_news=release_news,
                           total_page=total_page,
                           current_page=current_page)


@profile_blu.route('/follow', methods=['POST'])
@login_required
def user_follow():
    """
        关注或取消关注用户:
        1. 接收参数(user_id, action)并进行参数验证
        2. 根据`user_id`查询被关注的用户信息(如果查不到，说明用户不存在)
        3. 根据action执行对应的操作
        4. 返回应答，关注或取消关注成功
        """
    # 1. 接收参数(user_id, action)并进行参数验证
    req_dict = request.json

    if not req_dict:
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

    user_id = req_dict.get('user_id')
    action = req_dict.get('action')

    try:
        user_id = int(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    if action not in ('do', 'undo'):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 2. 根据`user_id`查询被关注的用户信息(如果查不到，说明用户不存在)
    try:
        followed_user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户信息失败')

    if not followed_user:
        return jsonify(errno=RET.NODATA, errmsg='用户信息不存在')

    # 3. 根据action执行对应的操作
    user = g.user
    if action == 'do':
        # 执行`关注`用户操作
        if user not in followed_user.followers:
            followed_user.followers.append(user)
    else:
        # 执行`取消关注`用户操作
        if user in followed_user.followers:
            followed_user.followers.remove(user)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='操作失败')

    # 4. 返回应答，关注或取消关注成功
    return jsonify(errno=RET.OK, errmsg='操作成功')


@profile_blu.route('/follows')
@login_required
def user_follows():
    """用户关注的其他用户"""
    # 1. 接收参数并进行参数校验
    page = request.args.get('p', 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 2. 获取用户收藏的新闻信息并进行分页
    # 获取登录用户
    user = g.user
    try:
        pagination = user.followed.paginate(page, constants.USER_FOLLOWED_MAX_COUNT, False)
        follows = pagination.items
        total_page = pagination.pages
        current_page = pagination.page
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户收藏新闻信息失败')

    for followed_user in follows:
        followed_user.avatar_url_path = constants.QINIU_DOMIN_PREFIX + followed_user.avatar_url if followed_user.avatar_url else ''

    # 3. 使用模板
    return render_template('news/user_follow.html',
                           follows=follows,
                           total_page=total_page,
                           current_page=current_page)


@profile_blu.route('/<int:user_id>')
@login_required
def user_others(user_id):
    """其他用户主页"""
    user = g.user
    # 1. 根据`user_id`获取用户信息
    try:
        author = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        abort(500)

    if not author:
        abort(404)

    # 保存用户头像完整url地址
    author.avatar_url_path = constants.QINIU_DOMIN_PREFIX + author.avatar_url if author.avatar_url else ''

    # 2. 判断`author`是否被当前用户关注
    is_followed = False
    if author in user.followers:
        is_followed = True

    return render_template('news/other.html',
                           user=user,
                           author=author,
                           is_followed=is_followed)


@profile_blu.route('/<int:user_id>/news')
@login_user_data
def user_others_news(user_id):
    """
    获取其他用户发布的新闻信息:
    """
    # 1. 接收参数并进行参数校验
    page = request.args.get('p', 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 2. 根据`user_id`获取用户信息
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询用户信息失败')

    if not user:
        return jsonify(errno=RET.NODATA, errmsg='用户不存在')

    # 3. 查询用户发布的新闻信息
    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(page, constants.OTHER_NEWS_PAGE_MAX_COUNT, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取总页数
        total_page = paginate.pages
        # 获取当前页
        current_page = paginate.page
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    news_dict_li = []
    for news in news_li:
        news_dict_li.append(news.to_basic_dict())

    # 4. 返回应答
    return jsonify(errno=RET.OK, errmsg='OK',
                   news_li=news_dict_li,
                   total_page=total_page,
                   current_page=current_page)