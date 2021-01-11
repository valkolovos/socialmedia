$(function() {

  var markReadTimer;
  var messageTemplate;
  var signupUrl;

  window.initPage = function(welcomeName) {
    $('#user').text(welcomeName);
    $('#logged-in').show();
    $('#sign-out').show();
    bs_input_file();
    $('.new-connection').click(function(evt) {
      $('#newConnectionModal').modal('show');
    });
    $('#requestConnectionButton').click(function() {
      requestConnection(
        $('#connection-handle').val(),
        $('#connection-host').val()
      );
      $('#newConnectionModal').modal('hide');
    });
    window.getConnectionInfo();
    $('#messageSubmit').click(createMessage);
    window.notifInterval = window.setInterval(getConnectionInfo, 30000);
    $.get('static/message.mst', function(template) {
      messageTemplate = template;
    });
  }

  window.getMessages = function() {
    $.ajax('/get-messages', { headers: getHeaders() }).then(function(data){
      $.each(data, function(i, message) {
        var rendered = Mustache.render(messageTemplate, {message: message, connectionId: ''});
        $('#messages').append(rendered);
        bs_input_file();
        $('#comment-submit-'+message.id).click(function() {
          submitComment(message.id);
        });
      });
    });
  }

  window.createMessage = function() {
    var submitData = new FormData();
    submitData.append('message', $('#message').val());
    $.each($('#message-file')[0].files, function(i, file) {
      submitData.append('file-'+i, file);
    });
    $.ajax('/create-message', {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      method: 'POST',
      headers: getHeaders(),
      data: submitData,
      cache: false,
      contentType: false,
      processData: false,
      xhr: function() {
        var xhr = $.ajaxSettings.xhr();
        xhr.upload.onprogress = function (e) {
          if (e.lengthComputable) {
            console.log('Uploaded ' + (e.loaded / e.total));
          }
        }
        return xhr;
      },
      error: function(errorData, status, errorThrown) {
        console.log(status);
        console.log(errorThrown);
      }
    }).then(function(data){
      getMessages();
    });
  }

  window.submitComment = function(messageId) {
    var submitData = new FormData();
    submitData.append('comment', $('#comment-'+messageId).val());
    submitData.append('connectionId', $('#connectionId-'+messageId).val());
    $.each($('#comment-'+messageId+'-file')[0].files, function(i, file) {
      submitData.append('file-'+i, file);
    });
    $.ajax('/add-comment/'+messageId, {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      method: 'POST',
      headers: getHeaders(),
      data: submitData,
      cache: false,
      contentType: false,
      processData: false,
      xhr: function() {
        var xhr = $.ajaxSettings.xhr();
        xhr.upload.onprogress = function (e) {
          if (e.lengthComputable) {
            console.log('Uploaded ' + (e.loaded / e.total));
          }
        }
        return xhr;
      },
      error: function(errorData, status, errorThrown) {
        console.log(status);
        console.log(errorThrown);
      }
    }).then(function(data){
      //getMessages();
      console.log(data);
    });
  }

  window.confirmConnection = function(connectionId) {
    $.ajax('/manage-connection', {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      method: 'POST',
      headers: getHeaders(),
      data: JSON.stringify({
        "connection_id": connectionId,
        "action": "connect"
      }),
      contentType: 'application/json; charset=utf-8',
      dataType: 'json'
    }).then(function(data){
      getConnectionInfo();
      console.log(data);
    });
  }

  window.declineConnection = function(connectionId) {
    $.ajax('/manage-connection', {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      method: 'POST',
      headers: getHeaders(),
      data: JSON.stringify({
        "connection_id": connectionId,
        "action": 'decline'
      }),
      contentType: 'application/json; charset=utf-8',
      dataType: 'json'
    }).then(function(data){
      getConnectionInfo();
      console.log(data);
    });
  }

  window.requestConnection = function(handle, host) {
    $.ajax('/request-connection', {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      method: 'POST',
      headers: getHeaders(),
      data: {
        'handle': handle,
        'host': host
      }
    }).then(function(data){
      console.log(data);
    });
  }


  window.getUserIdToken = function() {
    return userIdToken;
  }

  window.getConnectionInfo = function() {
    $.ajax('/get-connection-info', {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      method: 'GET',
      headers: getHeaders()
    }).then(function(data){
      connectionNavHtml = "";
      $.each(data, function(i, conn) {
        connectionNavHtml += '<li class="nav-item"><span class="nav-link">' +
          '<a href="#" class="connection-link"' +
          'data-connectionid="' + conn.id + '">' +
          conn.display_name;
        if (conn.unread_message_count > 0) {
          connectionNavHtml += ' <span class="badge badge-primary">' +
            conn.unread_message_count+ '</span>';
        }
        connectionNavHtml += '</a>';
        if (conn.status == 'pending') {
          connectionNavHtml += ' <span class="badge badge-primary">' +
            '<span class="fa fa-user-plus confirm-connection" data-connectionid="' +
            conn.id + '"></span></span>' +
            ' <span class="badge badge-danger">' +
            '<span class="fa fa-user-times decline-connection" data-connectionid="' +
            conn.id + '"></span></span>';
        }
        connectionNavHtml += '</span></li>';
      });
      $('#connection-nav').html(connectionNavHtml);
      $('.connection-link').click(function(evt) {
        getConnectionMessages(
          evt.currentTarget.dataset.connectionid
        );
      });
      $('.confirm-connection').css('cursor', 'pointer');
      $('.confirm-connection').click(function(evt) {
        confirmConnection(evt.currentTarget.dataset.connectionid);
      });
      $('.decline-connection').css('cursor', 'pointer');
      $('.decline-connection').click(function(evt) {
        declineConnection(evt.currentTarget.dataset.connectionid);
      });
      console.log(data);
    });
  }

  window.getConnectionMessages = function(connectionId) {
    var url = '/get-connection-messages/' + connectionId;
    $.ajax(url, {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      method: 'GET',
      headers: getHeaders()
    }).then(function(data){
      console.log(data);

      // render messages
      $.each(data, function(i, message) {
        // if message is already displayed, don't re-render
        if (!$('#'+message.id).length) {
          var rendered = Mustache.render(messageTemplate, {message: message, connectionId: connectionId});
          $('#messages').append(rendered);
          $('.message-section').mouseenter(markRead).mouseleave(clearMarkReadTimer);
          bs_input_file();
          $('#comment-submit-'+message.id).click(function() {
            submitComment(message.id);
          });
        }
      });

    });
  }

  window.markRead = function(evt) {
    markReadTimer = window.setInterval(clearRead, 2000, evt);
  }

  window.clearRead = function(evt) {
    window.clearInterval(markReadTimer);
    url = '/mark-message-read/' + evt.target.id;
    $.ajax(url, {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      method: 'GET',
      headers: getHeaders(),
      error: function(errorData, status, errorThrown) {
        console.log(status);
        console.log(errorThrown);
      }
    }).then(function(data){
      connectionId = evt.target.dataset.connectionid;
      var badge = $('a[data-connectionid="'+connectionId+'"] .badge-primary');
      if (badge.length > 0) {
        badge = badge[0];
        var count = parseInt(badge.innerHTML);
        if (count > 1) {
          badge.innerHTML = count - 1;
        } else {
          badge.innerHTML = '';
        }
      }
    });
  }

  window.clearMarkReadTimer = function() {
    window.clearInterval(markReadTimer);
  }

  window.bs_input_file = function() {
    $(".input-file").before(
      function() {
        if ( ! $(this).prev().hasClass('input-ghost') ) {
          var element = $("<input type='file' name='"+this.dataset.type+"-file' id='" + this.dataset.type+"-file' class='input-ghost' style='visibility:hidden; height:0'>");
          element.attr("name",$(this).attr("name"));
          element.change(function(){
            element.next(element).find('input').val((element.val()).split('\\').pop());
          });
          $(this).find("button.btn-choose").click(function(){
            element.click();
          });
          $(this).find("button.btn-reset").click(function(){
            element.val(null);
            $(this).parents(".input-file").find('input').val('');
          });
          $(this).find('input').css("cursor","pointer");
          $(this).find('input').mousedown(function() {
            $(this).parents('.input-file').prev().click();
            return false;
          });
          return element;
        }
      }
    );
  }


});
