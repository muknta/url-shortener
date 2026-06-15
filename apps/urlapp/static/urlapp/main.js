function copyToClipboard(text) {
    prompt("Copy to clipboard: Ctrl+C, Enter", text);
};


$(function() {
  $('#url-form').on('submit', function(event){
    event.preventDefault();
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
  } else {
    $('#result').text("Oops..some_error");
  }
};

function isUrl(value) {
  var regexp = /^(?:(?:(?:https?|ftp):)?\/\/)(?:\S+(?::\S*)?@)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:[/?#]\S*)?$/i;
  return regexp.test(value);
};

