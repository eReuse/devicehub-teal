$(document).ready(() => {
    const show_allocate_form = $("#allocateModal").data("show-action-form");
    const show_datawipe_form = $("#datawipeModal").data("show-action-form");
    const show_trade_form = $("#tradeLotModal").data("show-action-form");
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
    const devices_count = $(".deviceSelect").filter(":checked").length;
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
    const devices = $(".deviceSelect");
    if (devices.length > 0) {
        $("#btnRemoveLots .text-danger").show();
    } else {
        $("#btnRemoveLots .text-danger").hide();
    }
    $("#activeRemoveLotModal").click();
}

function removeTag() {
    const devices = $(".deviceSelect").filter(":checked");
    const devices_id = $.map(devices, (x) => $(x).attr("data"));
    if (devices_id.length == 1) {
        const url = `/inventory/tag/devices/${devices_id[0]}/del/`;
        window.location.href = url;
    } else {
        $("#unlinkTagAlertModal").click();
    }
}

function addTag() {
    const devices = $(".deviceSelect").filter(":checked");
    const devices_id = $.map(devices, (x) => $(x).attr("data"));
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
    let title = "Trade "
    const user_to = $("#user_to").data("email");
    const user_from = $("#user_from").data("email");
    if (action == "user_from") {
        title = "Trade Incoming";
        $("#user_to").attr("readonly", "readonly");
        $("#user_from").prop("readonly", false);
        $("#user_from").val("");
        $("#user_to").val(user_to);
    } else if (action == "user_to") {
        title = "Trade Outgoing";
        $("#user_from").attr("readonly", "readonly");
        $("#user_to").prop("readonly", false);
        $("#user_to").val("");
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
    const devices = $(".deviceSelect").filter(":checked");

    /* Insert the correct count of devices in actions form */
    const devices_count = devices.length;
    $("#datawipeModal .devices-count").html(devices_count);
    $("#allocateModal .devices-count").html(devices_count);
    $("#actionModal .devices-count").html(devices_count);

    /* Insert the correct value in the input devicesList */
    const devices_id = $.map(devices, (x) => $(x).attr("data")).join(",");
    $.map($(".devicesList"), (x) => {
        $(x).val(devices_id);
    });

    /* Create a list of devices for human representation */
    const computer = {
        "Desktop": "<i class='bi bi-building'></i>",
        "Laptop": "<i class='bi bi-laptop'></i>",
    };
    list_devices = devices.map((x) => {
        let typ = $(devices[x]).data("device-type");
        const manuf = $(devices[x]).data("device-manufacturer");
        const dhid = $(devices[x]).data("device-dhid");
        if (computer[typ]) {
            typ = computer[typ];
        };
        return `${typ  } ${  manuf  } ${  dhid}`;
    });

    description = $.map(list_devices, (x) => x).join(", ");
    $(".enumeration-devices").html(description);
}

function export_file(type_file) {
    const devices = $(".deviceSelect").filter(":checked");
    const devices_id = $.map(devices, (x) => $(x).attr("data-device-dhid")).join(",");
    if (devices_id){
        const url = `/inventory/export/${type_file}/?ids=${devices_id}`;
        window.location.href = url;
    } else {
        $("#exportAlertModal").click();
    }
}


/**
 * Reactive lots button
 */
async function processSelectedDevices() {
    class Actions {

        constructor() {
            this.list = []; // list of petitions of requests @item --> {type: ["Remove" | "Add"], "LotID": string, "devices": number[]}
        }

        /**
         * Manage the actions that will be performed when applying the changes
         * @param {*} ev event (Should be a checkbox type)
         * @param {string} lotID lot id
         * @param {number} deviceID device id
         */
        manage(event, lotID, deviceListID) {
            event.preventDefault();
            const srcElement = event.srcElement.parentElement.children[0]
            const {indeterminate} = srcElement;
            const checked = !srcElement.checked;

            const found = this.list.filter(list => list.lotID == lotID)[0];
            const foundIndex = found != undefined ? this.list.findLastIndex(x => x.lotID == found.lotID) : -1;

            if (checked) {
                if (found != undefined && found.type == "Remove") {
                    if (found.isFromIndeterminate == true) {
                        found.type = "Add";
                        this.list[foundIndex] = found;
                    } else {
                        this.list = this.list.filter(list => list.lotID != lotID);
                    }
                } else {
                    this.list.push({ type: "Add", lotID, devices: deviceListID, isFromIndeterminate: indeterminate });
                }
            } else if (found != undefined && found.type == "Add") {
                    if (found.isFromIndeterminate == true) {
                        found.type = "Remove";
                        this.list[foundIndex] = found;
                    } else {
                        this.list = this.list.filter(list => list.lotID != lotID);
                    }
                } else {
                    this.list.push({ type: "Remove", lotID, devices: deviceListID, isFromIndeterminate: indeterminate });
                }

            if (this.list.length > 0) {
                document.getElementById("ApplyDeviceLots").classList.remove("disabled");
            } else {
                document.getElementById("ApplyDeviceLots").classList.add("disabled");
            }
        }

        /**
         * Creates notification to give feedback to user
         * @param {string} title notification title
         * @param {string | null} toastText notification text
         * @param {boolean} isError defines if a toast is a error
         */
        notifyUser(title, toastText, isError) {
            const toast = document.createElement("div");
            toast.classList = `alert alert-dismissible fade show ${  isError ? "alert-danger" : "alert-success"}`;
            toast.attributes["data-autohide"] = !isError;
            toast.attributes.role = "alert";
            toast.style = "margin-left: auto; width: fit-content;";
            toast.innerHTML = `<strong>${title}</strong><button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
            if (toastText && toastText.length > 0) {
                toast.innerHTML += `<br>${toastText}`;
            }

            document.getElementById("NotificationsContainer").appendChild(toast);
            if (!isError) {
                setTimeout(() => toast.classList.remove("show"), 3000);
            }
            setTimeout(() => document.getElementById("NotificationsContainer").innerHTML == "", 3500);
        }

        /**
         * Get actions and execute call request to add or remove devices from lots
         */
        doActions() {
            let requestCount = 0; // This is for count all requested api count, to perform reRender of table device list
            this.list.forEach(async action => {
                if (action.type == "Add") {
                    try {
                        await Api.devices_add(action.lotID, action.devices);
                        this.notifyUser("Devices sucefully aded to selected lot/s", "", false);
                    } catch (error) {
                        this.notifyUser("Failed to add devices to selected lot/s", error.responseJSON.message, true);
                    }
                } else if (action.type == "Remove") {
                    try {
                        await Api.devices_remove(action.lotID, action.devices);
                        this.notifyUser("Devices sucefully removed from selected lot/s", "", false);
                    } catch (error) {
                        this.notifyUser("Fail to remove devices from selected lot/s", error.responseJSON.message, true);
                    }
                }
                requestCount += 1
                if (requestCount == this.list.length) {
                    this.reRenderTable();
                    this.list = [];
                }
            })
            document.getElementById("dropDownLotsSelector").classList.remove("show");
        }

        /**
         * Re-render list in table
         */
        async reRenderTable() {
            const newRequest = await Api.doRequest(window.location)

            const tmpDiv = document.createElement("div")
            tmpDiv.innerHTML = newRequest

            const oldTable = Array.from(document.querySelectorAll("table.table > tbody > tr .deviceSelect")).map(x => x.attributes["data-device-dhid"].value)
            const newTable = Array.from(tmpDiv.querySelectorAll("table.table > tbody > tr .deviceSelect")).map(x => x.attributes["data-device-dhid"].value)

            for (let i = 0; i < oldTable.length; i++) {
                if (!newTable.includes(oldTable[i])) {
                    // variable from device_list.html --> See: ereuse_devicehub\templates\inventory\device_list.html (Ln: 411)
                    table.rows().remove(i)
                }
            }
        }
    }

    let eventClickActions;

    /**
     * Generates a list item with a correspondient checkbox state
     * @param {String} lotID 
     * @param {String} lotName 
     * @param {Array<number>} selectedDevicesIDs
     * @param {HTMLElement} target
     */
    function templateLot(lot, elementTarget, actions) {
        elementTarget.innerHTML = ""
        const {id, name, state} = lot;

        const htmlTemplate = `<input class="form-check-input" type="checkbox" id="${id}" style="width: 20px; height: 20px; margin-right: 7px;">
            <label class="form-check-label" for="${id}">${name}</label>`;

        const doc = document.createElement("li");
        doc.innerHTML = htmlTemplate;

        switch (state) {
            case "true":
                doc.children[0].checked = true;
                break;
            case "false":
                doc.children[0].checked = false;
                break;
            case "indetermined":
                doc.children[0].indeterminate = true;
                break;
            default:
                console.warn("This shouldn't be happend: Lot without state: ", lot);
                break;
        }

        doc.children[0].addEventListener("mouseup", (ev) => actions.manage(ev, id, selectedDevicesIDs));
        doc.children[1].addEventListener("mouseup", (ev) => actions.manage(ev, id, selectedDevicesIDs));
        elementTarget.append(doc);
    }

    const listHTML = $("#LotsSelector")

    // Get selected devices
    // const selectedDevicesIDs = $.map($(".deviceSelect").filter(":checked"), (x) => parseInt($(x).attr("data")));

    
    const selectedDevices = table.rows().dt.activeRows.filter(item => item.childNodes[0].children[0].checked).map(item => {
        const child = item.childNodes[0].children[0]
        const info = {}
        Object.values(child.attributes).forEach(attrib => { info[attrib.nodeName] = attrib.nodeValue})
        return info
    })

    if (selectedDevices.length <= 0) {
        listHTML.html("<li style=\"color: red; text-align: center\">No devices selected</li>");
        return;
    }

    // Initialize Actions list, and set checkbox triggers
    const actions = new Actions();
    if (eventClickActions) {
        document.getElementById("ApplyDeviceLots").removeEventListener(eventClickActions);
    }
    eventClickActions = document.getElementById("ApplyDeviceLots").addEventListener("click", () => actions.doActions());
    document.getElementById("ApplyDeviceLots").classList.add("disabled");

    try {
        listHTML.html("<li style=\"text-align: center\"><div class=\"spinner-border text-info\" style=\"margin: auto\" role=\"status\"></div></li>")
        const devices = await Api.get_devices(selectedDevices.map(dev => dev.data));
        let lots = await Api.get_lots();

        lots = lots.map(lot => {
            lot.devices = devices
                .filter(device => device.lots.filter(devicelot => devicelot.id == lot.id).length > 0)
                .map(device => parseInt(device.id));

             switch (lot.devices.length) {
                case 0:
                    lot.state = "false";
                    break;
                case selectedDevices.length:
                    lot.state = "true";
                    break;
                default:
                    lot.state = "indetermined";
                    break;
            }

            return lot;
        })


        let lotsList = [];
        lotsList.push(lots.filter(lot => lot.state == "true").sort((a,b) => a.name.localeCompare(b.name)));
        lotsList.push(lots.filter(lot => lot.state == "indetermined").sort((a,b) => a.name.localeCompare(b.name)));
        lotsList.push(lots.filter(lot => lot.state == "false").sort((a,b) => a.name.localeCompare(b.name)));
        lotsList = lotsList.flat(); // flat array

        listHTML.html("");
        lotsList.forEach(lot => templateLot(lot, listHTML, actions));
    } catch (error) {
        console.log(error);
        listHTML.html("<li style=\"color: red; text-align: center\">Error feching devices and lots<br>(see console for more details)</li>");
    }
}
