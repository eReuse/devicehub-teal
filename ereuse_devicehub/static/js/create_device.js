$(document).ready(() => {
   $("#type").on("change", deviceInputs2);
   $("#amount").on("change", deviceInputs2);
   deviceInputs2()
})

function deviceInputs2() {
   deviceInputs();
   amountInputs();
}

function deviceInputs() {
    if ($("#type").val() == "ComputerMonitor") {
        $("#screen").show();
        $("#resolution").show();
        $("#components2").hide();
        $("#imei").hide();
        $("#meid").hide();
        $("#data_storage_size").hide();
    } else if (["Smartphone", "Cellphone", "Tablet"].includes($("#type").val())) {
        $("#screen").hide();
        $("#resolution").hide();
        $("#components2").hide();
        $("#imei").show();
        $("#meid").show();
        $("#data_storage_size").show();
    } else if (["HardDrive", "SolidStateDrive"].includes($("#type").val())) {
        $("#screen").hide();
        $("#resolution").hide();
        $("#components2").hide();
        $("#imei").hide();
        $("#meid").hide();
        $("#data_storage_size").show();
    } else {
        $("#screen").hide();
        $("#resolution").hide();
        $("#imei").hide();
        $("#meid").hide();
        $("#data_storage_size").hide();
        $("#components2").show();
    };
}

function amountInputs() {
    if ($("#amount").val() > 1) {
        $("#Phid").hide();
        $("#Id_device_supplier").hide();
        $("#Id_device_internal").hide();
        $("#Serial_number").hide();
        $("#Part_number").hide();
        $("#Sku").hide();
        $("#imei").hide();
        $("#meid").hide();
        $("#data_storage_size").hide();
    } else {
        $("#Phid").show();
        $("#Id_device_supplier").show();
        $("#Id_device_internal").show();
        $("#Serial_number").show();
        $("#Part_number").show();
        $("#Sku").show();
    };
}
