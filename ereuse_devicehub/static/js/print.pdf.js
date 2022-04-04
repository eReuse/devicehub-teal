$(document).ready(function() {
    STORAGE_KEY = 'tag-spec-key';
    $("#printerType").on("change", change_size);
    change_size();
    load_size();
})

function qr_draw(url, id) {
    var qrcode = new QRCode($(id)[0], {
        text: url,
        width: 128,
        height: 128,
        colorDark : "#000000",
        colorLight : "#ffffff",
        correctLevel : QRCode.CorrectLevel.Q
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
    var border = 2;
    var height = parseInt($("#height-tag").val());
    var width = parseInt($("#width-tag").val());
    img_side = Math.min(height, width) - 2*border;
    max_tag_side = (Math.max(height, width)/2) + border;
    if (max_tag_side < img_side) {
        max_tag_side = img_side+ 2*border;
    };
    min_tag_side = (Math.min(height, width)/2) + border;
    var last_tag_code = '';

    var pdf = new jsPDF('l', 'mm', [width, height]);
    $(".tag").map(function(x, y) {
        if (x != 0){
            pdf.addPage();
            console.log(x)
        };
        var tag = $(y).text();
        last_tag_code = tag;
        var imgData = $('#'+tag+' img').attr("src");
        pdf.addImage(imgData, 'PNG', border, border, img_side, img_side);
        pdf.text(tag, max_tag_side, min_tag_side);
    });

    pdf.save('Tag_'+last_tag_code+'.pdf');
}
