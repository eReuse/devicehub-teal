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
    var devices_count = $(".deviceSelect").filter(':checked').length;
    if (devices_count == 0) {
        $("#addingLotModal .pol").show();
        $("#addingLotModal .btn-primary").hide();

        $("#removeLotModal .pol").show();
        $("#removeLotModal .btn-primary").hide();

        $("#addingTagModal .pol").show();
        $("#addingTagModal .btn-primary").hide();

        $("#actionModal .pol").show();
        $("#actionModal .btn-primary").hide();

        $("#allocateModal .pol").show();
        $("#allocateModal .btn-primary").hide();
    } else {
        $("#addingLotModal .pol").hide();
        $("#addingLotModal .btn-primary").show();

        $("#removeLotModal .pol").hide();
        $("#removeLotModal .btn-primary").show();

        $("#actionModal .pol").hide();
        $("#actionModal .btn-primary").show();

        $("#allocateModal .pol").hide();
        $("#allocateModal .btn-primary").show();

        $("#addingTagModal .pol").hide();
    }
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
    get_device_list();
    deviceSelect();
    $("#activeActionModal").click();
}

function newAllocate(action) {
    $("#allocateModal #type").val(action);
    $("#allocateModal #title-action").html(action);
    get_device_list();
    deviceSelect();
    $("#activeAllocateModal").click();
}

function get_device_list() {
    var devices = $(".deviceSelect").filter(':checked');

    /* Insert the correct count of devices in actions form */
    var devices_count = devices.length;
    $("#allocateModal .devices-count").html(devices_count);
    $("#actionModal .devices-count").html(devices_count);

    /* Insert the correct value in the input devicesList */
    var devices_id = $.map(devices, function(x) { return $(x).attr('data')}).join(",");
    $.map($(".devicesList"), function(x) {
        $(x).val(devices_id);
    });

    /* Create a list of devices for human representation */
    var computer = {
        "Desktop": "<i class='bi bi-building'></i>",
        "Laptop": "<i class='bi bi-laptop'></i>",
    };
    list_devices = devices.map(function (x) {
        var typ = $(devices[x]).data("device-type");
        var manuf = $(devices[x]).data("device-manufacturer");
        var dhid = $(devices[x]).data("device-dhid");
        if (computer[typ]) {
            typ = computer[typ];
        };
        return typ + " " + manuf + " " + dhid;
    });

    description = $.map(list_devices, function(x) { return x }).join(", ");
    $(".enumeration-devices").html(description);
}
