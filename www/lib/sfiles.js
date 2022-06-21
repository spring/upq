var SFILES_URL = '/json.php';
//var SFILES_URL = 'https://springfiles.springrts.com/json.php'; // for local testing only
var REQUEST_TIMEOUT_MS = 7000;

var TYPE_GENERAL = 0;
var TYPE_SEARCH = 1;
var TYPE_DETAILS = 2;

var MAX_RECENT_ITEMS = 10;
var DEFAULT_SEARCH_ITEMS = 10;
var MORE_ITEMS_INCREMENT = 60;
var MAX_SEARCH_ITEMS = 10000;

var latestData = null;

var hoverMenuTimer = -1;
var HOVERMENU_TIME_MS = 3000;

var mapKeywordData = null;

// list of categories with ordered map keywords
var mapKeywordCategories = [ 
	{name: "Size", description: "Map area : smaller than 12x12,larger than 18x18 or in between" , keywords : ["small", "medium", "large"]}, 
	{name: "Land / Water", description: "How relevant are the water areas relative to land" ,keywords : ["land", "amphibious", "water"]},
	{name: "Traversability", description: "Is it particularly easy or hard for land/water units to move across the map" , keywords : ["open", "obstructed" ]}
];
// descriptions associated to map keywords
var mapKeywordDescriptions = {
	// size 
	small: "Map area <= 12x12", 
	medium: "12x12 < map area <= 18x18",
	large: "Map area > 18x18",
	// land / water
	land: "Mostly land",
	amphibious: "Mixed land and water areas, land-only or water-only units may not be viable",
	water: "Mostly water",
	// traversability
	open: "Mostly open, few or easily crossable terrain features",
	obstructed: "Many steep hills, chasms, land/water transitions or other choke points",
	lava: "Has lava instead of water",
	acid: "Has damage-dealing acid instead of water",
	"void": "Has void instead of water",
	air: "Key areas only reachable by air units",
	// other
	metal: "Continuous metal yield across the surface instead of discrete metal spots",
	ffa: "Map suitable for free-for-all battles"
};


// form fields used to generate query to server
var formFields = {
	"type" : TYPE_GENERAL,
	"filter" : "",
	"category" : "",
	"keywords" : "",
	"minW" : "",
	"minH" : "",
	"maxW" : "",
	"maxH" : "",
	"latestOnly" : 0
};
var nonTextFormFields = {"latestOnly": true}

var allCategories = {
	"game" : "Games",
	"map" : "Maps",
	"engine" : "Engines"
};

var contentUsageTipByCategory = {
	"game" : "<span class=\"content_h4\">What to do with this file?</span><br>First you need to download the Spring engine to play this game.<br><br>Games for Spring are .sd7 or .sdz files. To install these files move them into (Unix) ~/.spring/games or (Windows) \"My Documents\\My Games\\Spring\\games\".<br><br>Use the \"Reload maps/games\" option from the \"Tools\" menu in SpringLobby.",
	"map" : "<span class=\"content_h4\">What to do with this file?</span><br>First you need to download the Spring engine to play on this map.<br><br>Maps are .sd7 or .sdz files. To install these files move them into (Unix) ~/.spring/maps or (Windows) \"My Documents\\My Games\\Spring\\maps\".<br><br>Use the \"Reload maps/games\" option from the \"Tools\" menu in SpringLobby."
};

var gameThumbnailsRegex = [
{regex : /^metal factions[.]*/, thumbnail : "thumb_mf.jpg" },
{regex : /spring[:]* 1944[.]*/, thumbnail : "thumb_s44.png" },
{regex : /tech annihilation[.]*/, thumbnail : "thumb_techa.jpg" },
{regex : /^zero\-k[.]*/, thumbnail : "thumb_zk.png" },
{regex : /^nota[.]*/, thumbnail : "thumb_nota.jpg" },
{regex : /^balanced annihilation[.]*/, thumbnail : "thumb_ba.jpg" },
{regex : /^evolution rts[.]*/, thumbnail : "thumb_evo.jpg" },
{regex : /^imperial winter[.]*/, thumbnail : "thumb_swiw.jpg" },
{regex : /^kernel panic[.]*/, thumbnail : "thumb_kp.jpg" },
{regex : /^the cursed[.]*/, thumbnail : "thumb_cursed.jpg" },
{regex : /^xta[.]*/, thumbnail : "thumb_xta.jpg" },
{regex : /^beyond all reason[.]*/, thumbnail : "thumb_bar.jpg" }
];

