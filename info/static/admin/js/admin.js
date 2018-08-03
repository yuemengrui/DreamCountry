function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(function () {
    $(".logout").click(function () {
        // 管理员退出登录
        $.ajax({
            url: "/admin/logout",
            type: "post",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            success: function (resp) {
                if (resp.errno == "0"){
                    // 退出登录成功，跳转后台管理登录页面
                    location.href = '/admin/login';
                }
            }
        })
    })
})
