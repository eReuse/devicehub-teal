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
    data['phid'] = $("#phidCheck").prop('checked');
    data['tags'] = $("#tagsCheck").prop('checked');
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
        $("#phidCheck").prop('checked', data.phid);
        $("#tagsCheck").prop('checked', data.tags);
        $("#serialNumberCheck").prop('checked', data.serial_number);
        $("#manufacturerCheck").prop('checked', data.manufacturer);
        $("#modelCheck").prop('checked', data.model);
        if (data.logo) {
            // $("#logoCheck").prop('checked', data.sid);
            previewLogo(data.logoImg);
            $("#logoCheck").prop('checked', data.logo);
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
    $("#phidCheck").prop('checked', true);
    $("#tagsCheck").prop('checked', false);
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

    if ($("#phidCheck").prop('checked')) {
        $(".phid").show();
    } else {
        $(".phid").hide();
    };

    if ($("#tagsCheck").prop('checked')) {
        $(".tags").show();
    } else {
        $(".tags").hide();
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
    var logo = '';
    var _rel = 1;
    if ($('#logoCheck').prop('checked')) {
        logo = $("#logo-preview img").attr("src");
        if (logo) {
            var _img = new Image();
            _img.src = logo;
            _rel = parseInt(_img.height)/parseInt(_img.width);
        }
    }
    var img_side = (width/2) - 2*border;
    var last_tag_code = '';

    var height_need = border*2;
    if (logo) {
        height_need += width*_rel + border;
    };
    if ($("#qrCheck").prop('checked')) {
        height_need += img_side;
    } else if ($("#dhidCheck").prop('checked')) {
        height_need += line;
    };
    if ($("#sidCheck").prop('checked')) {
        height_need += line;
    };
    if ($("#phidCheck").prop('checked')) {
        height_need += line;
    };
    if ($("#tagsCheck").prop('checked')) {
        height_need += line;
    };
    if ($("#serialNumberCheck").prop('checked')) {
        height_need += line;
    };
    if ($("#manufacturerCheck").prop('checked')) {
        height_need += line;
    };
    if ($("#modelCheck").prop('checked')) {
        height_need += line;
    };
    height = Math.max(height, height_need);

    if (width > height) {
        var pdf = new jsPDF('l', 'mm', [width, height]);
    } else {
        var pdf = new jsPDF('p', 'mm', [height, width]);
    };

    var hlogo = 0;
    $(".tag").map(function(x, y) {
        if (x != 0){
            pdf.addPage();
        };
        var hspace = border;
        var tag = $(y).text();
        last_tag_code = tag;
        if (logo) {
            var wlogo = (width - border*2);
            hlogo = wlogo*_rel;
            pdf.addImage(logo, 'PNG', border, hspace, wlogo, hlogo);
            hspace += hlogo + border;
        };
        if ($("#qrCheck").prop('checked')) {
            var imgData = $('#'+tag+' img').attr("src");
            pdf.addImage(imgData, 'PNG', border, hspace, img_side, img_side);
            hspace += img_side;
        } else {
            hspace += line;
        };

        if ($("#dhidCheck").prop('checked')) {
            pdf.setFontSize(15);
            if ($("#qrCheck").prop('checked')) {
                var h = hspace + border - img_side/2;
                var w = border*2 + img_side;
                pdf.text(String(tag), w, h);
            } else {
                pdf.text(String(tag), border, hspace);
            }
            hspace += line;
        };
        if ($("#sidCheck").prop('checked')) {
            var sn = $(y).data('sid');
            pdf.setFontSize(12);
            if (sn) {
                pdf.text(String(sn), border, hspace);
                hspace += line;
            }
        };
        if ($("#phidCheck").prop('checked')) {
            var sn = $(y).data('phid');
            pdf.setFontSize(12);
            if (sn) {
                pdf.text(String(sn), border, hspace);
                hspace += line;
            }
        };
        if ($("#tagsCheck").prop('checked')) {
            var sn = $(y).data('tags');
            pdf.setFontSize(12);
            if (sn) {
                pdf.text(String(sn), border, hspace);
                hspace += line;
            }
        };
        if ($("#serialNumberCheck").prop('checked')) {
            var sn = $(y).data('serial-number');
            pdf.setFontSize(12);
            pdf.text(String(sn), border, hspace);
            hspace += line;
        };
        if ($("#manufacturerCheck").prop('checked')) {
            var sn = $(y).data('manufacturer');
            pdf.setFontSize(12);
            pdf.text(String(sn), border, hspace);
            hspace += line;
        };
        if ($("#modelCheck").prop('checked')) {
            var sn = $(y).data('model');
            pdf.setFontSize(8);
            pdf.text(String(sn), border, hspace);
            hspace += line;
        };
    });

    pdf.save('Tag_'+last_tag_code+'.pdf');
}
