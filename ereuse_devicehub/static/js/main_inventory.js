$(document).ready(function() {
    var show_allocate_form = $("#allocateModal").data('show-action-form');
    var show_datawipe_form = $("#datawipeModal").data('show-action-form');
    var show_trade_form = $("#tradeLotModal").data('show-action-form');
    if (show_allocate_form != "None") {
        $("#allocateModal .btn-primary").show();
        newAllocate(show_allocate_form);
    } else if (show_datawipe_form != "None") {
        $("#datawipeModal .btn-primary").show();
        newDataWipe(show_datawipe_form);
    } else if (show_trade_form != "None") {
        $("#tradeLotModal .btn-primary").show();
        newTrade(show_trade_form);
    } else {
        $(".deviceSelect").on("change", deviceSelect);
    }
    // $('#selectLot').selectpicker();
})

function deviceSelect() {
    var devices_count = $(".deviceSelect").filter(':checked').length;
    get_device_list();
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

        $("#datawipeModal .pol").show();
        $("#datawipeModal .btn-primary").hide();
    } else {
        $("#addingLotModal .pol").hide();
        $("#addingLotModal .btn-primary").show();

        $("#removeLotModal .pol").hide();
        $("#removeLotModal .btn-primary").show();

        $("#actionModal .pol").hide();
        $("#actionModal .btn-primary").show();

        $("#allocateModal .pol").hide();
        $("#allocateModal .btn-primary").show();

        $("#datawipeModal .pol").hide();
        $("#datawipeModal .btn-primary").show();

        $("#addingTagModal .pol").hide();
        $("#addingTagModal .btn-primary").show();
    }
}

function removeLot() {
    var devices = $(".deviceSelect");
    if (devices.length > 0) {
        $("#btnRemoveLots .text-danger").show();
    } else {
        $("#btnRemoveLots .text-danger").hide();
    }
    $("#activeRemoveLotModal").click();
}

function removeTag() {
    var devices = $(".deviceSelect").filter(':checked');
    var devices_id = $.map(devices, function(x) { return $(x).attr('data')});
    if (devices_id.length == 1) {
        var url = "/inventory/tag/devices/"+devices_id[0]+"/del/";
        window.location.href = url;
    } else {
        $("#unlinkTagAlertModal").click();
    }
}

function addTag() {
    var devices = $(".deviceSelect").filter(':checked');
    var devices_id = $.map(devices, function(x) { return $(x).attr('data')});
    if (devices_id.length == 1) {
        $("#addingTagModal .pol").hide();
        $("#addingTagModal .btn-primary").show();
    } else {
        $("#addingTagModal .pol").show();
        $("#addingTagModal .btn-primary").hide();
    }

    $("#addTagAlertModal").click();
}

function newTrade(action) {
    var title = "Trade "
    var user_to = $("#user_to").data("email");
    var user_from = $("#user_from").data("email");
    if (action == 'user_from') {
        title = 'Trade Incoming';
        $("#user_to").attr('readonly', 'readonly');
        $("#user_from").prop('readonly', false);
        $("#user_from").val('');
        $("#user_to").val(user_to);
    } else if (action == 'user_to') {
        title = 'Trade Outgoing';
        $("#user_from").attr('readonly', 'readonly');
        $("#user_to").prop('readonly', false);
        $("#user_to").val('');
        $("#user_from").val(user_from);
    }
    $("#tradeLotModal #title-action").html(title);
    $("#activeTradeModal").click();
}

function newAction(action) {
    $("#actionModal #type").val(action);
    $("#actionModal #title-action").html(action);
    deviceSelect();
    $("#activeActionModal").click();
}

function newAllocate(action) {
    $("#allocateModal #type").val(action);
    $("#allocateModal #title-action").html(action);
    deviceSelect();
    $("#activeAllocateModal").click();
}

function newDataWipe(action) {
    $("#datawipeModal #type").val(action);
    $("#datawipeModal #title-action").html(action);
    deviceSelect();
    $("#activeDatawipeModal").click();
}

function get_device_list() {
    var devices = $(".deviceSelect").filter(':checked');

    /* Insert the correct count of devices in actions form */
    var devices_count = devices.length;
    $("#datawipeModal .devices-count").html(devices_count);
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

function export_file(type_file) {
    var devices = $(".deviceSelect").filter(':checked');
    var devices_id = $.map(devices, function(x) { return $(x).attr('data-device-dhid')}).join(",");
    if (devices_id){
        var url = "/inventory/export/"+type_file+"/?ids="+devices_id;
        window.location.href = url;
    } else {
        $("#exportAlertModal").click();
    }
}

function lot_devices_del() {
    $('#lot_devices_del').submit();
}

function lot_devices_add() {
    $('#lot_devices_add').submit();
}
