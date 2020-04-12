function getdatestring() {
    //https://stackoverflow.com/a/25835182
    var d = new Date();
    var curr_day = d.getDate();
    var curr_month = d.getMonth();
    var curr_year = d.getFullYear();
    var curr_hour = d.getHours();
    var curr_min = d.getMinutes();
    var curr_sec = d.getSeconds();
    curr_month++ ; // In js, first month is 0, not 1
    st = curr_year + "-" + curr_month + "-" + curr_day + "T" + curr_hour + ":" + curr_min + ":" + curr_sec;
    return st   
}
    
function msg(message) {
    if (message.slice(-1) != '\n') {message=message + "\n";}
    $("#console").val($("#console").val() + message);// + "\n");
    var con = $('#console');
    con.scrollTop(con[0].scrollHeight - con.height());
}


image = 0
imagecount = 0
$("input#url").val(window.location.hostname+":5000")
url = "http://"+$('input#url').val()+"/setdatetime/"+getdatestring();
    $.ajax({
      url: url,
      success: function(data, status, jqXHR){
        msg(data);
      },
      error: function(jqXHR, status, errorThrown){msg('Startup Error');},
    });
$('button#start').click(function(){
    msg('Starting...');
    url = "http://"+$('input#url').val()+"/start";
    $.ajax({
      url: url,
      success: function(data, status, jqXHR){
        msg(data);
      },
      error: function(jqXHR, status, errorThrown){msg('Start Error');},
    });
});
$('button#stop').click(function(){
    msg('Stop...');
    url = "http://"+$('input#url').val()+"/stop";
    $.ajax({
      url: url,
      success: function(data, status, jqXHR){
        msg(data);
      },
      error: function(jqXHR, status, errorThrown){msg('Stop Error');},
    });
});
$('button#imageup').click(function(){image=image+1;})
$('button#imagedown').click(function(){image=image-1;})
$('button#imageupx10').click(function(){image=image+10;})
$('button#imagedownx10').click(function(){image=image-10;})

setInterval(function(){ 

    url = "http://"+$('input#url').val()+"/getimagecount";
    $.ajax({
      url: url,
      success: function(data, status, jqXHR){

        newtic = data
        if (newtic!=imagecount)
        {

            imagecount = newtic
            msg("new image");
            if($("#latestimage").is(':checked')) {

                image = imagecount-1
                $('#download').click();
            }
        }
      }
      
      
      });
}, 1000);


setInterval(function(){ 
    if($("#contactimage").is(':checked')) {
        url = "http://"+$('input#url').val()+"/getcontact";
        $.ajax({
          url: url,
          success: function(data, status, jqXHR){
            if (data!=null) {
                console.log(data);
                $('#beep').get(0).play();  
                image = data['index']-1
                $('#download').click();
            }
          }
          
          
          });
    }
}, 1000);

setInterval(function(){ 
    url = "http://"+$('input#url').val()+"/getmessage";
    $.ajax({
      url: url,
      success: function(data, status, jqXHR){
        if (data.length>1) {
          msg(data)
        }
      }
      
      
      });
}, 1000);

function drawpixel(imdata,x,y,width,height) {
    pos = 4*(x+y*width)
    imdata[pos] = 255
    imdata[pos+1] = 255
    imdata[pos+2] = 0
}

function drawcrosshair(imdata,x,y,imscale,width,height) {
    x=Math.round(x/imscale)
    y=height-Math.round(y/imscale)
    for (xstep=x-10;xstep<x+10;xstep+=1) {
        drawpixel(imdata,xstep,y,width,height)
    }
    for (ystep=y-10;ystep<y+10;ystep+=1) {
        drawpixel(imdata,x,ystep,width,height)
    }

}

function convertJSONtoImageURL(data,drawcrosshairs) {
    img = data['photo']
    record = data['record']
    height = img.length
    width = img[0].length

    var canvas=document.createElement("canvas");
    var ctx=canvas.getContext("2d");

    // size the canvas to your desired image
    canvas.width=width;
    canvas.height=height;

    // get the imageData and pixel array from the canvas
    var imgData=ctx.getImageData(0,0,width,height);
    var imdata=imgData.data;

    // manipulate some pixel elements
    row = height-1;
    col = 0;
    scale = 255/$('input#maxval').val()

    for(var i=0;i<imdata.length;i+=4){
        c = img[row][col]*scale;
        if (c>255) {c=255;}
        imdata[i]=c;
        imdata[i+1] = c;
        imdata[i+2] = c;
        imdata[i+3]=255; // make this pixel opaque
        col = col + 1;
        if (col>=width) {
          col = 0;
          row = row - 1;
        }
    }
//    console.log(data)

//    drawcrosshair(imdata,20,60,20,width,height)
    if ('track' in data) {
        if ((data['track']!=null) && (data['track'].length>0)) {
            console.log(data['track']);
            for (var i=0;i<10;i++){
                msg([data['track'][i]['searchmax'],data['track'][i]['mean'],data['track'][i]['centremax']])
                drawcrosshair(imdata,data['track'][i]['x'],data['track'][i]['y'],20,width,height);
            }
            
        }
    }
    // put the modified pixels back on the canvas
    ctx.putImageData(imgData,0,0);
    return "url('"+canvas.toDataURL()+"')";
}


$('button.refreshimages').click(function(){refreshimages();});

$('input#maxval').bind('input',function() {refreshimages();});
function refreshimages(){
    //$('audio#beep')[0].play();
    $('span#index').text(image+1);//have to add one as python is zero indexed
    $('span#imagecount').text(imagecount);
    msg('Downloading...');
    
    
    url = "http://"+$('input#url').val()+"/getimage/"+image;
    $.getJSON(url, function(data) {$('#image').css("background-image",convertJSONtoImageURL(data)); }); 
    
    url = "http://"+$('input#url').val()+"/getimagecentre/"+image;
    $.getJSON(url, function(data) {$('#image_centre').css("background-image",convertJSONtoImageURL(data)); }); 
}

$('button#setinterval').click(function(){
    msg('Setting...');
    url = "http://"+$('input#url').val()+"/set/trigger/t/"+$('input#interval').val();
    $.ajax({
      url: url,
      success: function(data, status, jqXHR){
        msg('Set');
      },
      error: function(jqXHR, status, errorThrown){msg('Set Error');}
    });
});

function sendinstruction(instruction){
    msg(instruction);
    url = "http://"+$('input#url').val()+instruction;
    $.ajax({
      url: url,
      success: function(data, status, jqXHR){
        msg(data);
      },
      error: function(jqXHR, status, errorThrown){msg('Instruction Error');}
    });
}

$('input#console_input').keyup(function(e){
    if(e.keyCode == 13)
    {
        sendinstruction($('input#console_input').val());
    }
});