// go to url
function fGo(url) {
	window.location = url;
}

// enable hover menu
function enableHoverMenu() {
	var checkExist = setInterval(function () {
		// enable hovermenu
		$(".menu_button").mouseover(function () {
			setHoverMenuContent();
			
			var pos = $(this).offset();
			var width = $(this).width();
			var childWidth = $("#hovermenu").width();
			var height = $(this).height();
			
			$("#hovermenu").css({
				top: pos.top + height,
				left: pos.left +width/2 - childWidth/2,
				position: 'absolute'
			});
			$("#hovermenu").show();

			clearTimeout(hoverMenuTimer);
			hoverMenuTimer = setTimeout(function () {
					$("#hovermenu").hide();
				}, HOVERMENU_TIME_MS);

		});

		$("body").click(function () {
			clearTimeout(hoverMenuTimer);
			$("#hovermenu").hide();
		});

		clearInterval(checkExist);

	}, 50);
}

function toggleFilterFormVisibility() {
	if ($("#filterFormDiv").is(":visible")) {
		$("#filterFormDiv").hide();
	} else {
		showFilterForm();
	}
}

function showFilterForm() {
	setFilterFormContent();

	// show box horizontally centered on filter button  	
	// but get the top offset from the menu icon instead
	var pos = $("#filterFormButton").offset();
	var width = $("#filterFormButton").width();
	var childWidth = $("#filterFormDiv").width();
	var top = $(".menu_button").offset().top+$(".menu_button").height();
	
	$("#filterFormDiv").css({
		top: top,
		left: pos.left +width/2 - childWidth/2,
		position: 'absolute'
	});
	$("#filterFormDiv").show();
}

// get request parameter
function getGETParameter(name) {
	if (name = (new RegExp('[?&]' + encodeURIComponent(name) + '=([^&]*)')).exec(location.search)) {
		return decodeURIComponent(name[1]);
	}
	return null;
}

// set hover menu content
function setHoverMenuContent() {
	var h = '<table cellpadding="0" cellspacing="0" border="0">';
	h += '<tr><td class="hovermenu_row"><button type="button" onclick="fGo(\'/upload/\')" class="hovermenu_button">Upload</button></td></tr>';
	h += '<tr><td class="hovermenu_row"><button type="button" onclick="fGo(\'https://github.com/spring/upq\')" class="hovermenu_button">About</button></td></tr>';
	h += '</table>';

	$("#hovermenu").html(h);
}

// set filter form
function setFilterFormContent() {
	var h = '<table cellspacing="1" border="0" class="filterFormTable">';
	if (formFields.category) {
		h += '<tr><th>Filter parameters ('+formFields.category+')</th></tr>';
		if (formFields.category == "map") {
			h += '<tr><td>Size: <input type="text" id="minW" maxlength="2" size="1" onchange="syncFormField(this)">&nbsp;x&nbsp;';
			h += '<input type="text" id="minH" maxlength="2" size="1" onchange="syncFormField(this)"> to ';
			h += '<input type="text" id="maxW" maxlength="2" size="1" onchange="syncFormField(this)">&nbsp;x&nbsp;';
			h += '<input type="text" id="maxH" maxlength="2" size="1" onchange="syncFormField(this)"></td></tr>';

			h += '<tr><td>Key Words: <input type="text" id="keywords" maxlength="30" size="10" onchange="syncFormField(this)"><br><span style="font-size:80%">lower case words separated by &quot;,&quot;</span></td></tr>';		
			
			h += '<tr><td>Only show latest version for each item <input type="checkbox" id="latestOnly" value="1" onchange="syncFormField(this)"></td></tr>';
		} else {
			h += '<tr><td>Extra filter parameters only available for maps...</td></tr>';
		}
	} else {
		for (key in allCategories) {
			h+='<tr><td><a class="abutton" style="font-size: 90%" href="?type=1&filter=&category='+key+'">'+allCategories[key]+'</a></td></tr>';
		}
	}
	h += '</table>';

	$("#filterFormDiv").html(h);
	
	updateAvailableFormFields();
}

