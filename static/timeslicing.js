function parse() {
  var datestr = $("#date_input input").val();
  var logstr = $("#log_input textarea").val();
  try {
    // global variables
    year_str = datestr.substring(0, 4);
    month_str = datestr.substring(4, 6);
    day_str = datestr.substring(6, 8);

    var parsed = Date.parse(year_str + "-" + month_str + "-" + day_str);
    if (isNaN(parsed)) {
      throw new Error("非法日期");
    }
    var date = new Date(parsed);
  } catch (error) {
    mdui.snackbar({
      message: "日期解析失败：" + error.message,
      position: "right-top",
    });
    logs = undefined;
    return;
  }
  date_str = year_str + "-" + month_str + "-" + day_str;
  var log_lines = logstr.split("\n");
  logs = []; // global variable
  var next_day = false;
  var pre_time = 0;
  for (let line of log_lines) {
    try {
      line = line.trim();
      if (line == "") {
        continue;
      }
      var items = line.split(" ");
      console.log(items);
      if (items.length != 2 && items.length != 3) {
        throw new Error("对象长度不正确");
      }
      var time = Number(items[0]);
      if (isNaN(time)) {
        throw new Error("非法时间");
      }
      if (time < pre_time) {
        next_day = true;
      }
      pre_time = time;
      if (items.length == 2) {
        var affair1 = items[1];
        var affair2 = items[1];
      } else {
        var affair1 = items[1];
        var affair2 = items[2];
      }
      var line_time = new Date(Date.parse(date_str));
      line_time.setHours(next_day ? time + 24 : time);
      logs.push([line_time.valueOf(), affair1]);
      line_time.setMinutes(30);
      logs.push([line_time.valueOf(), affair2]);
    } catch (error) {
      mdui.snackbar({
        message: "日志解析失败：" + error.message,
        position: "right-top",
      });
      logs = undefined;
      return;
    }
  }
  var table_str = make_table(logs);
  $("#log_table").html(table_str);
  $("#log_table").removeClass("mdui-hidden");
  mdui.snackbar({
    message: "日志解析成功",
    position: "right-top",
  });
  mdui.mutation();
}

function make_table(logs) {
  if (logs.length == 0) {
    return "<table class='mdui-table'><thead><tr><th>无内容</th></tr></thead><tbody></tbody></table>";
  }
  var with_update_time = logs[0].length == 3;
  var table_str = `<table class='mdui-table'><thead><tr><th>#</th><th>Time</th><th>Affair</th>${
    with_update_time ? "<th>Update time</th>" : ""
  }</tr></thead><tbody>`;
  for (let i = 0; i < logs.length; i++) {
    table_str +=
      "<tr><td>" +
      (i + 1) +
      "</td><td>" +
      new Date(logs[i][0]).toLocaleString() +
      "</td><td>" +
      logs[i][1] +
      (with_update_time
        ? "</td><td>" + new Date(logs[i][2]).toLocaleString()
        : "") +
      "</td></tr>";
  }
  table_str += "</tbody></table>";
  return table_str;
}

function insert() {
  if (logs == undefined || logs == []) {
    mdui.snackbar({
      message: "日志为空或解析失败",
      position: "right-top",
    });
    return;
  }
  $.post(
    "/insert_post",
    { logs: JSON.stringify(logs) },
    function (data, status) {
      if (status == "success" && data.status == "success") {
        mdui.snackbar({
          message: "插入成功",
          position: "right-top",
        });
        deal_next_day();
      } else {
        mdui.snackbar({
          message: "插入失败\nstatus: " + status + "\nmsg: " + data.msg,
          position: "right-top",
        });
      }
    }
  );
}

function deal_next_day()
{
  logs = undefined;
  $("#log_table").addClass("mdui-hidden");

  var datestr = year_str + "-" + month_str + "-" + day_str;
  var date = new Date(Date.parse(date_str));
  date.setDate(date.getDate() + 1);

  $("#date_input input").val(
    date.toISOString().substring(0, 10).replace(/-/g, "")
  );
  $("#log_input textarea").val("");
  mdui.mutation();
}

function query()
{
	$.get("/query", function(data, status){
		if (status == "success" && data.status == "success") {
			mdui.snackbar({
				message: "查询成功",
				position: "right-top",
			});
			$("#log_table").html(make_table(data.logs));
			$("#log_table").removeClass("mdui-hidden");
			mdui.mutation();
		} else {
			mdui.snackbar({
				message: "查询失败\nstatus: " + status + "\nmsg: " + data.msg,
				position: "right-top",
			});
			$("#log_table").addClass("mdui-hidden");
		}
	});
}