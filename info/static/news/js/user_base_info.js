function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(function () {

    $(".base_info").submit(function (e) {
        e.preventDefault();

        var signature = $("#signature").val();
        var nick_name = $("#nick_name").val();
        var gender = $(".gender:checked").val();

        if (!nick_name) {
            alert('请输入昵称');
            return
        }
        if (!gender) {
            alert('请选择性别');
        }

        // 组织参数
        var params = {
            "signature": signature,
            "nick_name": nick_name,
            "gender": gender
        };
        
        // TODO 请求修改用户基本信息
          $.ajax({
              url: "/user/basic",
              type: "post",
              data: JSON.stringify(params),
              contentType: "application/json",
              headers: {
                  "X-CSRFToken": getCookie("csrf_token")
              },
              success: function (resp) {
                  if (resp.errno == "0") {
                      // 用户基本信息`修改`成功
                      // 更新父窗口内容
                      $('.user_center_name', parent.document).html(params['nick_name']);
                      $('#nick_name', parent.document).html(params['nick_name']);
                      alert(resp.errmsg);
                      $('.input_sub').blur()

                  }
                  else {
                      // 用户基本信息`修改`失败
                      alert(resp.errmsg);
                  }
              }
          })

    })
});