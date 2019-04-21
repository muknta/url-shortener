//var givenUrl = document.getElementById("given-url");
//var submitBtn = document.getElementById("submit-btn");
//var result = document.getElementById("result");
//submitBtn.addEventListener("click", function(e) {
//  var xhr = new XMLHttpRequest();
//  xhr.open('POST', 'shorten-url', true);
//  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
//  xhr.onload = function() {
//    if (xhr.status >= 200 && xhr.status < 400) {
//      var resp = xhr.responseText;
//      alert(JSON.parse(resp)["data"]);
//    } else {
//      alert("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaalert"); 
//    }
//  };
//  xhr.send(givenUrl.value);
//});
 



$(function() {
  $('#submit-btn').click(function() {
    if (isUrl($('#given-url').val())) {
      $.ajax({
        type: "POST",
        url: "/shorten-url/",
        data: {
          'url' : $('#given-url').val(),
          'csrfmiddlewaretoken' : $("input[name=csrfmiddlewaretoken]").val()
        },
        success: returnSuccess,
        failure: function() {
          alert("errMsg");
        },
        dataType: 'json'
      });
    } else {
      $('#result').text("Invalid url.");
    };
  });
});

function returnSuccess(data, textStatus, jqXHR) {
  if(data.url) {
    $('#result').text(data.url);
    $('#given-url').val("");
  } else {
    $('#result').text("Do not submit blank.");
  }
};

function isUrl(s) {
  var regexp = /(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/
  return regexp.test(s);
};

