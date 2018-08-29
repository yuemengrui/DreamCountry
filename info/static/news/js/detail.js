function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

var currentCid = 1; // 当前分类 id
var cur_page = 1; // 当前页
var total_page = 1;  // 总页数
var data_querying = true;   // 是否正在向后台获取数据

$(function(){

    $('.menu li').click(function () {
        window.location.href='/'
        // var clickCid = $(this).attr('data-cid');
        // $('.menu li').each(function () {
        //     $(this).removeClass('active');
        // });
        // $(this).addClass('active');
        //
        // if (clickCid != currentCid) {
        //     // 记录当前分类id
        //     currentCid = clickCid;
        //
        //     // 重置分页参数
        //     cur_page = 1;
        //     total_page = 1;
        //     updateNewsData();
        // }
    });

    // 打开登录框
    $('.comment_form_logout').click(function () {
        $('.login_form_con').show();
    });

    // 收藏
    $(".collection").click(function () {
        // 获取收藏的`新闻id`
        var news_id = $(this).attr("data-news-id");
        var action = "do";

        // 组织参数
        var params = {
            "news_id": news_id,
            "action": action
        };

        // TODO 请求收藏新闻
        $.ajax({
            url:"/news/collect",
            type:"post",
            contentType:"application/json",
            data:JSON.stringify(params),
            headers:{
                "X-CSRFToken":getCookie("csrf_token")
            },
            success: function (resp) {
                if (resp.errno == "0"){
                    // 收藏新闻成功
                    // 隐藏收藏按钮
                    $(".collection").hide();
                    // 显示取消收藏按钮
                    $(".collected").show();
                }
                else {
                    // 收藏新闻失败
                    alert(resp.errmsg);
                }
            }
        })

       
    });

    // 取消收藏
    $(".collected").click(function () {
        // 获取收藏的`新闻id`
        var news_id = $(this).attr("data-news-id");
        var action = "undo";

        // 组织参数
        var params = {
            "news_id": news_id,
            "action": action
        };

        // TODO 请求取消收藏新闻
        $.ajax({
            url:"/news/collect",
            type:"post",
            contentType:"application/json",
            data:JSON.stringify(params),
            headers:{
                "X-CSRFToken": getCookie("csrf_token")
            },
            success: function (resp) {
                if (resp.errno == "0"){
                    // 取消收藏新闻成功
                    // 隐藏取消收藏按钮
                    $(".collected").hide();
                    // 显示收藏按钮
                    $(".collection").show();
                }
                else {
                    // 取消收藏新闻失败
                    alert(resp.errmsg);
                }
            }
        })


    });

    // 更新评论条数
    function updateCommentCount() {
        var length = $(".comment_list").length;
        $(".comment_count").html(length + "条评论");
        $(".comment").html(length);
    }

    // 评论提交
    $(".comment_form").submit(function (e) {
        // 组织表单默认提交行为
        e.preventDefault();

        // 获取参数
        var news_id = $(this).attr("data-news-id");
        var comment = $(".comment_input").val();

        // 组织参数
        var params = {
            "news_id": news_id,
            "content": comment
        };

        // TODO 请求对新闻`进行评论`
        $.ajax({
            url:"/news/comment",
            type:"post",
            data:JSON.stringify(params),
            contentType:"application/json",
            headers:{
                "X-CSRFToken": getCookie("csrf_token")
            },
            success: function (resp) {
                if (resp.errno == "0"){
                    // 新闻评论成功
                    var comment = resp.comment;
                    // 拼接内容
                    var comment_html = '';
                    comment_html += '<div class="comment_list">';
                    comment_html += '<div class="person_pic fl">';
                    if (comment.user.avatar_url){
                        comment_html += '<img src="' + comment.user.avatar_url + '" alt="用户图标">';
                    }
                    else {
                        comment_html += '<img src="/static/news/images/person01.png" alt="用户图标">';
                    }
                    comment_html += '</div>';
                    comment_html += '<div class="user_name fl">' + comment.user.nick_name + '</div>';
                    comment_html += '<div class="comment_text fl">';
                    comment_html += comment.content;
                    comment_html += '</div>';
                    comment_html += '<div class="comment_time fl">' + comment.create_time + '</div>';

                    comment_html += '<a href="javascript:;" class="comment_up fr" data-comment-id="' + comment.id + '" data-news-id="' + comment.news_id + '">赞</a>';
                    comment_html += '<a href="javascript:;" class="comment_reply fr">回复</a>';
                    comment_html += '<form class="reply_form fl" data-comment-id="' + comment.id + '" data-news-id="' + news_id + '">';
                    comment_html += '<textarea class="reply_input"></textarea>';
                    comment_html += '<input type="button" value="回复" class="reply_sub fr">';
                    comment_html += '<input type="reset" name="" value="取消" class="reply_cancel fr">';
                    comment_html += '</form>';
                    comment_html += '</div>';
                    // 拼接到内容的前面
                    $(".comment_list_con").prepend(comment_html);
                    // 让comment_sub失去焦点
                    $(".comment_sub").blur();
                    // 清空新闻评论输入框内容
                    $(".comment_input").val("");
                }
                else {
                    // 新闻评论失败
                    alert(resp.errmsg);
                }
            }
        })


    });

    $('.comment_list_con').delegate('a,input','click',function(){

        var sHandler = $(this).prop('class');

        if(sHandler.indexOf('comment_reply')>=0)
        {
            $(this).next().toggle();
        }

        if(sHandler.indexOf('reply_cancel')>=0)
        {
            $(this).parent().toggle();
        }

        if(sHandler.indexOf('comment_up')>=0)
        {
            var $this = $(this);
            // 默认点击时代表`点赞`
            var action = 'do';
            if(sHandler.indexOf('has_comment_up')>=0)
            {
                // 如果当前该评论已经是点赞状态，再次点击会进行到此代码块内，代表要取消点赞
                $this.removeClass('has_comment_up');
                // 如果已经点赞，设置为`取消点赞`
                action = 'undo';
            }else {
                $this.addClass('has_comment_up')
            }

            // 获取`评论id`
            var comment_id = $this.attr('data-comment-id');

            // 组织参数
            var params = {
                "comment_id": comment_id,
                "action": action
            };

            // TODO 请求`点赞`或`取消点赞`
            $.ajax({
                url:"/news/comment/like",
                type:"post",
                data: JSON.stringify(params),
                contentType:"application/json",
                headers:{
                    "X-CSRFToken": getCookie("csrf_token")
                },
                success: function (resp) {
                    if (resp.errno == "0"){
                        // 点赞或取消点赞成功
                        // 更新页面上评论点赞数
                        var like_count = $this.html();

                        if (isNaN(like_count)){
                            like_count = 0;
                        }

                        if (action == 'do'){
                            // 点赞数+1
                            like_count = parseInt(like_count) + 1;
                        }
                        else {
                            // 点赞数-1
                            like_count = parseInt(like_count) -1;
                        }
                        $this.html(like_count);
                    }
                    else if (resp.errno == "4101"){
                        // 用户未登录
                        $(".login_form_con").show();
                    }
                    else {
                        // 点赞或取消点赞失败
                        alert(resp.reemsg);
                    }
                }
            })

        }

        if(sHandler.indexOf('reply_sub')>=0)
        {
            alert('回复评论');
            // 获取参数
            var $this = $(this);
            var news_id = $this.parent().attr('data-news-id');
            var parent_id = $this.parent().attr('data-comment-id');
            var comment = $this.prev().val();

            if (!comment) {
                alert("请输入评论内容");
                return;
            }

            // 组织参数
            var params = {
                "news_id": news_id,
                "content": comment,
                "parent_id": parent_id
            };

            // TODO 请求`回复评论`
            $.ajax({
                url:"/news/comment",
                type:"post",
                data: JSON.stringify(params),
                contentType:"application/json",
                headers:{
                    "X-CSRFToken": getCookie("csrf_token")
                },
                success: function (resp) {
                    if (resp.errno == "0"){
                        // 回复评论成功
                        var comment = resp.comment;
                        // 拼接内容
                        var comment_html = "";
                        comment_html += '<div class="comment_list">';
                        comment_html += '<div class="person_pic fl">';
                        if (comment.user.avatar_url) {
                            comment_html += '<img src="' + comment.user.avatar_url + '" alt="用户图标">';
                        }
                        else {
                            comment_html += '<img src="/static/news/images/person01.png" alt="用户图标">';
                        }
                        comment_html += '</div>';
                        comment_html += '<div class="user_name fl">' + comment.user.nick_name + '</div>';
                        comment_html += '<div class="comment_text fl">';
                        comment_html += comment.content;
                        comment_html += '</div>';
                        comment_html += '<div class="reply_text_con fl">';
                        comment_html += '<div class="user_name2">' + comment.parent.user.nick_name + '</div>';
                        comment_html += '<div class="reply_text">';
                        comment_html += comment.parent.content;
                        comment_html += '</div>';
                        comment_html += '</div>';
                        comment_html += '<div class="comment_time fl">' + comment.create_time + '</div>';

                        comment_html += '<a href="javascript:;" class="comment_up fr" data-comment-id="' + comment.id + '" data-news-id="' + comment.news_id + '">赞</a>';
                        comment_html += '<a href="javascript:;" class="comment_reply fr">回复</a>';
                        comment_html += '<form class="reply_form fl" data-comment-id="' + comment.id + '" data-news-id="' + news_id + '">';
                        comment_html += '<textarea class="reply_input"></textarea>';
                        comment_html += '<input type="button" value="回复" class="reply_sub fr">';
                        comment_html += '<input type="reset" name="" value="取消" class="reply_cancel fr">';
                        comment_html += '</form>';

                        comment_html += '</div>';
                        $(".comment_list_con").prepend(comment_html);
                        // 清空输入框
                        $this.prev().val("");
                        // 关闭
                        $this.parent().hide();

                        // 更新评论数目
                        updateCommentCount();
                    }
                    else {
                        // 回复评论失败
                        alert(resp.errmsg);
                    }
                }
            })

        }
    });

    // 关注当前新闻作者
    $(".focus").click(function () {
        // 获取参数
        var user_id = $(this).attr("data-user-id");
        var action = "do";

        // 组织参数
        var params = {
            "user_id": user_id,
            "action": action
        };
        // 请求关注新闻作者
        $.ajax({
          url: "/user/follow",
        type: "post",
        data: JSON.stringify(params),
        contentType: "application/json",
        headers: {
            "X-CSRFToken": getCookie("csrf_token")
        },
        success: function (resp) {
            if (resp.errno == "0") {
                // `关注`成功
                // 隐藏`关注`按钮
                $(".focus").hide();
                // 显示`已关注`按钮
                $(".focused").show();
                // 页面新闻作者`被关注数量`+1
                var count = $(".follows b").html();
                $(".follows b").html(parseInt(count) + 1);
            }
            else if (resp.errno == "4101") {
                // 用户未登录
                $(".login_form_con").show();
            }
            else {
                // `取消关注`成功
                alert(resp.errmsg);
            }
        }
        })

    });

    // 取消关注当前新闻作者
    $(".focused").click(function () {
        // 获取参数
        var user_id = $(this).attr("data-user-id");
        var action = "undo";

        // 组织参数
        var params = {
            "user_id": user_id,
            "action": action
        };
        // TODO 请求关注新闻作者
        $.ajax({
            url: "/user/follow",
            type: "post",
            data: JSON.stringify(params),
            contentType: "application/json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            success: function (resp) {
                if (resp.errno == "0") {
                    // `取消关注`成功
                    // 显示`关注`按钮
                    $(".focus").show();
                    // 隐藏`已关注`按钮
                    $(".focused").hide();
                    // 页面新闻作者`被关注数量`-1
                    var count = $(".follows b").html();
                    $(".follows b").html(parseInt(count) - 1);
                }
                else if (resp.errno == "4101") {
                    // 用户未登录
                    $(".login_form_con").show();
                }
                else {
                    // `取消关注`成功
                    alert(resp.errmsg);
                }
            }
        })
    });
})

