$(document).ready(function() {
   $(".deviceSelect").on("change", deviceSelect);
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
        $("#addingLotModal .btn-primary").removeClass('d-none');
        $("#addingLotModal .btn-primary").show();
        $("#removeLotModal .text-danger").hide();
        $("#removeLotModal .btn-primary").removeClass('d-none');
        $("#removeLotModal .btn-primary").show();
        $("#addingTagModal .text-danger").hide();
        $("#addingTagModal .btn-primary").removeClass('d-none');
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
    console.log(action);
}
