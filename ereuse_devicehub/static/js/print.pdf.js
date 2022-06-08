$(document).ready(function() {
    STORAGE_KEY = 'tag-spec-key';
    $("#printerType").on("change", change_size);
    $(".form-check-input").on("change", change_check);
    change_size();
    load_settings();
    change_check();
    $("#imgInp").change(function(){
        readURL(this);
    });
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

function previewLogo(logo) {
    const img = "<img style='max-width: 150px' src='"+logo+"' />";
    $("#logo-preview").html(img);
    $(".label-logo-dev").html(img);
}

function readURL(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();

        reader.onload = function (e) {
            previewLogo(e.target.result);
            $("#logoCheck").prop('disabled', '');
        }

        reader.readAsDataURL(input.files[0]);
    }
}


function save_settings() {
    var logo = $('#logo-preview img').attr('src');
    var height = $("#height-tag").val();
    var width = $("#width-tag").val();
    var sizePreset = $("#printerType").val();
    var data = {"height": height, "width": width, "sizePreset": sizePreset, 'logoImg': ''};
    if (logo) {
        data['logoImg'] = logo;
    };
    data['logo'] = $("#logoCheck").prop('checked');
    data['dhid'] = $("#dhidCheck").prop('checked');
    data['sid'] = $("#sidCheck").prop('checked');
    data['qr'] = $("#qrCheck").prop('checked');
    data['serial_number'] = $("#serialNumberCheck").prop('checked');
    data['manufacturer'] = $("#manufacturerCheck").prop('checked');
    data['model'] = $("#modelCheck").prop('checked');
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function load_settings() {
    var data = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (data){
        $("#height-tag").val(data.height);
        $("#width-tag").val(data.width);
        $("#printerType").val(data.sizePreset);
        $("#qrCheck").prop('checked', data.qr);
        $("#dhidCheck").prop('checked', data.dhid);
        $("#sidCheck").prop('checked', data.sid);
        $("#serialNumberCheck").prop('checked', data.serial_number);
        $("#manufacturerCheck").prop('checked', data.manufacturer);
        $("#modelCheck").prop('checked', data.model);
        if (data.logo) {
            $("#logoCheck").prop('checked', data.sid);
            previewLogo(data.logoImg);
        } else {
            $("#logoCheck").prop('checked', false);
            $("#logoCheck").prop('disabled', 'disabled');
        }
    };
}

function reset_settings() {
    localStorage.removeItem(STORAGE_KEY);
    $("#printerType").val('brotherSmall');
    $("#qrCheck").prop('checked', true);
    $("#dhidCheck").prop('checked', true);
    $("#sidCheck").prop('checked', true);
    $("#serialNumberCheck").prop('checked', false);
    $("#logoCheck").prop('checked', false);
    $("#manufacturerCheck").prop('checked', false);
    $("#modelCheck").prop('checked', false);
    $('#logo-preview').html('');
    change_size();
    change_check();
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

function change_check() {
    if ($('#logo-preview img').attr('src')) {
        $("#logoCheck").prop('disabled', '');
    } else {
        $("#logoCheck").prop('checked', false);
        $("#logoCheck").prop('disabled', 'disabled');
    };

    if ($("#logoCheck").prop('checked') && $('#logo-preview img').attr('src')) {
        $(".label-logo").show();
    } else {
        $(".label-logo").hide();
    };

    if ($("#dhidCheck").prop('checked')) {
        $(".dhid").show();
    } else {
        $(".dhid").hide();
    };

    if ($("#sidCheck").prop('checked')) {
        $(".sid").show();
    } else {
        $(".sid").hide();
    };

    if ($("#serialNumberCheck").prop('checked')) {
        $(".serial_number").show();
    } else {
        $(".serial_number").hide();
    };

    if ($("#manufacturerCheck").prop('checked')) {
        $(".manufacturer").show();
    } else {
        $(".manufacturer").hide();
    };

    if ($("#modelCheck").prop('checked')) {
        $(".model").show();
    } else {
        $(".model").hide();
    };

    if ($("#qrCheck").prop('checked')) {
        $(".qr").show();
    } else {
        $(".qr").hide();
    };
}

function printpdf() {
    var border = 2;
    var line = 5;
    var height = parseInt($("#height-tag").val());
    var width = parseInt($("#width-tag").val());
    var img_side = Math.min(height, width) - 2*border;
    max_tag_side = (Math.max(height, width)/2) + border;
    if (max_tag_side < img_side) {
        max_tag_side = img_side + 2*border;
    };
    min_tag_side = (Math.min(height, width)/2) + border;
    var last_tag_code = '';

    if ($("#sidCheck").prop('checked')) {
        height += line;
    };
    if ($("#serialNumberCheck").prop('checked')) {
        height += line;
    };
    if ($("#manufacturerCheck").prop('checked')) {
        height += line;
    };
    if ($("#modelCheck").prop('checked')) {
        height += line;
    };

    var pdf = new jsPDF('l', 'mm', [width, height]);
    $(".tag").map(function(x, y) {
        if (x != 0){
            pdf.addPage();
        };
        var space = line + border;
        if ($("#qrCheck").prop('checked')) {
            space += img_side;
        }
        var tag = $(y).text();
        last_tag_code = tag;
        if ($("#qrCheck").prop('checked')) {
            var imgData = $('#'+tag+' img').attr("src");
            pdf.addImage(imgData, 'PNG', border, border, img_side, img_side);
        };

        if ($("#dhidCheck").prop('checked')) {
           if ($("#qrCheck").prop('checked')) {
               pdf.setFontSize(15);
               pdf.text(tag, max_tag_side, min_tag_side);
           } else {
               pdf.setFontSize(15);
               pdf.text(tag, border, space);
               space += line;
           }
        };
        if ($("#sidCheck").prop('checked')) {
            var sn = $(y).data('sid');
            pdf.setFontSize(15);
            pdf.text(sn, border, space);
            space += line;
        };
        if ($("#serialNumberCheck").prop('checked')) {
            var sn = $(y).data('serial-number');
            pdf.setFontSize(12);
            pdf.text(sn, border, space);
            space += line;
        };
        if ($("#manufacturerCheck").prop('checked')) {
            var sn = $(y).data('manufacturer');
            pdf.setFontSize(12);
            pdf.text(sn, border, space);
            space += line;
        };
        if ($("#modelCheck").prop('checked')) {
            var sn = $(y).data('model');
            pdf.setFontSize(8);
            pdf.text(sn, border, space);
            space += line;
        };
    });

    pdf.save('Tag_'+last_tag_code+'.pdf');
}