// generate centered loading gif thingy
function generateLoadingHtml() {
	return '<table width="100%"><tr><td align="center" valign="middle" height="300px"><div style="width:128px; height: 128px; padding:20px; background-image: url(\'images/loading_bg.png\');"><img width="128px" height="128px" src="images/loading.gif" alt="loading..."></div></td></table>';
}


// send request
function sendRequest(sfQuery,query) {
	// loading...
	$('#dataDiv').html(generateLoadingHtml());

	/*
	$.ajax({
		url: SFILES_URL + query,
		dataType: "json",
		timeout: REQUEST_TIMEOUT_MS,
		success: function (data) {
			processData(data);
		},
		error: function (XHR, textStatus, errorThrown) {
			if (textStatus === "timeout") {
				// something went wrong, show message
				$('#dataDiv').html("<h2>Server unavailable.<br/><br/>Please try again later...</h2>");
			}
		}
	});
	*/
	$.ajax({
		url: SFILES_URL + sfQuery,
		dataType: "jsonp",
		timeout: REQUEST_TIMEOUT_MS,
		crossDomain: true,
		jsonpCallback: "processData",
		error: function (XHR, textStatus, errorThrown) {
			if (textStatus === "timeout") {
				// something went wrong, show message
				$('#dataDiv').html("<h2>Server unavailable.<br/><br/>Please try again later...</h2>");
			} else if (textStatus === "error") {
				$('#dataDiv').html("<h2>Server error.<br/><br/>Please try again later...</h2>");
			}
		}
	}).done(function() {
		var newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + query;
		window.history.pushState({path:newUrl},'',newUrl);
		
		// if map keyword data hasn't been loaded yet, get it
		if (mapKeywordData == null) {
			sendMapKeywordDataRequest();
		}
	});
}

// get map keyword data from server
function sendMapKeywordDataRequest() {
	$.ajax({
		url: SFILES_URL + "?getMapKeywordData=1",
		dataType: "jsonp",
		timeout: REQUEST_TIMEOUT_MS,
		crossDomain: true,
		jsonpCallback: "processMapKeywordData"
	});
}


// get "width X height" string from metadata if item is a map
function getMapSizeStrFromMetadata(item) {
	var metadata = item.metadata;
	var mapSizeStr = "";
	if (metadata && item.category == "map") {
		mapSizeStr = ""+metadata.Width +"&nbsp;X&nbsp;"+ metadata.Height; 
	}
	return mapSizeStr;
}

// format date
function formatDate(dateStr) {
	if(dateStr) {
		return dateStr.substring(0,dateStr.indexOf("T"))+"&nbsp;"+dateStr.substring(dateStr.indexOf("T")+1);
	}
	
	return "";
}

// capitalize first character in a string
function capitalizeFirstChar(str) {
	return str.charAt(0).toUpperCase() + str.slice(1);
}

// get item thumbnail
function getItemThumbnail(item) {
	var img = "images/unknown.jpg";
	try {
		var category = item.category.toUpperCase();
		var lcName = item.springname.toLowerCase();
		if (item.mapimages && item.mapimages[0]) {
			img = item.mapimages[0];
		} else {
			if (category.indexOf("ENGINE") >= 0) {
				img = "images/spring_logo.png";
			} else if (category == "GAME") {
				for (var j=0; j<gameThumbnailsRegex.length; j++ ) {
					var obj = gameThumbnailsRegex[j];
					if (obj.regex.test(lcName)) {
						img = "images/games/"+obj.thumbnail;
						break;
					}
				}
			}
		}
	} catch(ex) {
		img = "images/unknown.jpg";
	}
	return img;
}

