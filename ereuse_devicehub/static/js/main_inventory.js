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
    };
    select_shift();
    // $('#selectLot').selectpicker();
    $("#filter").on("change", () => {
      $("#submit_filter").click();
    });
})

class TableController {
    static #tableRows = () => table.activeRows.length > 0 ? table.activeRows : [];

    static #tableRowsPage = () => table.pages[table.rows.dt.currentPage - 1];

    /**
     * @returns Selected inputs from device list
     */
    static getSelectedDevices() {
        if (this.#tableRows() == undefined) return [];
        return this.#tableRows()
            .filter(element => element.querySelector("input").checked)
            .map(element => element.querySelector("input"))
    }

    /**
     * @returns Selected inputs in current page from device list
     */
    static getAllSelectedDevicesInCurrentPage() {
        if (this.#tableRowsPage() == undefined) return [];
        return this.#tableRowsPage()
            .filter(element => element.querySelector("input").checked)
            .map(element => element.querySelector("input"))
    }

    /**
     * @returns All inputs from device list
     */
    static getAllDevices() {
        if (this.#tableRows() == undefined) return [];
        return this.#tableRows()
            .map(element => element.querySelector("input"))
    }

    /**
     * @returns All inputs from current page in device list
     */
    static getAllDevicesInCurrentPage() {
        if (this.#tableRowsPage() == undefined) return [];
        return this.#tableRowsPage()
            .map(element => element.querySelector("input"))
    }

    /**
     *
     * @param {HTMLElement} DOMElements
     * @returns Procesed input atributes to an Object class
     */
    static ProcessTR(DOMElements) {
        return DOMElements.map(element => {
            const info = {}
            info.checked = element.checked
            Object.values(element.attributes).forEach(attrib => { info[attrib.nodeName.replace(/-/g, "_")] = attrib.nodeValue })
            return info
        })
    }
}

/**
 * Select all functionality
 */

const selectorController = (action) => {
    const btnSelectAll = document.getElementById("SelectAllBTN");
    const alertInfoDevices = document.getElementById("select-devices-info");

    function softInit() {
        TableController.getAllDevices().forEach(item => {
            item.addEventListener("click", itemListCheckChanged);
        })

        // https://github.com/fiduswriter/Simple-DataTables/wiki/Events
        table.on("datatable.page", () => itemListCheckChanged());
        table.on("datatable.perpage", () => itemListCheckChanged());
        table.on("datatable.update", () => itemListCheckChanged());
    }

    if (action == "softInit") {
        softInit();
        itemListCheckChanged();
        return;
    }

    function itemListCheckChanged() {
        alertInfoDevices.innerHTML = `Selected devices: ${TableController.getSelectedDevices().length}
            ${TableController.getAllDevices().length != TableController.getSelectedDevices().length
                ? `<a href="#" class="ml-3">Select all devices (${TableController.getAllDevices().length})</a>`
                : "<a href=\"#\" class=\"ml-3\">Cancel selection</a>"
            }`;

        if (TableController.getSelectedDevices().length <= 0) {
            alertInfoDevices.classList.add("d-none")
        } else {
            alertInfoDevices.classList.remove("d-none");
        }

        if (TableController.getAllDevices().length == TableController.getSelectedDevices().length) {
            btnSelectAll.checked = true;
            btnSelectAll.indeterminate = false;
        } else if(TableController.getAllSelectedDevicesInCurrentPage().length > 0) {
            btnSelectAll.indeterminate = true;
        } else {
            btnSelectAll.checked = false;
            btnSelectAll.indeterminate = false;
        }

        if (TableController.getAllDevices().length == 0) {
            btnSelectAll.checked = false;
            btnSelectAll.disabled = true;
        } else {
            btnSelectAll.disabled = false;
        }

        get_device_list();
    }

    btnSelectAll.addEventListener("click", event => {
        const checkedState = event.target.checked;
        TableController.getAllDevicesInCurrentPage().forEach(ckeckbox => { ckeckbox.checked = checkedState });
        itemListCheckChanged()
    })

    alertInfoDevices.addEventListener("click", () => {
        const checkState = TableController.getAllDevices().length == TableController.getSelectedDevices().length
        TableController.getAllDevices().forEach(ckeckbox => { ckeckbox.checked = !checkState });
        itemListCheckChanged()
    })

    softInit();

    itemListCheckChanged();
}

window.addEventListener("DOMContentLoaded", () => selectorController());

function deviceSelect() {
    const devices_count = TableController.getSelectedDevices().length;
    get_device_list();
    if (devices_count == 0) {
        $("#addingLotModal .pol").show();
        $("#addingLotModal .btn-primary").hide();

        $("#removeLotModal .pol").show();
        $("#removeLotModal .btn-primary").hide();

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
    }
}

function removeLot() {
    const devices = TableController.getAllDevices();
    if (devices.length > 0) {
        $("#btnRemoveLots .text-danger").show();
    } else {
        $("#btnRemoveLots .text-danger").hide();
    }
    $("#activeRemoveLotModal").click();
}

function select_shift() {
    const chkboxes = $(".deviceSelect");
    let lastChecked = null;
    chkboxes.click(function(e) {
        if (!lastChecked) {
            lastChecked = this;
            return;
        }

        if (e.shiftKey) {
            const start = chkboxes.index(this);
            const end = chkboxes.index(lastChecked);

            chkboxes.slice(Math.min(start,end), Math.max(start,end)+ 1).prop("checked", lastChecked.checked);
        }

        lastChecked = this;
    });
    selectorController("softInit");
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
    const devices = TableController.getSelectedDevices();

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

    const list_devices = devices.map((x) => {
        let typ = $(x).data("device-type");
        const manuf = $(x).data("device-manufacturer");
        const dhid = $(x).data("device-dhid");
        if (computer[typ]) {
            typ = computer[typ];
        };
        return `${typ} ${manuf} ${dhid}`;
    });

    const description = $.map(list_devices, (x) => x).join(", ");
    $(".enumeration-devices").html(description);
}

function export_file(type_file) {
    const devices = TableController.getSelectedDevices();
    const devices_id = $.map(devices, (x) => $(x).attr("data-device-dhid")).join(",");
    if (devices_id) {
        const url = `/inventory/export/${type_file}/?ids=${devices_id}`;
        window.location.href = url;
    } else {
        $("#exportAlertModal").click();
    }
}

function export_actions_erasure(type_file) {
    const actions = TableController.getSelectedDevices();
    const actions_id = $.map(actions, (x) => $(x).attr("data-action-erasure")).join(",");
    if (actions_id) {
        const url = `/inventory/export/${type_file}/?ids=${actions_id}`;
        window.location.href = url;
    } else {
        $("#exportAlertModal").click();
    }
}

class lotsSearcher {
    static lots = [];

    static lotsSearchElement = null;
    
    static getListLots = () => {
        const lotsList = document.getElementById("LotsSelector")
        if (lotsList) {
                                                 // Apply filter to get only labels
            return Array.from(lotsList.children).filter(item => item.querySelector("label"));
        }
        return [];
    }

    static enable() {
        if (this.lotsSearchElement) this.lotsSearchElement.disabled = false;
    }

    static disable() {
        if (this.lotsSearchElement) this.lotsSearchElement.disabled = true;
    }

    /**
     * do search when lot change in the search input
     */
    static doSearch(inputSearch) {
        const lots = this.getListLots();
        for (let i = 0; i < lots.length; i++) {
            const lot = lots[i]
            if (lot.innerText.toLowerCase().includes(inputSearch.toLowerCase())) {
                lot.style.display = "";
            } else {
                lot.style.display = "none";
            }
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    lotsSearcher.lotsSearchElement = document.getElementById("lots-search");
    lotsSearcher.lotsSearchElement.addEventListener("input", (e) => { lotsSearcher.doSearch(e.target.value) })
})

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
         * @param {EventSource} ev event (Should be a checkbox type)
         * @param {Lot} lot lot id
         * @param {Device[]} selectedDevices device id
         */
        manage(event, lot, selectedDevices) {
            event.preventDefault();
            const lotID = lot.id;
            const srcElement = event.srcElement.parentElement.children[0]
            const checked = !srcElement.checked;
            const { indeterminate } = srcElement

            const found = this.list.filter(list => list.lot.id == lotID)[0];

            if (checked) {
                if (found && found.type == "Remove") {
                    const affectedDevices = found.devices.filter(dev => found.lot.devices.includes(dev.id))
                    if (affectedDevices.length > 0 && found.indeterminate == false) { // Remove action from list
                        actions.list = actions.list.filter(x => x.lot.id != found.lot.id)
                    } else {
                        found.type = "Add";
                    }
                } else {
                    this.list.push({ type: "Add", lot, devices: selectedDevices, indeterminate });
                }
            } else if (found && found.type == "Add") {
                const affectedDevices = found.devices.filter(dev => !found.lot.devices.includes(dev.id))
                if (affectedDevices.length > 0 && found.indeterminate == false) { // Remove action from list
                    actions.list = actions.list.filter(x => x.lot.id != found.lot.id)
                } else {
                    found.type = "Remove";
                }
            } else {
                this.list.push({ type: "Remove", lot, devices: selectedDevices, indeterminate });
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
            toast.classList = `alert alert-dismissible fade show ${isError ? "alert-danger" : "alert-success"}`;
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
                        const devicesIDs = action.devices.filter(dev => !action.lot.devices.includes(dev.id)).map(dev => dev.id)
                        await Api.devices_add(action.lot.id, devicesIDs);
                        this.notifyUser("Devices sucefully added to selected lot/s", "", false);
                    } catch (error) {
                        this.notifyUser("Failed to add devices to selected lot/s", error.responseJSON.message, true);
                    }
                } else if (action.type == "Remove") {
                    try {
                        const devicesIDs = action.devices.filter(dev => action.lot.devices.includes(dev.id)).map(dev => dev.id)
                        await Api.devices_remove(action.lot.id, devicesIDs);
                        this.notifyUser("Devices sucefully removed from selected lot/s", "", false);
                    } catch (error) {
                        this.notifyUser("Failed to remove devices from selected lot/s", error.responseJSON.message, true);
                    }
                }
                requestCount += 1
                if (requestCount == this.list.length) {
                    this.reRenderTable();
                    this.list = [];
                }
            })
            $("#confirmLotsModal").modal("hide"); // Hide dialog when click "Save changes"
            document.getElementById("dropDownLotsSelector").classList.remove("show");
        }

        /**
         * Re-render list in table
         */
        async reRenderTable() {
            const newRequest = await Api.doRequest(window.location)

            const tmpDiv = document.createElement("div")
            tmpDiv.innerHTML = newRequest


            const newTable = document.createElement("table")
            newTable.innerHTML = tmpDiv.querySelector("table").innerHTML
            newTable.classList = "table"

            const oldTable = document.querySelector(".dataTable-wrapper")
            oldTable.parentElement.replaceChild(newTable, oldTable)

            table = new simpleDatatables.DataTable(newTable, {perPage: 20})

            // // Restore state of checkbox
            const selectAllBTN = document.getElementById("SelectAllBTN");
            selectAllBTN.checked = false;
            selectAllBTN.indeterminate = false;

            // Re-init SelectorController
            selectorController("softInit");
        }
    }

