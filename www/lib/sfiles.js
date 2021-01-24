var SFILES_URL = 'https://api.springfiles.com/json.php';
var REQUEST_TIMEOUT_MS = 7000;


var TYPE_GENERAL = 0;
var TYPE_SEARCH = 1;
var TYPE_DETAILS = 2;

var type = TYPE_GENERAL;

var hovermenuTimer = -1;
var HOVERMENU_TIME_MS = 3000;

var allCategories = {
	"game" : "Games",
	"map" : "Maps",
	"engine" : "Engines"
}

var contentUsageTipByCategory = {
	"game" : "<span class=\"content_h4\">What to do with this file?</span><br>First you need to download the Spring engine to play this game.<br><br>Games for Spring are .sd7 or .sdz files. To install this files move them into (Unix) ~/.spring/games or (Windows) \"My Documents\\My Games\\Spring\\games\".<br><br>Use the \"Reload maps/games\" option from the \"Tools\" menu in SpringLobby.",
	"map" : "<span class=\"content_h4\">What to do with this file?</span><br>First you need to download the Spring engine to play on this map.<br><br>Maps are .sd7 or .sdz files. To install this files move them into (Unix) ~/.spring/maps or (Windows) \"My Documents\\My Games\\Spring\\maps\".<br><br>Use the \"Reload maps/games\" option from the \"Tools\" menu in SpringLobby."
}

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

			clearTimeout(hovermenuTimer);
			hovermenuTimer = setTimeout(function () {
					$("#hovermenu").hide();
				}, HOVERMENU_TIME_MS);

		});

		$("body").click(function () {
			clearTimeout(hovermenuTimer);
			$("#hovermenu").hide();
		});

		clearInterval(checkExist);

	}, 50);
}

// get request parameter
function getGETParameter(name) {
	if (name = (new RegExp('[?&]' + encodeURIComponent(name) + '=([^&]*)')).exec(location.search)) {
		return decodeURIComponent(name[1]);
	}
}

// set hover menu content
function setHoverMenuContent() {
	var h = '<table cellpadding="0" cellspacing="0" border="0">';
	h += '<tr><td class="hovermenu_row"><button type="button" onclick="fGo(\'https://api.springfiles.com/upload/\')" class="hovermenu_button">Upload</button></td></tr>';
	h += '<tr><td class="hovermenu_row"><button type="button" onclick="fGo(\'https://github.com/spring/upq\')" class="hovermenu_button">About</button></td></tr>';
	h += '</table>';

	$("#hovermenu").html(h);
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
			}
		}
	}).done(function() {
		var newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + query;
		window.history.pushState({path:newUrl},'',newUrl);
	});
}