// 获取指定页码的`分类新闻信息`
function updateNewsData() {
    // 组织参数
    var params = {
        "cid": currentCid,
        "page": cur_page,
        "per_page": 50
    };

    // TODO 更新新闻数据
    $.ajax({
        url:"/news",
        type:"get",
        data:params,
        success: function (resp) {
            // 是个这是否正在向后端请求数据标志

            data_querying = false;

            if (resp.errno == "0"){
                // 获取`分类新闻信息`成功
                // 设置分页之后`总页数`
                total_page = resp.total_page;

                if (cur_page == 1){
                    // 首先清空页面原有的内容
                    $('.list_con').html("");
                }
                // 获取返回的新闻信息
                var news_li = resp.news_li;
                // 遍历news_li获取每个新闻的信息并显示在页面上
                for (var  i=0; i < news_li.length; i++){
                    // 获取每个新闻信息
                    var news = news_li[i];
                    // 拼接新闻显示内容
                    var content = '<li>';
                    content += '<a href="/news/' + news.id+'" class="news_pic fl"><img src="' + news.index_image_url + '?imageView2/1/w/170/h/170"></a>';
                    content += '<a href="/news/'+news.id+'" class="news_title fl">' + news.title + '</a>';
                    content += '<a href="/news/'+news.id+'" class="news_detail fl">' + news.digest + '</a>';
                    content += '<div class="author_info fl">';
                    content += '<div class="source fl">来源：' + news.source + '</div>';
                    content += '<div class="time fl">' + news.create_time + '</div>';
                    content += '</div>';
                    content += '</li>';

                    // 将新闻显示内容添加到首页上
                    $(".list_con").append(content);
                }
                // 设置页码加1
                cur_page += 1;
            }
            else {
                // 获取`分类新闻信息`失败
                alert(resp.errmsg);
            }
        }
    })


}
