$(document).ready(function () {
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
    var devices_id = $.map(devices, function (x) { return $(x).attr('data') });
    if (devices_id.length == 1) {
        var url = "/inventory/tag/devices/" + devices_id[0] + "/del/";
        window.location.href = url;
    } else {
        $("#unlinkTagAlertModal").click();
    }
}

function addTag() {
    var devices = $(".deviceSelect").filter(':checked');
    var devices_id = $.map(devices, function (x) { return $(x).attr('data') });
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
    var devices_id = $.map(devices, function (x) { return $(x).attr('data') }).join(",");
    $.map($(".devicesList"), function (x) {
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

    description = $.map(list_devices, function (x) { return x }).join(", ");
    $(".enumeration-devices").html(description);
}

function export_file(type_file) {
    var devices = $(".deviceSelect").filter(':checked');
    var devices_id = $.map(devices, function (x) { return $(x).attr('data-device-dhid') }).join(",");
    if (devices_id) {
        var url = "/inventory/export/" + type_file + "/?ids=" + devices_id;
        window.location.href = url;
    } else {
        $("#exportAlertModal").click();
    }
}

window.addEventListener("DOMContentLoaded", () => {
    var searchForm = document.getElementById("SearchForm")
    var inputSearch = document.querySelector("#SearchForm > input")
    var doSearch = true

    const Api = {
        /**
         * get lots id
         * @returns get lots
         */
        async get_lots() {
            var request = await this.doRequest(API_URLS.lots, "GET", null)
            if (request != undefined) return request.items
            throw request
        },

        /**
         * Get filtered devices info
         * @param {number[]} ids devices ids
         * @returns full detailed device list
         */
        async get_devices(id) {
            var request = await this.doRequest(API_URLS.devices + '?filter={"devicehub_id": ["' + id + '"]}', "GET", null)
            if (request != undefined) return request.items
            throw request
        },

        /**
         * 
         * @param {string} url URL to be requested
         * @param {String} type Action type
         * @param {String | Object} body body content
         * @returns {Object[]}
         */
        async doRequest(url, type, body) {
            var result;
            try {
                result = await $.ajax({
                    url: url,
                    type: type,
                    headers: {
                        "Authorization": API_URLS.Auth_Token
                    },
                    body: body
                });
                return result
            } catch (error) {
                console.error(error)
                throw error
            }
        }
    }



    searchForm.addEventListener("submit", (event) => {
        event.preventDefault();
    })

    let timeoutHandler = setTimeout(() => { }, 1)
    let dropdownList = document.getElementById("dropdown-search-list")
    let defaultEmptySearch = document.getElementById("dropdown-search-list").innerHTML


    inputSearch.addEventListener("input", (e) => {
        clearTimeout(timeoutHandler)
        let searchText = e.target.value
        if (searchText == '') {
            document.getElementById("dropdown-search-list").innerHTML = defaultEmptySearch;
            return
        }

        let resultCount = 0;
        function searchCompleted() {
            resultCount++;
            if (resultCount < 2 && document.getElementById("dropdown-search-list").children.length > 0) {
                setTimeout(() => {
                    document.getElementById("dropdown-search-list").innerHTML = `
                <li id="deviceSearchLoader" class="dropdown-item">
                <i class="bi bi-x-lg"></i>
                        <span style="margin-right: 10px">Nothing found</span>
                </li>`
                }, 100)
            }
        }
        
        timeoutHandler = setTimeout(async () => {
            dropdownList.innerHTML = `
                <li id="deviceSearchLoader" class="dropdown-item">
                    <i class="bi bi-laptop"></i>
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </li>
                <li id="lotSearchLoader" class="dropdown-item">
                    <i class="bi bi-folder2"></i>
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </li>`;


            try {
                Api.get_devices(searchText.toUpperCase()).then(devices => {
                    dropdownList.querySelector("#deviceSearchLoader").style = "display: none"

                    for (let i = 0; i < devices.length; i++) {
                        const device = devices[i];

                        // See: ereuse_devicehub/resources/device/models.py
                        var verboseName = `${device.type} ${device.manufacturer} ${device.model}`

                        const templateString = `
                        <li>
                            <a class="dropdown-item" href="${API_URLS.devices_detail.replace("ReplaceTEXT", device.devicehubID)}" style="display: flex; align-items: center;" href="#">
                                <i class="bi bi-laptop"></i>
                                <span style="margin-right: 10px">${verboseName}</span>
                                <span class="badge bg-secondary" style="margin-left: auto;">${device.devicehubID}</span>
                            </a>
                        </li>`;
                        dropdownList.innerHTML += templateString
                        if (i == 4) { // Limit to 4 resullts
                            break;
                        }
                    }

                    searchCompleted();
                })
            } catch (error) {
                dropdownList.innerHTML += `
                <li id="deviceSearchLoader" class="dropdown-item">
                <i class="bi bi-x"></i>
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Error searching devices</span>
                    </div>
                </li>`;
                console.log(error);
            }

            try {
                Api.get_lots().then(lots => {
                    dropdownList.querySelector("#lotSearchLoader").style = "display: none"
                    for (let i = 0; i < lots.length; i++) {
                        const lot = lots[i];
                        if (lot.name.toUpperCase().includes(searchText.toUpperCase())) {
                            const templateString = `
                            <li>
                                <a class="dropdown-item" href="${API_URLS.lots_detail.replace("ReplaceTEXT", lot.id)}" style="display: flex; align-items: center;" href="#">
                                    <i class="bi bi-folder2"></i>
                                    <span style="margin-right: 10px">${lot.name}</span>
                                </a>
                            </li>`;
                            dropdownList.innerHTML += templateString
                            if (i == 4) { // Limit to 4 resullts
                                break;
                            }
                        }
                    }
                    searchCompleted();
                })

            } catch (error) {
                dropdownList.innerHTML += `
                <li id="deviceSearchLoader" class="dropdown-item">
                <i class="bi bi-x"></i>
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Error searching lots</span>
                    </div>
                </li>`;
                console.log(error);
            }
        }, 1000)
    })


})