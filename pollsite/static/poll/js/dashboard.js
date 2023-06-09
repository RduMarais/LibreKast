function copyToClipboard(targetUrl,targetName){
	var dest_url = document.location.protocol+'//'+document.location.host+targetUrl;
	navigator.clipboard.writeText(dest_url);
	console.log('destination url : '+dest_url);
	let copyNotif = document.createElement('small');
	copyNotif.innerText = targetName + trans_copied_clipboard;
	copyNotif.id = 'copy-notification-box';
	document.querySelector('#chatlog-title').appendChild(document.createElement('br'));
	document.querySelector('#chatlog-title').appendChild(copyNotif);
	setTimeout(function(){document.querySelector('#copy-notification-box').remove();}, 2000);
}

function cleanAlert(alertName){
	document.querySelector('#'+alertName).remove();
}
function showAlert(alertObj){
	let alertNotif = document.createElement('div');
	let alertTextBox = document.createElement('p');
	let alertTitleBox = document.createElement('p');
	alertTitleBox.classList.add("font-bold","m-1","text-center");
	alertTextBox.classList.add("text-center");
	alertNotif.classList.add("text-center","m-2");
	alertTitleBox.innerText = alertObj['message'];
	if(alertObj['message'] === "twitch-oauth-error") {
		alertNotif.classList.style = "background-color: lightblue;";
		alertTextBox.innerText = alertObj['text'];
		alertLink = document.createElement('a');
		alertLink.innerText = alertObj['url'];
		alertLink.href = alertObj['url'];
		alertTextBox.appendChild(alertLink);
	} else if(alertObj['message'] === "warning") {
		alertNotif.style = "background-color: lightyellow;"
		alertTextBox.innerText = alertObj['text'];
		alertTextBox.classList.add('italic');
	} else {
		alertNotif.classList.style = "background-color: lightpink;"
		alertTextBox.innerText = alertObj;
	}
	alertNotif.id = 'alert-notification-box-'+alertObj['message'];
	alertNotif.appendChild(alertTitleBox);
	alertNotif.appendChild(alertTextBox);
	document.querySelector('#meeting-title').appendChild(alertNotif);
	if(alertObj['message'] === "warning") {
		setTimeout(function(){document.querySelector('#alert-notification-box-warning').remove();}, 8000);
	}
}


function getQRCode(){
	// send request to prepare the QR code
	const createRequest = new XMLHttpRequest()
	console.log(meeting_qr_url)
	createRequest.open("GET", meeting_qr_url)
	createRequest.send()
	createRequest.onload = function() {
		if (createRequest.status === 200) {
		    console.log('QR created :'+createRequest.responseText)
			window.open(createRequest.responseURL);
		}
	}
}

function quickNdirtyExpandGraphHeight(height){
	document.querySelector('.anychart-ui-support').height.baseVal.valueAsString = height;
}


function updateScoreboard(scoresArray){
	tableBody = document.querySelector('#scoreboard-tbody');
	tableBody.textContent =''; //clear previous rows
	for(i in scoresArray){
		let row = document.createElement('tr');
		let username = document.createElement('td');
		let userscore = document.createElement('td');
		username.innerText = scoresArray[i].name;
		username.classList.add("break-words");
		userscore.innerText = scoresArray[i].score;
		userscore.id = 'librekast-userscore-'+scoresArray[i].id;
		row.appendChild(username);
		row.appendChild(userscore);
		if(meetingPlatform != 'IRL'){
			let userBadges = document.createElement('td');
			if(scoresArray[i].is_sub){
				userBadges.innerHTML += '<img class="w-4" src="'+sub_icon_url+'">';
			}
			if(scoresArray[i].yt){
				username.classList.add("text-red-700","dark:text-red-500");
				userBadges.innerHTML += '<img class="w-4" src="'+youtube_icon_url+'">';
			}
			if(scoresArray[i].tw){
				username.classList.add("text-purple-700","dark:text-pour1nf0-purple-100");
				userBadges.innerHTML = '<img class="w-4" src="'+twitch_icon_url+'">';
			}
			row.appendChild(userBadges);
		}
		tableBody.appendChild(row);
	}
}