    let eventClickActions;

    /**
     * Generates a list item with a correspondient checkbox state
     * @param {Object} lot Lot model server
     * @param {Device[]} selectedDevices list selected devices
     * @param {HTMLElement} elementTarget
     * @param {Action[]} actions
     */
    function templateLot(lot, selectedDevices, elementTarget, actions) {
        elementTarget.innerHTML = ""
        const { id, name, state } = lot;

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

        doc.children[0].addEventListener("mouseup", (ev) => actions.manage(ev, lot, selectedDevices));
        doc.children[1].addEventListener("mouseup", (ev) => actions.manage(ev, lot, selectedDevices));
        elementTarget.append(doc);
    }

    const listHTML = $("#LotsSelector")

    // Get selected devices
    const selectedDevicesID = TableController.ProcessTR(TableController.getSelectedDevices()).map(item => item.data)

    if (selectedDevicesID.length <= 0) {
        listHTML.html("<li style=\"color: red; text-align: center\">No devices selected</li>");
        return;
    }

    // Initialize Actions list, and set checkbox triggers
    const actions = new Actions();
    if (eventClickActions) {
        document.getElementById("ApplyDeviceLots").removeEventListener(eventClickActions);
    }

    eventClickActions = document.getElementById("ApplyDeviceLots").addEventListener("click", () => {
        const modal = $("#confirmLotsModal")
        modal.modal({ keyboard: false })

        let list_changes_html = "";
        //  {type: ["Remove" | "Add"], "LotID": string, "devices": number[]}
        actions.list.forEach(action => {
            let type;
            let devices;
            if (action.type == "Add") {
                type = "success";
                devices = action.devices.filter(dev => !action.lot.devices.includes(dev.id)) // Only show affected devices
            } else {
                type = "danger";
                devices = action.devices.filter(dev => action.lot.devices.includes(dev.id)) // Only show affected devices
            }
            list_changes_html += `
            <div class="card border-primary mb-3 w-100">
            <div class="card-header" title="${action.lotID}">${action.lot.name}</div>
            <div class="card-body pt-3">
              <p class="card-text">
                ${devices.map(item => {
                const name = `${item.type} ${item.manufacturer} ${item.model}`
                return `<span class="badge bg-${type}" title="${name}">${item.devicehubID}</span>`;
            }).join(" ")}
              </p>
            </div>
          </div>`;
        })

        modal.find(".modal-body").html(list_changes_html)

        const el = document.getElementById("SaveAllActions")
        const elClone = el.cloneNode(true);
        el.parentNode.replaceChild(elClone, el);
        elClone.addEventListener("click", () => actions.doActions())

        modal.modal("show")

        // actions.doActions();
    });
    document.getElementById("ApplyDeviceLots").classList.add("disabled");