// compose html for map category/keyword shortcuts table
function getMapKeywordDataHtml() {
	if (mapKeywordData != null) {
		var shownKeywords = {}
		var kwDataByName = {}
		for (var i = 0; i < mapKeywordData.length; i++) {
			var item = mapKeywordData[i];
			kwDataByName[item.keyword] = item;
		} 
		
		var h = '<table cellpadding="5" cellspacing="0" border="0" class="search_results" style="float: right;"><tr><th colspan="2" align="center"><span class="content_h3">Map Categories</span></th></tr>';
		// first try to show categorized keywords
		for (var i=0; i < mapKeywordCategories.length; i++) {
			var cat = mapKeywordCategories[i];
			var catShown = false;
			
			for (var j=0; j< cat.keywords.length; j++) {
				var kw = cat.keywords[j];
				var item = kwDataByName[kw]
				if (kwDataByName[kw]) {
					if (!catShown) {
						h += '<tr><td class="quick_find_map_category"><span style="font-size: 80%" title="'+cat.description+'">'+cat.name+'</span></td></tr>';
						catShown = true;
					}
					h+='<tr><td>&emsp;<a class="abutton" href="?type=1&filter=&category=map&keywords='+kw+'&latestOnly=1" title="'+mapKeywordDescriptions[kw]+'">'+capitalizeFirstChar(kw)+'</a>&nbsp;<span style="font-size: 90%" >('+item.maps+')</span> </td></tr>';
					shownKeywords[kw] = 1;
				}
			}
		}
		
		// show remaining keywords
		if (Object.keys(shownKeywords).length < mapKeywordData.length) {
			h += '<tr><td class="quick_find_map_category"><span style="font-size: 80%" title="Other properties">Other</span></td></tr>';
		
			for (var i = 0; i < mapKeywordData.length; i++) {
				var item = mapKeywordData[i];
				var kw = item.keyword;
				
				if (!shownKeywords[kw]) {
					h+='<tr><td>&emsp;<a class="abutton" href="?type=1&filter=&category=map&keywords='+kw+'&latestOnly=1" '+(mapKeywordDescriptions[kw] ? ' title="'+mapKeywordDescriptions[kw]+'"' : '')+'>'+capitalizeFirstChar(kw)+'</a>&nbsp;<span style="font-size: 90%" >('+item.maps+')</span> </td></tr>';
					shownKeywords[kw] = 1;
				}
			}
		
		}
		
		h += '</table>';

		return h;		
	}
	return "";
}

// process map keyword data, update view if available
function processMapKeywordData(data) {
	if (data != null) {
		mapKeywordData = data;
		
		var div = document.getElementById("mapKeywordShortcutsDiv");
		if (div) {
			div.innerHTML = getMapKeywordDataHtml(); 	
		}
	}
}