// process data and generate view
function processData(data) {
	if (data != null) {
		var h = '<table width="100%" ><tr><td align="center">';
		if (type == TYPE_GENERAL) {
			h+='<table width="100%"><tr>';
			
			// general description
			h+='<td colspan="3"><span style="font-size: 80%">This is a content repository for the <a class="abutton" href="https://www.springrts.com">Spring RTS Engine</a>, which features large 3D ground, air and naval battles on large maps with deformable terrain, supporting thousands of units, realistic simulation of projectiles and explosions and several 3D camera modes with complete freedom in movement.<br><br>To start playing SpringRTS games using content downloaded from this web site, you\'ll likely want to install a lobby client, but you can also download and run the engine by itself. You can find download links for the recommended lobby client <a class="abutton" href="https://springrts.com/wiki/Download">here</a>.</span><hr/></td></tr>';
			
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
				var date = item.timestamp;
				var mirrors = item.mirrors;
				var img = "images/unknown.jpg";
				if (item.mapimages && item.mapimages[0]) {
					img = item.mapimages[0];
				}
				var category = item.category.toUpperCase();
				var sdp = item.sdp;
				var md5 = item.md5;
				var version = item.version;
				// item table
				h += '<tr class="res_row'+(i%2 ? '_':'')+'"><td style="width:10px;">#' + (i + 1) + '</td><td style="width:100%"><table style="width: 100%;">';
				
				h+='<tr><td>'+date+'</td><td align="right"><span class="category"> '+category+' </span></td></tr>';
				h+='<tr><td>'+name+(version ? '<br><span style="font-size:70%">version '+version+'</span>':'')+'</td><td rowspan="2"><img style="width:6vw; height: 3vw; float:right" src="'+img+'"></td></tr>';
				h+='<tr><td><button onclick="go('+TYPE_DETAILS+',\''+md5+'\')">view details...</button></td></tr>';
				
				h += '</table></td></tr>';
			}
			h += '</table>';
			h+='</td>';

			// quick find - maps
			h+='<td style="width:25%" valign="top">';
			h += '<table cellpadding="5" cellspacing="0" border="0" class="search_results" style="width:30%; float: right;"><tr><th colspan="2" align="center"><span class="content_h3">Map Categories</span></th></tr>';
			h += '<tr><td><a href="?type=1&filter=&category=map&tags=1v1"><img class="quick_find_map_category" src="images/1v1.png"></a></td><td><a href="?type=1&filter=&category=map&tags=2v2"><img class="quick_find_map_category" src="images/2v2.png"></a></td></tr>';
			h += '<tr><td><a href="?type=1&filter=&category=map&tags=team"><img class="quick_find_map_category" src="images/team.png"></a></td><td><a href="?type=1&filter=&category=map&tags=ffa"><img class="quick_find_map_category" src="images/ffa.png"></a></td></tr>';
			h += '<tr><td><a href="?type=1&filter=&category=map&tags=metal"><img class="quick_find_map_category" src="images/metal.png"></a></td><td><a href="?type=1&filter=&category=map&tags=no-metal"><img class="quick_find_map_category" src="images/no-metal.png"></a></td></tr>';
			h += '<tr><td><a href="?type=1&filter=&category=map&tags=watermap"><img class="quick_find_map_category" src="images/water.png"></a></td><td><a href="?type=1&filter=&category=map&tags=some-water"><img class="quick_find_map_category" src="images/some-water.png"></a></td></tr>';
			h += '<tr><td><a href="?type=1&filter=&category=map&tags=no-water"><img class="quick_find_map_category" src="images/no-water.png"></a></td><td><a href="?type=1&filter=&category=map&tags=flat"><img class="quick_find_map_category" src="images/flat.png"></a></td></tr>';
			h += '<tr><td><a href="?type=1&filter=&category=map&tags=hilly"><img class="quick_find_map_category" src="images/hilly.png"></a></td><td><a href="?type=1&filter=&category=map&tags=mountainous"><img class="quick_find_map_category" src="images/mountainous.png"></a></td></tr>';
			h += '</table>';
			h+='</td>';
			
			h+='</tr></table>';
		} else if (type == TYPE_SEARCH) {
			// list of matching items
			h += '<table cellpadding="5" cellspacing="0" border="0" class="search_results" style="width:70%"><tr><th colspan="2" align="center"><span class="content_h1">Search Results</span></th></tr>';
				if (data && data.length > 0) {
				for (var i = 0; i < data.length; i++) {
					var item = data[i];
					
					var name = item.springname;
					var date = item.timestamp;
					var mirrors = item.mirrors;
					var img = "images/unknown.jpg";
					if (item.mapimages && item.mapimages[0]) {
						img = item.mapimages[0];
					}
					var category = item.category.toUpperCase();
					var sdp = item.sdp;
					var md5 = item.md5;
					var version = item.version;
					// item table
					h += '<tr class="res_row'+(i%2 ? '_':'')+'"><td style="width:1vw;">#' + (i + 1) + '</td><td style="width:100%"><table style="width: 100%;">';
					
					h+='<tr><td>'+date+'</td><td align="right"><span class="category"> '+category+' </span></td></tr>';
					h+='<tr><td>'+name+(version ? '<br><span style="font-size:70%">version '+version+'</span>':'')+'</td><td rowspan="2"><img style="width:6vw; height: 3vw; float:right" src="'+img+'"></td></tr>';
					h+='<tr><td><button onclick="go(TYPE_DETAILS,\''+md5+'\')">view details...</button></td></tr>';
					
					h += '</table></td></tr>';
				}
			} else {
				h+= '<tr><td>No results found.</td></tr>';
				
			}
			h += '</table>';

		} else if (type == TYPE_DETAILS) {
			
			if (data.length >0) {
				var item = data[0];
				var name = item.springname;
				var sdp = item.sdp;
				var md5 = item.md5;
				var version = item.version;
				var date = item.timestamp;
				var mirrors = item.mirrors;
				var mapImages = item.mapimages;
				var category = item.category;
				var size = item.size;
				var tags = item.tags;
				var filename = item.filename;
				var description = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed sed purus magna. Ut pharetra vestibulum mauris, ac hendrerit tortor tincidunt vel. Vestibulum sit amet turpis fringilla, interdum mi non, pharetra orci. Cras at cursus quam. Nullam at est quis velit viverra euismod nec at libero. Vestibulum accumsan purus mauris, at tristique felis ultricies sit amet. Aliquam consequat lacinia magna, id euismod erat euismod ac. Morbi posuere elit ut eleifend dictum. Sed congue volutpat consequat. Sed auctor augue odio, non laoreet risus vulputate vel. Morbi ac eros vel lacus ullamcorper posuere. Aliquam vulputate volutpat mi, non efficitur sapien pulvinar sit amet. Phasellus pulvinar tempus pellentesque. Maecenas hendrerit leo erat, eget porttitor leo dictum in.<br><br>Ut venenatis risus sit amet lectus lacinia, ut tincidunt orci tempus. Curabitur vitae tincidunt magna. Integer semper, magna eu pretium lobortis, orci dolor porttitor nibh, sit amet imperdiet justo quam a urna. Etiam semper nibh ligula, cursus hendrerit odio dignissim vel. Sed accumsan fringilla justo, at ultrices ante facilisis non. Vivamus in ipsum id sapien pharetra pharetra. Aliquam eleifend mollis ex, ac bibendum risus viverra ut. Morbi vel bibendum mi, sit amet luctus risus. In malesuada massa vel turpis consequat, id tincidunt felis aliquet. Nunc elit felis, condimentum sit amet hendrerit vel, fringilla in leo. Suspendisse potenti.<br><br>Cras scelerisque vestibulum pulvinar. Aenean vitae massa vitae mi dignissim porta. Etiam ultricies fermentum tellus, a sollicitudin metus semper at. Sed mattis consequat varius. Donec eu bibendum leo. Curabitur egestas justo mauris, nec fringilla justo tincidunt vel. Maecenas ac ex a justo ornare mollis vel quis nisl. Suspendisse id eros commodo, fringilla nibh a, semper eros. Aliquam nec porttitor odio, ultricies lacinia erat. Etiam luctus ipsum et massa hendrerit, ut pellentesque sapien molestie. Nunc eget arcu posuere, efficitur dolor non, rutrum diam. Duis aliquet libero id sem aliquam, non varius nulla consequat.<br><br>Morbi laoreet libero eu turpis semper, sit amet feugiat dolor efficitur. Proin interdum nibh id dui eleifend porttitor. Praesent pulvinar nulla in semper tincidunt. Donec commodo ligula ultricies facilisis elementum. Mauris varius blandit diam, in pretium erat pretium quis. Nullam aliquet sem et dolor iaculis, at cursus sem tincidunt. Praesent varius maximus congue. Etiam laoreet gravida nibh, a laoreet tellus tincidunt vel. Duis vulputate enim eget nibh maximus pulvinar. Integer hendrerit elit et dapibus cursus. Ut venenatis tellus vitae placerat molestie. Nunc tempus, ante non sollicitudin mattis, nibh sem sagittis ante, vitae mollis lacus enim nec libero. Aliquam erat volutpat. Sed velit enim, tincidunt sit amet purus eget, convallis lobortis urna.";
				
				// update document title
				document.title = item.springname;
				
				// details for the matching item
				h += '<table cellpadding="5" cellspacing="0" border="0" class="search_results" style="width:100%"><tr><th colspan="2" align="center"><span class="content_h1">'+name+(version ? '<br><span style="font-size:70%">version '+version+'</span>':'')+'</span></th></tr>';

				// details table
				h+= '<tr><td valign="top"><table>';
				h+='<tr><td><span class="label">Modified:</span> '+date+'</td></tr>';
				h+='<tr><td><span class="label">Category:</span> <span class="category"> '+category.toUpperCase()+' </span></td></tr>';
				if (sdp) {
					h+='<tr><td><span class="label">SDP:</span> '+sdp+'</td></tr>';
				}
				h+='<tr><td><span class="label">MD5:</span> '+md5+'</td></tr>';
				if (filename) {
					h+='<tr><td><span class="label">Filename:</span> '+filename+'</td></tr>';
				}
				h+='<tr><td><span class="label">Size:</span> '+size+' bytes</td></tr>';
				var tagsStr = "";
				if (tags && tags.length > 0) {
					for (var i=0; i< tags.length; i++) {
						tagsStr +='&emsp;<span class="category">'+tags[i]+'</span>';
					}
					h+='<tr><td><span class="label">Tags:</span> '+tagsStr+'</td></tr>';	
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

// clear filter
function clearFilter() {
	fGo('?type='+TYPE_GENERAL);
}

// go to search url
function go(t,filter,category,tags) {
	if (!t) {
		t = getGETParameter('type');
	}
	if (!t){
		t = TYPE_GENERAL;
	}
	if (!filter) {
		filter = $('#filter').val().trim();	
	}
	if (!filter) {
		filter = getGETParameter('filter');
	}
	if (!filter) {
		filter = "";
	}
	
	if (!category) {
		category = getGETParameter('category');
	}
	if (!category) {
		category = "";
	}
	if (!tags) {
		tags = getGETParameter('tags');
	}
	if (!tags) {
		tags = "";
	}
	var extraFilter = "";

	if (category || tags) {
		extraFilter = "(";
		if (category) {
			extraFilter += " "+category;
		}
		if (tags) {
			extraFilter += " "+tags;
		}
		extraFilter += " )";
	}
	$('#extraFilter').html(extraFilter);
	
	t = parseInt(t);
	type = t;
	var query = "";
	var sfQuery = "";
	//alert("t="+t+" filter="+filter);
	switch(t) {
		case (TYPE_GENERAL):
			query = "?type=" + TYPE_GENERAL;	
			sfQuery = "?nosensitive=on&images=on&springname=*";
		break;
		case (TYPE_SEARCH):
			query = "?type=" + TYPE_SEARCH+"&filter="+filter+"&category="+category+"&tags="+tags;	
			sfQuery = "?nosensitive=on&images=on&springname=*"+filter+"*&category=*"+category+"*&tags=*"+tags+"*";
		break;		
		case (TYPE_DETAILS):
			query = "?type=" + TYPE_DETAILS + "&filter=" + filter;
			sfQuery = "?nosensitive=on&images=on&md5=" + filter;
		break;
		default:
		
		break;
	}
	sendRequest(sfQuery,query);	
	
	if (type == TYPE_DETAILS) {
		$('#filter').val('');	
	} else {
		$('#filter').val(filter);
	}
}