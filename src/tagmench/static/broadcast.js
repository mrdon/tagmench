document.addEventListener('DOMContentLoaded', function() {
    var es = new EventSource('/sse');

    var tagTemplate = Handlebars.compile($('#tag-template').html());
    Handlebars.registerPartial("tag", tagTemplate);
    var badgeTemplate = Handlebars.compile($('#badge-template').html());
    Handlebars.registerPartial("badge", badgeTemplate);
    var messageTemplate = Handlebars.compile($('#message-template').html());

    var messages_dom = document.getElementById('messages');

    function init() {
        es = new EventSource('/sse');
        es.onmessage = function (event) {

            var data = JSON.parse(event.data);
            var message_dom = document.createElement('div');
            message_dom.setAttribute('class', 'row');
            message_dom.innerHTML = messageTemplate(data)
            messages_dom.appendChild(message_dom);
            if (is_guest) {
                $('button', $(message_dom)).attr("disabled", "disabled");
            }
        };

        var evtSourceErrorHandler = function(event){
            var txt;
            switch( event.target.readyState ){
                case EventSource.CONNECTING:
                    txt = 'Reconnecting...';
                    break;
                case EventSource.CLOSED:
                    txt = 'Reinitializing...';
                    es = init();
                    break;
            }
            console.log(txt);
        };
        es.onerror = evtSourceErrorHandler;
        return es
    }


    var evtSourceErrorHandler = function(event){
        var txt;
        switch( event.target.readyState ){
            case EventSource.CONNECTING:
                txt = 'Reconnecting...';
                break;
            case EventSource.CLOSED:
                txt = 'Reinitializing...';
                es = new EventSource("../sse.php");
                es.onerror = evtSourceErrorHandler;
                break;
        }
        console.log(txt);
    };


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
