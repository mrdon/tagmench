document.addEventListener('DOMContentLoaded', function() {
    var tagTemplate = Handlebars.compile($('#tag-template').html());
    Handlebars.registerPartial("tag", tagTemplate);
    var badgeTemplate = Handlebars.compile($('#badge-template').html());
    Handlebars.registerPartial("badge", badgeTemplate);
    var messageTemplate = Handlebars.compile($('#message-template').html());

    var messages_dom = document.getElementById('messages');

    function onMessage(event) {
        var data = JSON.parse(event.data);
        var message_dom = document.createElement('div');
        message_dom.setAttribute('class', 'row');
        message_dom.innerHTML = messageTemplate(data);
        messages_dom.prepend(message_dom);
        if (is_guest) {
            $('button', $(message_dom)).attr("disabled", "disabled");
        }
    }

    function isFunction(functionToCheck) {
      return functionToCheck && {}.toString.call(functionToCheck) === '[object Function]';
    }

    function debounce(func, wait) {
        var timeout;
        var waitFunc;

        return function() {
            if (isFunction(wait)) {
                waitFunc = wait;
            }
            else {
                waitFunc = function() { return wait };
            }

            var context = this, args = arguments;
            var later = function() {
                timeout = null;
                func.apply(context, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, waitFunc());
        };
    }

    // reconnectFrequencySeconds doubles every retry
    var reconnectFrequencySeconds = 1;
    var evtSource;

    var reconnectFunc = debounce(function() {
        setupEventSource();
        // Double every attempt to avoid overwhelming server
        reconnectFrequencySeconds *= 2;
        // Max out at ~1 minute as a compromise between user experience and server load
        if (reconnectFrequencySeconds >= 64) {
            reconnectFrequencySeconds = 64;
        }
    }, function() { return reconnectFrequencySeconds * 1000 });

    function setupEventSource() {
        evtSource = new EventSource("/sse");
        evtSource.onmessage = function(e) {
          onMessage(e);
        };
        evtSource.onopen = function(e) {
          // Reset reconnect frequency upon successful connection
          reconnectFrequencySeconds = 1;
        };
        evtSource.onerror = function(e) {
          evtSource.close();
          reconnectFunc();
        };
    }
    setupEventSource();

    if (is_guest) {
     return
    }
    $(messages_dom).on('click', '.btn-tag', function (e) {
        var $message = $(this).parent().parent();
        var username = $('.username', $message).text().trim();
        var $btn = $(this)
        var tag = $btn.text();
        $.ajax( "tag", {'method': 'POST', 'data': JSON.stringify({"username": username, "tag": tag}),
        "contentType" : 'application/json', "success":
        function( data ) {
            $('.author-tags', $message).append(badgeTemplate(tag));
            $btn.attr("disabled", "");
            console.log("Tagged")
        }});

        console.log('text: ' + username + " : " + $(this).text());
    });

    $(messages_dom).on('click', '.badge-tag', function (e) {
        var $message = $(this).parent().parent().parent()
        var username = $('.username', $message).text().trim();
        $badge = $(this);
        var tag = $badge.text();
        $.ajax( "untag", {'method': 'POST', 'data': JSON.stringify({"username": username, "tag": tag}),
        "contentType" : 'application/json', 'success':
        function( data ) {
            $('button.btn-tag:contains("' + tag + '")', $message).removeAttr('disabled');
            $badge.remove();
            console.log("Untagged")
        }});
        console.log('text: ' + username + " : " + $(this).text());
    });
});
