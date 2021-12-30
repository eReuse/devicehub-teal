$(document) .ready(function() {
    $(".deviceSelect").on("change", deviceSelect);
//  $('#selectLot').selectpicker();
})

function deviceSelect() {
    var devices = $(".deviceSelect").filter(':checked');
    var devices_id = $.map(devices, function(x) { return $(x).attr('data')}).join(",");
    if (devices_id == "") {
        $("#addingLotModal .text-danger").show();
        $("#addingLotModal .btn-primary").hide();
    } else {
        $("#addingLotModal .text-danger").hide();
        $("#addingLotModal .btn-primary").removeClass('d-none');
        $("#addingLotModal .btn-primary").show();
    }
    $.map($(".devicesList"), function(x) {
        $(x).val(devices_id);
    });
}
