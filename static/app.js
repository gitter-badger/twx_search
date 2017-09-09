



var summaryTemplate = $('#summaryTemplate').html();
Mustache.parse(summaryTemplate);


var resultTemplate = $('#resultTemplate').html();
Mustache.parse(resultTemplate);

function reloadSummary(){
    $.get('/listApps',function(data){
        var json  = JSON.parse(data)
        console.log(json)
        var result = Mustache.render(summaryTemplate, { 'data': json })
        //console.log(result)
         $('#summary').html(result);
         $('.deleteBtn').click(deleteApp);
    })
}

function importApp(){
    var value = $('#importPath').val()
    $.get('/importApp',{twxpath : value},function(res){ console.log(res)})
}

function search(){
    var q = $('#q').val()
    $.get('/search',{'q' : q},function(data){
        var json  = JSON.parse(data)
        console.log(json)
        var result = Mustache.render(resultTemplate, { 'data': json })
        $('#result').html(result);
    })

}
function deleteApp(ev){
console.log('hjhjh')
    var value = $(ev.target).data('path')
    console.log(value)
    $.get('/deleteApp',{twxpath : value},function(res){ console.log(res)})
}

window.prevCounter=0;
function loadProcessStatus(){
    setInterval(function() {
     $.get('/inprogress',function(data){
         data = Number(data)
         if(data<window.prevCounter){
            reloadSummary()
         }
         window.prevCounter=data
         if(data==1){
            data = '1 file'
         }else{
            data = data+" files"
         }
         $('#counter').html(data);
    })
    }, 3000);
}
$(document).ready(function(){
    reloadSummary();
    loadProcessStatus();
    $('#reloadBtn').click(reloadSummary)
    $('#importBtn').click(importApp)
    $('#searchBtn').click(search)

})