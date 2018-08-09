# -*- coding: UTF-8 -*-
from flask import abort
from flask import g, current_app, jsonify
from flask import render_template
from flask import request
from flask import session
from info.models import News, Comment
from info.modules.news import news_blu
from info.utils.commons import login_user_data, login_required
from info import db
from info import constants
from info.utils.response_code import RET


@news_blu.route('/<int:news_id>')
@login_user_data
def get_news_detail(news_id):
    """获取新闻详情信息"""
    # 从g变量中获取user
    user = g.user

    """获取`新闻详情`信息"""
    try:

        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    if not news:
        abort(404)

    # 新闻点击量+1
    news.clicks += 1

    try:

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)

    # 获取首页`点击排行`新闻信息
    rank_news_li = []
    try:

        rank_news_li = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS).all()
    except Exception as e:
        current_app.logger.error(e)

    # 判断用户`是否收藏`该新闻
    is_collected = False
    if user:
        if news in user.collection_news:
            is_collected = True

    """获取新闻评论信息"""
    comments_li = []
    try:
        comments_li = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)

    """判断用户是否登录"""
    is_followed = False
    like_comments = []
    if user:
        # 用户已登录，获取用户的点赞的评论信息
        like_comments = user.like_comments

        # 判断当前用户是否｀关注｀了新闻作者
        if news.user and (user in news.user.followers):
            is_followed = True

    return render_template('news/detail.html',
                           user=user,
                           news=news,
                           rank_news_li=rank_news_li,
                           is_collected=is_collected,
                           comments_li=comments_li,
                           like_comments=like_comments,
                           qiniu_domain=constants.QINIU_DOMIN_PREFIX,
                           is_followed=is_followed)


@news_blu.route('/collect', methods=['POST'])
@login_required
def news_collect():
    """新闻收藏或取消收藏"""
    # 1. 获取请求参数并进行参数校验
    req_dict = request.json
    if not req_dict:

        return jsonify(errno=RET.PARAMERR, ERRMSG='缺少参数')

    news_id = req_dict.get('news_id')
    action = req_dict.get('action')

    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

    # 如果action=='do',则收藏新闻
    # 如果action=='undo',则取消收藏新闻
    if action not in('do', 'undo'):
        return jsonify(errno=RET.PARAMERR, errmsg='参数有误')

    # 2. 根据news_id查询新闻信息
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询新闻信息失败')

    if not news:
        return jsonify(errno=RET.NODATA, errmsg='新闻信息不存在')

    # 2. 根据action执行相应的操作
    user = g.user
    if action == 'do':
        # 收藏新闻
        if news not in user.collection_news:
            user.collection_news.append(news)
    else:
        # 取消收藏新闻
        if news in user.collection_news:
            user.collection_news.remove(news)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='操作失败')

    # 3. 返回应答，操作成功
    return jsonify(errno=RET.OK, errmsg='操作成功')


@news_blu.route('/comment', methods=['POST'])
@login_required
def save_news_commit():
    """新闻评论"""
    # 1. 获取请求参数并进行参数校验
    req_dict = request.json
    if not req_dict:
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

    news_id = req_dict.get('news_id')
    content = req_dict.get('content')
    parent_id = req_dict.get('parent_id')

    if not all([news_id, content]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

    # 2. 根据news_id查询新闻信息
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询新闻信息失败')

    if not news:
        return jsonify(errno=RET.NODATA, errmsg='新闻信息不存在')

    # 3. 创建Comment对象并保存评论信息
    comment = Comment()
    comment.user_id = g.user.id
    comment.news_id = news_id
    comment.content = content
    if parent_id:
        comment.parent_id = parent_id

    # 新闻评论数目加一
    news.comments_count += 1

    # 4. 将评论信息添加进数据库
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存订单评论失败')

    # 5. 返回应答，评论成功
    return jsonify(errno=RET.OK, errmsg='评论成功', comment=comment.to_dict())


@news_blu.route('/comment/like', methods=['POST'])
@login_required
def set_comment_like():
    """评论点赞或取消点赞"""
    # 1. 获取参数并进行参数校验
    req_dict = request.json
    if not req_dict:
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

    comment_id = req_dict.get('comment_id')
    action = req_dict.get('action')

    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, reemsg='参数不完整')

    if action not in ('do', 'undo'):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 2. 根据comment_id获取评论信息
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询评论信息失败')

    if not comment:
        return jsonify(errno=RET.NODATA, errmsg='评论信息不存在')

    # 3. 根据action执行对应的操作
    user = g.user
    if action == "do":
        # 评论点赞
        if comment not in user.like_comments:
            user.like_comments.append(comment)
            comment.like_count += 1
    else:
        # 评论取消点赞
        if comment in user.like_comments:
            user.like_comments.remove(comment)
            comment.like_count -= 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='操作失败')

    # 4. 返回应答，操作成功
    return jsonify(errno=RET.OK, errmsg='操作成功')