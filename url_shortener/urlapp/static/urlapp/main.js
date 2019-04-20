//var xhr = new XMLHttpRequest();
//xhr.open('POST', 'index', true);
//xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
//xhr.onload = function() {
//    if (xhr.status >= 200 && xhr.status < 400) {
//        var resp = xhr.responseText;
//    } else {
//         
//    }
//};
//xhr.send(data);

alert("ASdas");
console.log("DASSSSSSSSSSSSSSSSSSSSSSS)))");


var xhr = new XMLHttpRequest();
xhr.open('GET', '', true);
xhr.onload = function() {
  if (xhr.status >= 200 && xhr.status < 400) {
    var resp = xhr.responseText;
    alert(resp);
    alert("SDFSDFDSF");
  } else {

  }
};
xhr.send();
alert("GGGGGGGGGGGGGGGG");
