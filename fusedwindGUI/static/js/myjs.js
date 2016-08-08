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




// Table expansion for bootstrap ------------------
function expandTable($detail, row) {
   $detail.html();
   if (row.type == 'Array') {
       buildArrayTable($detail.html('<p><b>Description:</b> ' + row.desc + '</p>' +
                               '<p><b>Units:</b> ' + row.units + '</p>' +
                               '<table data-show-export="true"></table>').find('table'), row);
   }
   else if (row.type == 'VarTree') {
       buildVTTable($detail.html('<p><b>Description:</b> ' + row.state.desc + '</p>' +
                               '<table data-show-export="true">' +
                                   '<thead>' +
                                   '<tr>' +
                                       '<th data-field="name">Name</th>'+
                                       '<th data-field="state">Value</th>'+
                                   '</tr>'+
                                   '</thead></table>').find('table'), row.state);

   }
   else {
       $detail.html('<p><b>Description:</b> ' + row.desc + ';<b> Value (Units):</b> ' + row.state + ' (' + row.units + ')</p>');
   }
}

// Builds variable trees for bootsrap table in outputs panel 
function buildVTTable($el, vtdata) { /* variable tree */ 

   var data = [], row = []
   for (var key in vtdata) {
       row = {};
       if (vtdata.hasOwnProperty(key)) {
           row['name'] = key ;
           row['state'] = vtdata[key].toPrecision(5);
       }
       data.push(row)
   }
   $el.bootstrapTable({data: data});
}

// Builds array tables for bootstrap table in outputs panel 
function buildArrayTable($el, rowdata) {
   var i, j, row, cell,
           columns = [],
           data = [];
   var row0 = rowdata.state[0]
   if (row0.length >= 2){
       for (i = 0; i < row0.length; i++) {
           columns.push({
               field: 'field' + i,
               title: 'Col' + i,
               sortable: true
           });

       }
       for(var i = 0; i < rowdata.state.length; i++) {
           var r = rowdata.state[i]
           row = {};
           for(var j = 0; j < r.length; j++) {
               row['field' + j] = r[j];

           }
           data.push(row);
       }
   }
   else {
           columns.push({
               field: 'field0',
               title: 'Col0',
               sortable: true
           });
           for(var i = 0; i < rowdata.state.length; i++) {
               var r = rowdata.state[i]
               row = {};
               row['field0'] = rowdata.state[i].toPrecision(5);
               data.push(row);
           }
   }

   $el.bootstrapTable({
       columns: columns,
       data: data,
       height: getHeight()
   });
}




// Case recorder scripts ------------------
// http://api.jquery.com/jquery.ajax/
function record_case() {
    console.log('calling record_case')
    $.ajax({
        url: 'analysis/record_case',
        type: 'POST',
        success: function(response) {
            console.log(response);
            showalert(response, 'success');
           },
        error: function(error) {
            console.log(error);
        }
    });
};

function clear_recorder() {
    console.log('calling clear_recorder')
    $.ajax({
        url: 'analysis/clear_recorder',
        type: 'POST',
        success: function(response) {
            console.log(response);

            showalert(response, 'success');
        },
        error: function(error) {
            console.log(error);
        }
    });
};

function compare_results() {
  console.log('calling compare_results')
  $.ajax({
      url: 'analysis/compare_results',
      type: 'POST',
      success: function(response) {
          console.log(response);
          showalert(response, 'success');
      },
      error: function(error) {
          console.log(error);
      }
  });
};

// Submit forms ------------------
submitForms = function(){
   document.forms["global-inputs-form"].submit();
}

$(document).ready( function() {
$('#alertdiv').delay(5000).remove();
});

