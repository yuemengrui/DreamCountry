from flask import g, current_app, jsonify
from flask import request
from flask import session
from info.models import User, News
from info.utils.commons import login_user_data
from . import index_blu
from flask import render_template
from info import constants
from info.utils.response_code import RET


@index_blu.route('/news')
def get_news_list():
    """
    获取分类新闻信息
    1.接收参数(新闻分页id，页面，每页容量)并进行参数校验
    2.根据category_id查询分类新闻信息并分页
    3.遍历分类信息对象列表，将每个对象转化为字典数据
    4.返回应答
    :return:
    """
    # 1.接收参数(新闻分页id，页面，每页容量)并进行参数校验
    category_id = request.args.get('cid')
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', constants.HOME_PAGE_MAX_NEWS)

    if not category_id:
        return jsonify(errno=RET.PARAMERR, errmsg='缺少参数')

    try:
        category_id = int(category_id)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 2.根据category_id查询分类新闻信息并分页
    # filters = []
    filters = [News.status == 0]
    if category_id != 1:
        filters.append(News.category_id == category_id)

    try:
        pagination = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
        news_li = pagination.items
        total_page = pagination.pages
        current_page = pagination.page
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取分类新闻信息失败')

    # 3.遍历分类信息对象列表，将每个对象转化为字典数据
    news_dict_li = []
    for news in news_li:
        news_dict_li.append(news.to_basic_dict())

    # 4.返回应答
    resp = {
        "news_li": news_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }
    return jsonify(errno=RET.OK, errmsg='OK', **resp)


@index_blu.route('/favicon.ico')
def send_web_ico():
    return current_app.send_static_file('news/favicon.ico')


@index_blu.route('/')
@login_user_data
def index():
    # 从g变量中获取user
    user = g.user

    # 获取点击排行数据
    # 获取首页`点击排行`新闻信息
    rank_news_li = []
    try:
        from info.models import News
        rank_news_li = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS).all()
    except Exception as e:
        current_app.logger.error(e)

    # 获取首页`新闻分类`信息
    categories = []
    try:
        from info.models import Category
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)

    return render_template("news/index.html",
                           user=user,
                           rank_news_li=rank_news_li,
                           categories=categories)