// process data and generate view
function processData(data,showLimit) {
	if (data != null) {
		var h = '<table width="100%" ><tr><td align="center">';
		
		if (formFields.type == TYPE_GENERAL) {
			h+='<table width="100%"><tr>';
			
			// general description
			h+='<td colspan="3"><span style="font-size: 80%">This is a content repository for the <a class="abutton" href="https://www.springrts.com">Spring RTS Engine</a>, which runs games featuring large 3D ground, air and naval battles on large maps with deformable terrain, supporting thousands of units, realistic simulation of projectiles and explosions and several 3D camera modes with complete freedom in movement.<br><br>To start playing SpringRTS games using content downloaded from this web site, you\'ll likely want to install a lobby client, but you can also download and run the engine by itself. You can find download links for the recommended lobby client <a class="abutton" href="https://springrts.com/wiki/Download">here</a>.</span><hr/></td></tr>';
			
			h+='<tr>';
			// quick find - categories
			h+='<td style="width:25%" valign="top">';
			h += '<table cellpadding="5" cellspacing="0" border="0" class="search_results" style="width:70%;float:left;"><tr><th align="center"><span class="content_h3">Spring Categories</span></th></tr>';
			for (key in allCategories) {
				h+='<tr><td><a class="abutton" href="?type=1&filter=&category='+key+'">'+allCategories[key]+'</a></td></tr>';
			}
			h += '</table>';
			h+='</td>';			
			
			// list of recent items
			h+='<td style="width:50%" valign="top">';
			h += '<table cellpadding="5" cellspacing="0" border="0" class="search_results" style="width:100%"><tr><th colspan="2" align="center"><span class="content_h1">Latest Entries</span></th></tr>';
			
			for (var i = 0; i < data.length; i++) {
				var item = data[i];
				
				var name = item.springname;
				var date = formatDate(item.timestamp);
				var mirrors = item.mirrors;
				var img = getItemThumbnail(item);
				var category = item.category.toUpperCase();
				var sdp = item.sdp;
				var md5 = item.md5;
				var version = item.version;
				var mapSizeStr = getMapSizeStrFromMetadata(item);
				
				// item table
				h += '<tr class="res_row'+(i%2 ? '_':'')+'"><td style="width:10px;">#' + (i + 1) + '</td><td style="width:100%"><table style="width: 100%;">';
				
				h+='<tr><td>'+name+'</td><td align="right"><span class="category"> '+category+' </span></td></tr>';
				h+='<tr><td style="font-size:80%">'+date+(version ? '<br>version '+version:'')+(mapSizeStr ? '<br>'+mapSizeStr:'')+'</td><td rowspan="2" style="width:6vw;"><img class="search_thumbnail" src="'+img+'"></td></tr>';
				h+='<tr><td><button onclick="go('+TYPE_DETAILS+',\''+md5+'\')">view details...</button></td></tr>';
				
				h += '</table></td></tr>';
				if (i >= MAX_RECENT_ITEMS -1) {
					break;
				}
			}
			h += '</table>';
			h+='</td>';

			// quick find - maps
			h += '<td style="width:25%" valign="top" id="mapKeywordShortcutsDiv">';
			h += getMapKeywordDataHtml(); 
			h += '</td>';
			
			h+='</tr></table>';
		} else if (formFields.type == TYPE_SEARCH) {
			// list of matching items
			h += '<table cellpadding="5" cellspacing="0" border="0" class="search_results" style="width:70%"><tr><th colspan="2" align="center"><span class="content_h1">Search Results<br><span style="font-size:50%">'+(data.length > MAX_SEARCH_ITEMS ? (Math.min(data.length,MAX_SEARCH_ITEMS)+"+") : data.length )+' matches</span></span></th></tr>';
			if (data && data.length > 0) {
				latestData = data;
				var resultsShown = 0;
				for (var i = 0; i < data.length; i++) {
					var item = data[i];
					
					var name = item.springname;
					var date = formatDate(item.timestamp);
					var mirrors = item.mirrors;
					var category = item.category.toUpperCase();
					var img = getItemThumbnail(item);
					var sdp = item.sdp;
					var md5 = item.md5;
					var version = item.version;
					var mapSizeStr = getMapSizeStrFromMetadata(item);
					
					// item table
					h += '<tr class="res_row'+(i%2 ? '_':'')+'"><td style="width:1vw;">#' + (i + 1) + '</td><td style="width:100%"><table style="width: 100%;">';
					
					h+='<tr><td>'+name+'</td><td align="right"><span class="category"> '+category+' </span></td></tr>';
					h+='<tr><td style="font-size:80%">'+date+(version ? '<br>version '+version:'')+(mapSizeStr ? '<br>'+mapSizeStr:'')+'</td><td rowspan="2" style="width:6vw;"><img class="search_thumbnail" src="'+img+'"></td></tr>';
					h+='<tr><td><button onclick="go(TYPE_DETAILS,\''+md5+'\')">view details...</button></td></tr>';
					
					h += '</table></td></tr>';
					resultsShown++;
					if ((!showLimit && resultsShown >= DEFAULT_SEARCH_ITEMS) || (resultsShown >= showLimit)) {
						break;
					}
				}
				if (data.length > resultsShown) {
					if(!showLimit) {
						showLimit = 0;
					}
					h += '<tr><td colspan="2" align="center"><button type="button" onclick="processData(latestData,'+(showLimit+60)+')"> ... more ...</button></td></tr>';
				}
			} else {
				h+= '<tr><td>No results found.</td></tr>';
				
			}
			h += '</table>';

		} else if (formFields.type == TYPE_DETAILS) {
			
			if (data.length >0) {
				var item = data[0];
				var name = item.springname;
				var sdp = item.sdp;
				var md5 = item.md5;
				var version = item.version;
				var date = formatDate(item.timestamp);
				var mirrors = item.mirrors;
				var mapImages = item.mapimages;
				var category = item.category;
				var size = item.size;
				var keywords = item.keywords;
				var filename = item.filename;
				var description = "";
				var metadata = item.metadata;
				if (metadata) {
					description = metadata.Description;
				}
				var mapSizeStr = getMapSizeStrFromMetadata(item);
				var author = "?";
				if (metadata) {
					author = metadata.Author;
				}
				
				// update document title
				document.title = item.springname;
				
				// details for the matching item
				h += '<table cellpadding="5" cellspacing="0" border="0" class="search_results" style="width:100%"><tr><th colspan="2" align="center"><span class="content_h1">'+name+(version ? '<br><span style="font-size:70%">version '+version+'</span>':'')+'</span></th></tr>';

				// details table
				h+= '<tr><td valign="top"><table>';
				h+='<tr><td><span class="label">Modified:</span> '+date+'</td></tr>';
				h+='<tr><td><span class="label">Category:</span> <span class="category"> '+category.toUpperCase()+' </span></td></tr>';
				h+='<tr><td><span class="label">Author:</span> '+author+'</td></tr>';
				if (sdp) {
					h+='<tr><td><span class="label">SDP:</span> '+sdp+'</td></tr>';
				}
				h+='<tr><td><span class="label">MD5:</span> '+md5+'</td></tr>';
				if (filename) {
					h+='<tr><td><span class="label">Filename:</span> '+filename+'</td></tr>';
				}
				var sizeMb = size/(1024*1024);
				h+='<tr><td><span class="label">Size:</span> '+sizeMb.toFixed(1)+' MB ('+size+' bytes)</td></tr>';
				var keywordsStr = "";
				if (keywords && keywords.length > 0) {
					keywords = keywords.split(',');
					for (var i=0; i< keywords.length; i++) {
						var kwDesc = "";
						if (category == "map") {
							kwDesc = mapKeywordDescriptions[keywords[i]];
						}
						
						keywordsStr +='&nbsp;<span class="category" '+(kwDesc ? ' title="'+kwDesc+'"':'')+'>'+keywords[i]+'</span>';
					}
					h+='<tr><td><span class="label">Keywords:</span> '+keywordsStr+'</td></tr>';	
				}

				if (mirrors && mirrors.length > 0) {
					var links = "";
					for (var i=0; i< mirrors.length; i++) {
						links +='&emsp;<a href="'+mirrors[i]+'">LINK'+(i+1)+'</a>';
					}
					h+='<tr><td><span class="label">Download links:</span>'+links+'</td></tr>';
				} else {
					h+='<tr><td>No download links found.</td></tr>';
				}
				
				var tip = contentUsageTipByCategory[category];
				if (tip) {
					h+='<tr><td style="font-size:80%"><hr/>'+tip+'</td></tr>';
				}
				if (metadata) {
					if (category == "map") {
						h+='<tr><td><hr/><h4>In-game properties:</h4></td></tr>';
						h+='<tr><td><span class="label">Size:</span> '+mapSizeStr+'</td></tr>';
						h+='<tr><td><span class="label">Wind:</span> '+metadata.MinWind+'-'+metadata.MaxWind+'</td></tr>';
						h+='<tr><td><span class="label">Tidal:</span> '+metadata.TidalStrength+'</td></tr>';
						h+='<tr><td><span class="label">Gravity:</span> '+metadata.Gravity+'</td></tr>';
					}
				}

				if (description) {
					h+='<tr><td><hr/>'+description+'</td></tr>';
				}
				
				h += '</table></td>';
				// images table
				h+= '<td valign="top"><table>';
				if (mapImages && mapImages.length > 0) {
					for (var i=0; i< mapImages.length; i++) {
						h+='<tr><td><img style="max-width:18vw;max-width:18vw;" src="'+mapImages[i]+'"></td></tr>';
					}
				}
				h += '</table></td></tr>';

				h += '</table>';
			
			} else {
				h += 'No results found.';
			}
		}
		h += '</td></tr></table>';
		$('#dataDiv').html(h);
	}
}

