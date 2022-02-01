$(document).ready(function() {
    var show_action_form = $("#allocateModal").data('show-action-form');
    if (show_action_form != "None") {
        $("#allocateModal .btn-primary").show();
        newAllocate(show_action_form);
    } else {
        $(".deviceSelect").on("change", deviceSelect);
    }
    // $('#selectLot').selectpicker();
})

function deviceSelect() {
    var devices = $(".deviceSelect").filter(':checked');
    var devices_id = $.map(devices, function(x) { return $(x).attr('data')}).join(",");
    if (devices_id == "") {
        $("#addingLotModal .text-danger").show();
        $("#addingLotModal .btn-primary").hide();

        $("#removeLotModal .text-danger").show();
        $("#removeLotModal .btn-primary").hide();

        $("#actionModal .text-danger").show();
        $("#actionModal .btn-primary").hide();
    } else {
        $("#addingLotModal .text-danger").hide();
        $("#addingLotModal .btn-primary").show();

        $("#removeLotModal .text-danger").hide();
        $("#removeLotModal .btn-primary").show();

        $("#actionModal .text-danger").hide();
        $("#actionModal .btn-primary").show();

        $("#allocateModal .text-danger").hide();
        $("#allocateModal .btn-primary").show();
    }
    $.map($(".devicesList"), function(x) {
        $(x).val(devices_id);
    });
}

function newAction(action) {
    $("#actionModal #type").val(action);
    $("#activeActionModal").click();
}

function newAllocate(action) {
    $("#allocateModal #type").val(action);
    $("#activeAllocateModal").click();
}
