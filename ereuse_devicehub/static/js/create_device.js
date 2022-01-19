$(document).ready(function() {
   $("#type").on("change", deviceInputs);
   $("#screen").hide();
   $("#resolution").hide();
   $("#imei").hide();
   $("#meid").hide();
})

function deviceInputs() {
    if ($("#type").val() == 'Monitor') {
        $("#screen").show();
        $("#resolution").show();
        $("#imei").hide();
        $("#meid").hide();
    } else if (['Smartphone', 'Cellphone', 'Tablet'].includes($("#type").val())) {
        $("#screen").hide();
        $("#resolution").hide();
        $("#imei").show();
        $("#meid").show();
    } else {
        $("#screen").hide();
        $("#resolution").hide();
        $("#imei").hide();
        $("#meid").hide();
    }
}
