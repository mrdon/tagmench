document.addEventListener('DOMContentLoaded', function() {
    $("#btn-guest").click(function(e) {
        $('#guest').val("true");
        $("#login").submit();
    });

});