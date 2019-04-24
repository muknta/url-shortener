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
    $('#given-url').val("");
  } else {
    $('#result').text("Do not submit blank.");
  }
};

function isUrl(s) {
  var regexp = /(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/
  return regexp.test(s);
};

