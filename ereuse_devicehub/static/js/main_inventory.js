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
        $("#addingTagModal .text-danger").show();
        $("#addingTagModal .btn-primary").hide();
    } else {
        $("#addingLotModal .text-danger").hide();
        $("#addingLotModal .btn-primary").show();

        $("#removeLotModal .text-danger").hide();
        $("#removeLotModal .btn-primary").show();

        $("#actionModal .text-danger").hide();
        $("#actionModal .btn-primary").show();

        $("#allocateModal .text-danger").hide();
        $("#allocateModal .btn-primary").show();

        $("#addingTagModal .text-danger").hide();
    }
    $.map($(".devicesList"), function(x) {
        $(x).val(devices_id);
    });
}

function removeTag() {
    var devices = $(".deviceSelect").filter(':checked');
    var devices_id = $.map(devices, function(x) { return $(x).attr('data')});
    console.log(devices_id);
    if (devices_id.length > 0) {
        var url = "/inventory/tag/devices/"+devices_id[0]+"/del/";
        window.location.href = url;
    }
}

function newAction(action) {
    $("#actionModal #type").val(action);
    $("#actionModal #title-action").html(action);
    $("#activeActionModal").click();
}

function newAllocate(action) {
    $("#allocateModal #type").val(action);
    $("#allocateModal #title-action").html(action);
    $("#activeAllocateModal").click();
}
