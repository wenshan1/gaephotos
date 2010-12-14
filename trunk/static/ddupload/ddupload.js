var ddupload = ddupload || function(){};  

var default_settings = {
enterbackcolor:"#CDEB8B",
filetypes:"jpg,png,gif,jpeg,tiff,ico,bmp,jpe,JPG,PNG,GIF,JPEG,TIFF,ICO,BMP,JPE",
filelimit: 8*1024*1024,
};

ddupload.setup = function (container/*Dom Element*/, settings) {
	
        savedBackColor = container.style.backgroundColor;
        
        enterbackcolor = settings.enterbackcolor || default_settings.enterbackcolor;
        ddupload.filetypes = settings.filetypes || default_settings.filetypes;
        ddupload.filelimit = settings.filelimit || default_settings.filelimit;
        
        ddupload.posturl = settings.posturl;
        ddupload.postdata_handler = settings.postdata_handler;
        ddupload.loadedhandler = settings.loadedhandler;
        ddupload.progresshandler = settings.progresshandler;
        ddupload.onupload_success_handler = settings.onupload_success_handler;
        ddupload.onupload_failed_handler = settings.onupload_failed_handler;
                
        container.addEventListener("dragenter", function(event){
			event.stopPropagation();event.preventDefault();
			container.style.backgroundColor = enterbackcolor;
		}, false);
        container.addEventListener("dragover", function(event){
			event.stopPropagation();event.preventDefault();
			container.style.backgroundColor = enterbackcolor;
		}, false);
        container.addEventListener("dragleave", function(event){
			event.stopPropagation();event.preventDefault();
			container.style.backgroundColor = savedBackColor;
		}, false);
        container.addEventListener("drop", function(event){
			event.stopPropagation();event.preventDefault();
			container.style.backgroundColor = savedBackColor;
			ddupload.processdroppedfile(event, container);
		}, false);
};

ddupload.processdroppedfile = function (event, container) {
    var files = event.dataTransfer.files;
       
    for (var i = 0; i < files.length; i++) { 
        if(files[i].size < ddupload.filelimit) {
           var  file = files[i];
                         
            /* check file ext */
            filename = file.name.split('.');
            ext = filename[filename.length-1];

            if ( ddupload.filetypes.indexOf(ext) >= 0 )
            {
                if(ddupload.loadedhandler) {
                	localreader = new FileReader();
                    localreader.file = file;
                    localreader.onload = function(evt){ 
                        ddupload.loadedhandler(evt, container);
                        
                        uploadreader = new FileReader();
                        uploadreader.file = evt.target.file;
                        uploadreader.onload = function(event){ 
                            ddupload.processXHR(event.target.file, event.target.result, container);
                        };
                        uploadreader.readAsBinaryString(evt.target.file);
                    };
                    localreader.readAsDataURL(file);
                }
                else
                {
                    uploadreader = new FileReader();
                    uploadreader.file = file;
                    uploadreader.onload = function(evt){ 
                        ddupload.processXHR(evt.target.file, evt.target.result, container);
                    };
                    uploadreader.readAsBinaryString(file);
                }
            }
            else
            {
                alert("unsupported file type for file: "+file.name);
            }
        } 
        else {
            alert("file size exceed!");
        } /*end if*/
    } /*end for*/
};

ddupload.on_XHR_state_change_handler = function(xhr, evt, container) {
    if (xhr.readyState == 4) {
        if(xhr.status == 200) {
            ddupload.onupload_success_handler(xhr, evt, container);
        } else {
        	ddupload.onupload_failed_handler(xhr, evt, container);
        }  
    }
};

ddupload.processXHR = function (file, bin, container) {
    var xhr = new XMLHttpRequest(),
        xhrupload = xhr.upload;
    
    if (ddupload.progresshandler)
    {
        xhrupload.addEventListener("progress", function(event) {
            if (event.lengthComputable) {
                var percentage = Math.round((event.loaded * 100) / event.total);
                ddupload.progresshandler(file, percentage, container)
            }
        }, false);
    }
    
    xhrupload.addEventListener("error", ddupload.upload_error, false);
    
    xhr.onreadystatechange = function (evt) {
        evt.file = file;
        ddupload.on_XHR_state_change_handler(xhr, evt, container);
    };
    
    var postdata = ddupload.postdata_handler(file, container); 

    xhr.open("POST", ddupload.posturl);
    xhr.overrideMimeType('text/plain; charset=x-user-defined-binary'); 
    xhr.setRequestHeader('Content-Disposition', postdata);
    if(xhr.sendAsBinary) xhr.sendAsBinary(bin);	
    else xhr.send(file);
};
        
ddupload.upload_error = function (error) {
    alert("ddu upload error: " + error.code);
};   