// writes message string
function writeMessage(msg) {
	var messageDiv = document.getElementById('messageDiv');
	messageDiv.innerHTML = msg;
}

// appends message string
function appendMessage(msg) {
	var messageDiv = document.getElementById('messageDiv');
	messageDiv.innerHTML += '<br/>' + msg;
}

// clear filter (reload page)
function clearFilter() {
	fGo('?type='+TYPE_GENERAL);
}

// clear form fields
function clearFormFields() {
	for (const paramId in formFields) {
		if (!nonTextFormFields[paramId]) {
			formFields[paramId] = "";
		}
	}
	formFields.latestOnly = 0;
	formFields["type"] = TYPE_GENERAL;
	updateAvailableFormFields();
}

// sync html input value with formFields js table
function syncFormField(el) {
	if ($(el).is(':checkbox')) {
		formFields[el.id] = el.checked ? 1 : 0;
	} else {
		formFields[el.id] = el.value;
	}
}

// load filter parameters from url query string
function loadFilterParametersUrl() {
	for (const paramId in formFields) {
		var value = getGETParameter(paramId);
		if (value !== null) {
			formFields[paramId] = value;
		}
	}
}

// update all available form fields to match the formFields
function updateAvailableFormFields() {
	for (const paramId in formFields) {
		if (!nonTextFormFields[paramId]) {
			setFormTextField(paramId,formFields[paramId]);
		}
	}
	setFormCheckboxField('latestOnly',formFields.latestOnly);
}
// set a form text field value, if available
function setFormTextField(paramId,value) {
	var obj = $('#'+paramId);
	if (obj.length > 0) {
		obj.val(value);
	}
}
// set a form checkbox field value, if available
function setFormCheckboxField(paramId,value) {
	var obj = $('#'+paramId);
	if (obj.length > 0) {
		obj.prop( "checked", value ? 1 : 0 );
	}
}

