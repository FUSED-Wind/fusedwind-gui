   // The treeview script ---------------------------------------------------------
   var tree = {{ assembly_structure|safe }}
   $('#assembly-tree').treeview({
           data: tree,
           enableLinks: true,
           showBorder: false,
           onNodeSelected: function(event, data){
               $('.comp-panels').hide();
               console.log(data)
               if ( $('.panel-'+data['text']).hasClass( 'hidden' ) ) $('.panel-'+data['text']).hide().removeClass('hidden');
               $('.panel-'+data['text']).toggle();
           }});
   

// The fileupload script -------------------------------------------------------
$('#fileupload').fileupload({
   dataType: 'json',
   singleFileUploads: false,
   forceIframeTransport: true,
   url: '/upload/',
   add: function (e, data) {
       var jqXHR = data.submit()
           .success(function (result, textStatus, jqXHR) {
               console.log('success-result',result);
               console.log('success-textStatus',textStatus);
               console.log('success-jqXHR',jqXHR);

               for ( var j = 0; j < result['files'].length; j++ ) {
                   content = result['files'][j].content
                   for (var key in content) {
                      if (content.hasOwnProperty(key)) {
                          var obj = content[key];
                          console.log(key,obj)
                          $('#'+key).val(function( index, value ) {
                               return obj;
                           });
                       }
                   }
               }
           });
       }
   });



// Alert script ---------------------------
function showalert(message,alerttype, delayms) {
   delayms = typeof delayms !== 'undefined' ?  delayms : 5000; // default parameters do not work in function() stmt

   $('#alert_placeholder').append('<div id="alertdiv" class="alert alert-' +
                                  alerttype +
                                  '" role="alert"><a class="close" data-dismiss="alert">×</a><span>' +
                                  message +
                                  '</span></div>')

       setTimeout(function() { // this will automatically close the alert and remove this if the users doesn't close it in 'delayms' ms

           $("#alertdiv").remove();
           $("#alertdiv").remove();


       }, delayms); //5000);
   }