function startQuestion(item){
	// console.log(item.innerHTML);
	id = item.id.split('-')[3];
	// change button for stop button
	item.onclick = null;
	questionResults = document.querySelector('#librekast-question-results-'+id);
	questionResults.innerHTML = "&#128202;" //rsults icon
	questionResults.onclick = function(item_stop){stopQuestion(questionResults);};
	item.innerHTML = "&#9723;"; // blanck icon

	// change button 
	document.querySelector("#meeting-question-go").classList.add('hidden');
	buttonResults = document.querySelector('#meeting-question-results');
	buttonResults.classList.remove('hidden');
	buttonResults.onclick = function(item){stopQuestion(questionResults);};

	dashboardSocket.send(JSON.stringify({
		'message': "admin-question-start",
		'question_id':id,
	}))
}

function stopQuestion(item_stop){
	// console.log(item_stop.innerHTML);
	id = item_stop.id.split('-')[3];
	// change button for Next button
	item_stop.onclick = null;
	questionNext = document.querySelector('#librekast-question-next-'+id);
	questionNext.innerHTML = "&#9193;"
	questionNext.onclick = function(item){nextQuestion(questionNext);}
	item_stop.innerHTML = "&#9723;"; //blank icon

	// change button 
	document.querySelector("#meeting-question-results").classList.add('hidden');
	buttonNext = document.querySelector('#meeting-question-next');
	buttonNext.classList.remove('hidden');
	buttonNext.onclick = function(item){nextQuestion(questionNext);};

	buttonScores = document.querySelector('#meeting-question-scores');
	buttonScores.classList.remove('hidden');
	buttonScores.onclick = function(item){sendScores(item);}; 


	dashboardSocket.send(JSON.stringify({
		'message': "admin-question-results",
		'question_id':id,
	}))
}

function nextQuestion(item_next){
	id = item_next.id.split('-')[3];
	item_next.onclick = null;
	item_next.innerHTML = "&#9723;"; //blank icon

	document.querySelector('#librekast-question-'+id).classList.remove('bg-red-200','dark:bg-pour1nf0-pink-400');
	document.querySelector('#librekast-question-status-'+id).innerHTML = '&#9745;';

	// change button 
	document.querySelector("#meeting-question-next").classList.add('hidden');
	document.querySelector("#meeting-question-scores").classList.add('hidden');

	dashboardSocket.send(JSON.stringify({
		'message': "admin-question-next", 
		'question_id':id,
	}))
	showWait();
}

function sendScores(item) {
	dashboardSocket.send(JSON.stringify({
		'message': "admin-send-scoreboard",
	}))
}


function updateMeetingPlan(questionId){
	questionStatus = document.querySelector('#librekast-question-status-'+questionId);
	questionStatus.innerHTML = '&#9989;';
	document.querySelector('#librekast-question-'+questionId).classList.add('bg-red-200','dark:bg-pour1nf0-pink-400');
	questionGo = document.querySelector('#librekast-question-go-'+questionId);
	// questionGo.classList.remove('hidden');
	questionGo.innerHTML = "&#9199;";
	questionGo.onclick = function(item){startQuestion(questionGo);}
	buttonGo = document.querySelector("#meeting-question-go");
	buttonGo.classList.remove('hidden');
	buttonGo.onclick = function(item){startQuestion(questionGo);}
	buttonPrevious = document.querySelector("#meeting-question-previous");
	if(buttonPrevious.classList.contains('hidden')){
		buttonPrevious.classList.remove('hidden');
		buttonPrevious.onclick = function(item){previousQuestion();}
	} 

}

function showQuestionText(questionObj){
	questionTitle.textContent = questionObj['title'];
	questionTitle.value = questionObj['id'];
	questionTitle.classList.add('librekast-'+questionObj['type']);
	questionDesc.innerHTML = questionObj['desc'];
	if(questionObj['type'] === 'WC'){showWordCloud(questionObj);}
	else if(questionObj['type'] !== 'TX'){showChoices(questionObj['choices'])}
}