// get form text field
function getFormTextField(paramId) {
	var obj = $('#'+paramId);
	if (obj.length > 0) {
		return obj.val().trim();
	}
	return null;
}

// get form checkbox field
function getFormCheckboxField(paramId) {
	var obj = $('#'+paramId);
	if (obj.length > 0) {
		return obj.is(':checked') ? 1 : 0;
	}
	return null;
}

// send request to get data from server
// set parameters override formFields table
// response updates url query string to match
function go(type,filter,category,keywords) {
	if (!type) {
		type = formFields.type;
	} else {
		formFields.type = type;
	}
	
	if (!filter) {
		filter = $('#filter').val().trim();	
		// replace spaces and separators with * for easier matching
		filter = filter.replace(/[ \-_]/g,"*");
	} else {
		// replace spaces and separators with * for easier matching
		filter = filter.replace(/[ \-_]/g,"*");
		formFields.filter = filter;
		setFormTextField('filter',filter);
	}
	
	if (!category) {
		category = formFields.category;
	} else {
		formFields.category = category;
	}
	
	if (!keywords) {
		keywords = formFields.keywords;
	} else {
		formFields.keywords = keywords;
	}

	// visual indicator of category selected
	var extraFilter = "";
	if (category || keywords) {
		extraFilter = "(";
		if (category) {
			extraFilter += " "+category;
		}
		if (keywords) {
			extraFilter += " "+keywords;
		}
		extraFilter += " )";
	}
	$('#extraFilter').html(extraFilter);

	// add filter form 
	if (category) {
		setFilterFormContent();
	}
	
	var query = "";
	var sfQuery = "";
	var filterformQStr = "";
	switch(category) {
		case ("map"): 
			filterformQStr = "&minW="+formFields.minW+"&minH="+formFields.minH+"&maxW="+formFields.maxW+"&maxH="+formFields.maxH+"&latestOnly="+formFields.latestOnly+"&keywords="+keywords;
		break;
		default:
			filterformQStr = "&latestOnly="+formFields.latestOnly+"&keywords="+keywords;
		break;
	}
	//alert("t="+t+" filter="+filter);
	switch(parseInt(type)) {
		case (TYPE_GENERAL):
			query = "?type=" + TYPE_GENERAL;	
			sfQuery = "?nosensitive=on&images=on&metadata=1&springname=*";
		break;
		case (TYPE_SEARCH):
			query = "?type=" + TYPE_SEARCH+"&filter="+filter+"&category="+category+filterformQStr;	
			sfQuery = "?nosensitive=on&images=on&metadata=1&springname=*"+filter+"*&category=*"+category+"*&keywords="+keywords+"&limit="+MAX_SEARCH_ITEMS+filterformQStr;
		break;		
		case (TYPE_DETAILS):
			query = "?type=" + TYPE_DETAILS + "&filter=" + filter;
			sfQuery = "?nosensitive=on&metadata=1&images=on&md5=" + filter;
		break;
		default:
		
		break;
	}
	
	sendRequest(sfQuery,query);
}