    try {
        lotsSearcher.disable()
        listHTML.html("<li style=\"text-align: center\"><div class=\"spinner-border text-info\" style=\"margin: auto\" role=\"status\"></div></li>")
        const selectedDevices = await Api.get_devices(selectedDevicesID);
        let lots = await Api.get_lots();

        lots = lots.map(lot => {
            lot.devices = selectedDevices
                .filter(device => device.lots.filter(devicelot => devicelot.id == lot.id).length > 0)
                .map(device => parseInt(device.id));

            switch (lot.devices.length) {
                case 0:
                    lot.state = "false";
                    break;
                case selectedDevicesID.length:
                    lot.state = "true";
                    break;
                default:
                    lot.state = "indetermined";
                    break;
            }

            return lot;
        })

        listHTML.html("");
        const lot_temporary = lots.filter(lot => !lot.transfer && !lot.trade);
        appendMenu(lot_temporary, listHTML, templateLot, selectedDevices, actions, "Temporary");

        const lot_incoming = lots.filter(lot => lot.transfer && lot.transfer == "Incoming");
        appendMenu(lot_incoming, listHTML, templateLot, selectedDevices, actions, "Incoming");

        const lot_outgoing = lots.filter(lot => lot.transfer && lot.transfer == "Outgoing");
        appendMenu(lot_outgoing, listHTML, templateLot, selectedDevices, actions, "Outgoing");

        lotsSearcher.enable();
    } catch (error) {
        console.log(error);
        listHTML.html("<li style=\"color: red; text-align: center\">Error feching devices and lots<br>(see console for more details)</li>");
    }
}

function appendMenu(lots, listHTML, templateLot, selectedDevices, actions, title) {
    let lotsList = [];
    lotsList.push(lots.filter(lot => lot.state == "true").sort((a, b) => a.name.localeCompare(b.name)));
    lotsList.push(lots.filter(lot => lot.state == "indetermined").sort((a, b) => a.name.localeCompare(b.name)));
    lotsList.push(lots.filter(lot => lot.state == "false").sort((a, b) => a.name.localeCompare(b.name)));
    lotsList = lotsList.flat(); // flat array

    listHTML.append(`<li style="color: black; text-align: center">${  title  }<hr /></li>`);
    lotsList.forEach(lot => templateLot(lot, selectedDevices, listHTML, actions));
}