function showResultsPoll(resultsArray){
	document.querySelector("#question-content").innerText = '';

	var chart = anychart.column();
	let chartData = [];
	for(i in resultsArray){
		a = [resultsArray[i].text,resultsArray[i].votes];
		chartData.push(a);
	}
	if(document.querySelector('#darkmode-button').value == 'night'){
		anychart.theme(anychart.themes.darkBlue);
		// anychart.theme(anychart.themes.darkGlamour);
	}
	chart.data(chartData);
	chart.container("question-content");

	chart.draw();
	quickNdirtyExpandGraphHeight(300);
}

function showResultsQuizz(resultsArray){
	for(i in resultsArray){
		if(resultsArray[i].isTrue){
			let s = document.createElement("span");
			s.innerHTML = "The answer was <b>"+resultsArray[i].text+"</b><br/>";
			questionDesc.appendChild(s);
		}
	}
	showResultsPoll(resultsArray);
}

function updateWordCloud(word){
	//updte value array
	let b = false;
	//if word exists
	let obj = wordCloudData.find((o, i) => {
		if (o.x === word) {
    		o.value++;
    		b = true;
    		return true;
		}
	});
	//add word to data if non existent
	if(!b){
		let n = {'x':word,'value':1};
		wordCloudData.push(n);
	}

	//remove old graph
	ocontent = document.querySelector('#question-content');
	ocontent.remove();
	//show ne graph
	ncontent = document.createElement("div");
	ncontent.id = "question-content";
	document.querySelector('#question-div').appendChild(ncontent);

	var chart = anychart.tagCloud(wordCloudData);
	if(document.querySelector('#darkmode-button').value == 'night'){
		// anychart.theme(anychart.themes.darkBlue);
		anychart.theme(anychart.themes.darkGlamour);
	}
	chart.angles([0]);
	chart.container("question-content");
	chart.draw();
	quickNdirtyExpandGraphHeight(250);
}

function showWordCloud(questionObj){
	console.log('start WC');
	wordCloudData = questionObj['choices'];

	// show results
	content = document.createElement("div");
	content.id = "question-content";
	document.querySelector('#question-div').appendChild(content);
	// console.log('created content');

	var chart = anychart.tagCloud(wordCloudData);
	if(document.querySelector('#darkmode-button').value == 'night'){
		anychart.theme(anychart.themes.darkGlamour);
		// anychart.theme(anychart.themes.darkBlue);
	}
	chart.angles([0]);
	chart.container("question-content");
	chart.draw();
	// console.log('WC drawn');
	quickNdirtyExpandGraphHeight(250);
}

function showChoices(choicesArray){
	console.log("choices array : "+choicesArray);
	content = document.createElement("div");
	content.id = "question-content";
	content.classList.add("py-8"); 
	content.classList.add("px-2"); 
	content.style="";
	document.querySelector('#question-div').appendChild(content);

	let l = document.createElement("ul");
	l.id="choice-table";
	content.appendChild(l);
	for(i in choicesArray){
		let c = document.createElement("li");
		c.innerText = choicesArray[i].text;
		c.id = 'choice-'+choicesArray[i].id;
		c.value = choicesArray[i].id;
		c.classList.add("bg-blue-200","hover:bg-blue-700","hover:text-white","dark:bg-pour1nf0-blue-400","dark:hover:bg-pour1nf0-blue-200");
		c.classList.add("text-blue-600","dark:text-gray-200","text-center","py-2","px-4","my-2","rounded");
		c.classList.add("librekast-choice");
		content.children[0].appendChild(c);
	}
}

function addFlagLog(flagAttempt){
	console.log('addFlagLog');
	flagLogSize = 6;
	let flaglog = document.querySelector('#latest-submissions-content');
	if(flaglog.childElementCount>=flagLogSize){
		flaglog.removeChild(flaglog.firstChild);
	}
	let l = document.createElement("p");
	let u = document.createElement("span");
	let t = document.createElement("span");
	l.classList.add("librekast-flaglog","mx-2","my-2");
	u.innerText = flagAttempt['user'];
	u.classList.add("text-pour1nf0-purple-800","librekast-flaglog-username","font-bold","mr-2");
	t.innerText = flagAttempt['code']+' ('+flagAttempt['correct']+')';
	t.classList.add("librekast-flaglog-code");
	l.appendChild(u);
	l.appendChild(t);
	flaglog.appendChild(l);
}

function previousQuestion(){
	alert('not implemented yet');
	//TODO
}


