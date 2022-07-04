$(document).ready(() => {
   $("#type").on("change", deviceInputs);
   $("#amount").on("change", amountInputs);
   deviceInputs();
   amountInputs();
})

function deviceInputs() {
    if ($("#type").val() == "ComputerMonitor") {
        $("#screen").show();
        $("#resolution").show();
        $("#imei").hide();
        $("#meid").hide();
    } else if (["Smartphone", "Cellphone", "Tablet"].includes($("#type").val())) {
        $("#screen").hide();
        $("#resolution").hide();
        $("#imei").show();
        $("#meid").show();
    } else {
        $("#screen").hide();
        $("#resolution").hide();
        $("#imei").hide();
        $("#meid").hide();
    };
    amountInputs();
}

function amountInputs() {
    if ($("#amount").val() > 1) {
        $("#Phid").hide();
        $("#Id_device_supplier").hide();
        $("#Serial_number").hide();
        $("#Sku").hide();
        $("#imei").hide();
        $("#meid").hide();
    } else {
        $("#Phid").show();
        $("#Id_device_supplier").show();
        $("#Serial_number").show();
        $("#Sku").show();
        deviceInputs();
    };
}
