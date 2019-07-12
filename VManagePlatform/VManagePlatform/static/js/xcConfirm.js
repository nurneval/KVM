/*
 * 使用说明:
 * window.wxc.Pop(popHtml, [type], [options])
 * popHtml:html字符串
 * type:window.wxc.xcConfirm.typeEnum集合中的元素
 * options:扩展对象
 * 用法:
 * 1. window.wxc.xcConfirm("我是弹窗<span>lalala</span>");
 * 2. window.wxc.xcConfirm("Success","success");
 * 3. window.wxc.xcConfirm("Please Enter","input",{onOk:function(){}})
 * 4. window.wxc.xcConfirm("Customize",{title:"Customize"})
 */
(function($){
	window.wxc = window.wxc || {};
	window.wxc.xcConfirm = function(popHtml, type, options) {
	    var btnType = window.wxc.xcConfirm.btnEnum;
		var eventType = window.wxc.xcConfirm.eventEnum;
		var popType = {
			info: {
				title: "Information",
				icon: "0 0",//Blue i
				btn: btnType.ok
			},
			success: {
				title: "Success",
				icon: "0 -48px",//Green check
				btn: btnType.ok
			},
			error: {
				title: "Error",
				icon: "-48px -48px",//Red cross
				btn: btnType.ok
			},
			confirm: {
				title: "Prompt",
				icon: "-48px 0",//Yellow question mark
				btn: btnType.okcancel
			},
			warning: {
				title: "Caveat",
				icon: "0 -96px",//Yellow exclamation mark
				btn: btnType.okcancel
			},
			input: {
				title: "Enter",
				icon: "",
				btn: btnType.ok
			},
			custom: {
				title: "",
				icon: "",
				btn: btnType.ok
			}
		};
		var itype = type ? type instanceof Object ? type : popType[type] || {} : {};//Format the input parameters:Pop-up window type
		var config = $.extend(true, {
			//Attributes
			title: "", //Custom title
			icon: "", //icon
			btn: btnType.ok, //Buttons,Default single button
			//event
			onOk: $.noop,//Click OK button callback
			onCancel: $.noop,//Click cancel button callback
			onClose: $.noop//Closed callback,Return trigger event
		}, itype, options);
		
		var $txt = $("<p>").html(popHtml);//Pop-up window text dom
		var $tt = $("<span>").addClass("tt").text(config.title);//title
		var icon = config.icon;
		var $icon = icon ? $("<div>").addClass("bigIcon").css("backgroundPosition",icon) : "";
		var btn = config.btn;//Button group generation parameters
		
		var popId = creatPopId();//Popup Index
		
		var $box = $("<div>").addClass("xcConfirm");//Pop-up widget container
		var $layer = $("<div>").addClass("xc_layer");//Mask layer
		var $popBox = $("<div>").addClass("popBox");//Popup box
		var $ttBox = $("<div>").addClass("ttBox");//Pop-up window area
		var $txtBox = $("<div>").addClass("txtBox");//Popup content main area
		var $btnArea = $("<div>").addClass("btnArea");//Button area
		
		var $ok = $("<a>").addClass("sgBtn").addClass("ok").text("Confirm");//Confirm button
		var $cancel = $("<a>").addClass("sgBtn").addClass("cancel").text("Cancel");//Cancel button
		var $input = $("<input>").addClass("inputBox");//Input box
		var $clsBtn = $("<a>").addClass("clsBtn");//Close button
		
		//Create a button mapping relationship
		var btns = {
			ok: $ok,
			cancel: $cancel
		};
		
		init();
		
		function init(){
			//Handle special types of input
			if(popType["input"] === itype){
				$txt.append($input);
			}
			
			creatDom();
			bind();
		}
		
		function creatDom(){
			$popBox.append(
				$ttBox.append(
					$clsBtn
				).append(
					$tt
				)
			).append(
				$txtBox.append($icon).append($txt)
			).append(
				$btnArea.append(creatBtnGroup(btn))
			);
			$box.attr("id", popId).append($layer).append($popBox);
			$("body").append($box);
		}
		
		function bind(){
			//Click on the confirmation button
			$ok.click(doOk);
			
			//Enter key trigger confirmation button event
			$(window).bind("keydown", function(e){
				if(e.keyCode == 13) {
					if($("#" + popId).length == 1){
						doOk();
					}
				}
			});
			
			//Click the cancel button
			$cancel.click(doCancel);
			
			//Click the close button
			$clsBtn.click(doClose);
		}

		//Confirm button event
		function doOk(){
			var $o = $(this);
			var v = $.trim($input.val());
			if ($input.is(":visible"))
		        config.onOk(v);
		    else
		        config.onOk();
			$("#" + popId).remove(); 
			config.onClose(eventType.ok);
		}
		
		//Cancel button event
		function doCancel(){
			var $o = $(this);
			config.onCancel();
			$("#" + popId).remove(); 
			config.onClose(eventType.cancel);
		}
		
		//Close button event
		function doClose(){
			$("#" + popId).remove();
			config.onClose(eventType.close);
			$(window).unbind("keydown");
		}
		
		//Generate button group
		function creatBtnGroup(tp){
			var $bgp = $("<div>").addClass("btnGroup");
			$.each(btns, function(i, n){
				if( btnType[i] == (tp & btnType[i]) ){
					$bgp.append(n);
				}
			});
			return $bgp;
		}

		//Rebirth popId,Prevent id from repeating
		function creatPopId(){
			var i = "pop_" + (new Date()).getTime()+parseInt(Math.random()*100000);//Popup Index
			if($("#" + i).length > 0){
				return creatPopId();
			}else{
				return i;
			}
		}
	};
	
	//Button type
	window.wxc.xcConfirm.btnEnum = {
		ok: parseInt("0001",2), //Confirm button
		cancel: parseInt("0010",2), //Cancel button
		okcancel: parseInt("0011",2) //determine&&取消
	};
	
	//Trigger event type
	window.wxc.xcConfirm.eventEnum = {
		ok: 1,
		cancel: 2,
		close: 3
	};
	
	//Pop-up window type
	window.wxc.xcConfirm.typeEnum = {
		info: "info",
		success: "success",
		error:"error",
		confirm: "confirm",
		warning: "warning",
		input: "input",
		custom: "custom"
	};

})(jQuery);