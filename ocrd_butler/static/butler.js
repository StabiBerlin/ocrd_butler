$(document).ready(function() {

    console.log("foobar")
    console.log($("#new-task"))
    $("#new-task").click(() => {
        console.log($(".new-task-form"))
        $(".new-task-form").slideToggle({direction: 'right'});
    });

    $("#new-chain").click(() => {
        $(".new-chain-form").slideToggle({direction: 'right'});
    });

    let cp_select = $('.container.chains #processors');
    if (cp_select.length > 0) {
        cp_select.multiSelect({
            "keepOrder": true
        });
    }
});
