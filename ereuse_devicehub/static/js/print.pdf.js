$(document).ready(function() {
    STORAGE_KEY = 'tag-spec-key';
    $("#printerType").on("change", change_size);
    change_size();
    load_size();
})

function qr_draw(url) {
    var qrcode = new QRCode($("#qrcode")[0], {
        text: url,
        width: 128,
        height: 128,
        colorDark : "#000000",
        colorLight : "#ffffff",
        correctLevel : QRCode.CorrectLevel.H
    });
}

function save_size() {
    var height = $("#height-tag").val();
    var width = $("#width-tag").val();
    var sizePreset = $("#printerType").val();
    var data = {"height": height, "width": width, "sizePreset": sizePreset};
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function load_size() {
    var data = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (data){
        $("#height-tag").val(data.height);
        $("#width-tag").val(data.width);
        $("#printerType").val(data.sizePreset);
    };
}

function reset_size() {
    localStorage.removeItem(STORAGE_KEY);
    $("#printerType").val('brotherSmall');
    change_size();
}

function change_size() {
    var sizePreset = $("#printerType").val();
    if (sizePreset == 'brotherSmall') {
        $("#height-tag").val(29);
        $("#width-tag").val(62);
    } else if (sizePreset == 'smallTagPrinter') {
        $("#height-tag").val(59);
        $("#width-tag").val(97);
    }
}

function printpdf() {
    var height = parseInt($("#height-tag").val());
    var width = parseInt($("#width-tag").val());
    var doc = new jsPDF('l', 'mm', [width, height]);
    //var doc = new jsPDF('l', 'mm', [62, 29]);
    doc.addHTML($("#print"), 2, 2);
    doc.save('Tags.pdf');
}
