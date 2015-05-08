$(function() {
  var moveLeft = 20;
  var moveDown = 10;

  $('div#trigger').hover(function(e) {
    $('div#pop-up').show()
      .css('top', e.pageY + moveDown)
      .css('left', e.pageX + moveLeft)
      .appendTo('body');
  }, function() {
    $('div#pop-up').hide();
  });

  $('div#trigger').mousemove(function(e) {
    $("div#pop-up").css('top', e.pageY + moveDown).css('left', e.pageX + moveLeft);
  });

});
