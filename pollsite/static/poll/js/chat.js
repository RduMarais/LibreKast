function playAlert(alert){
	if(alert['url']){
		videoPlayer = '<video id="librekast-alert" controls><source src="'+alert['url']+'" type="video/webm;video/mp4" />'
		document.querySelector('#librekast-alertbox').innerHTML = videoPlayer;
		document.querySelector('#librekast-alertbox video').autoplay=true;
	}
}

function addChatLog(chatMessage){
	// let chatLogSize = {{ meeting.chat_log_size }} -1;
	let chatlog = document.querySelector('#chatlog-content');
	if(chatlog.childElementCount>=chatLogSize){
		chatlog.removeChild(chatlog.firstChild);
	}
	let l = document.createElement("p");
	let u = document.createElement("span");
	let t = document.createElement("span");
	l.classList.add("librekast-chatlog","mx-2","my-2");
	u.innerText = chatMessage['author'];
	u.classList.add("text-blue-700","librekast-chatlog-username","font-bold","mr-2");
	if(chatMessage['source']=='y'){
		u.classList.remove('text-blue-700');
		u.classList.add("librekast-youtube-username","text-red-700","dark:text-red-500");
		if(meetingPlatform == 'MX'){
		let youtubeIcon = document.createElement('img');
		youtubeIcon.classList.add("w-4","mr-1","inline","librekast-chatlog-platform");
		youtubeIcon.src = youtube_icon_url;
		l.appendChild(youtubeIcon);
		}
	}
	if(chatMessage['source']=='t'){
		u.classList.remove('text-blue-700');
		u.classList.add("librekast-twitch-username","text-purple-700","dark:text-purple-500");
		if(meetingPlatform == 'MX'){
		let twitchIcon = document.createElement('img');
		twitchIcon.classList.add("w-4","mr-1","inline","librekast-chatlog-platform");
		twitchIcon.src = twitch_icon_url;
		l.appendChild(twitchIcon);
		}
	}
	if(chatMessage['source']=='b'){
		t.classList.add("librekast-bot-message","italic");
		let botIcon = document.createElement('img');
			botIcon.classList.add("w-4","mr-1","inline","librekast-chatlog-bot");
			botIcon.src = bot_icon_url;
			l.appendChild(botIcon);
	}
	t.innerText = chatMessage['text'];
	t.classList.add("librekast-chatlog-msg","break-words");
	l.appendChild(u);
	l.appendChild(t);
	chatlog.appendChild(l);
}

function addChatLogDark(chatMessage){
	let chatlog = document.querySelector('#chatlog-content');
	if(chatlog.childElementCount>=chatLogSize){
		chatlog.removeChild(chatlog.firstChild);
	}
	let l = document.createElement("p");    //line
	let u = document.createElement("span"); //username
	let t = document.createElement("span"); //text
	l.classList.add("librekast-chatlog","mx-2","my-2","text-2xl");
	u.innerText = chatMessage['author'];
	u.classList.add("librekast-chatlog-username","font-bold","mr-2");
	if(chatMessage['source']=='y'){
		u.classList.add("librekast-youtube-username","text-red-100");
		if(meetingPlatform == 'MX'){
			let youtubeIcon = document.createElement('img');
			youtubeIcon.classList.add("w-4","mr-1","inline","librekast-chatlog-platform");
			youtubeIcon.src = youtube_icon_url;
			l.appendChild(youtubeIcon);
		}
	}
	if(chatMessage['source']=='t'){
		u.classList.add("librekast-twitch-username","text-purple-100");
		if(meetingPlatform == 'MX'){
			let twitchIcon = document.createElement('img');
			twitchIcon.classList.add("w-4","mr-1","inline","librekast-chatlog-platform");
			twitchIcon.src = twitch_icon_url;
			l.appendChild(twitchIcon);
		}
	}
	if(chatMessage['source']=='b'){
		t.classList.add("librekast-bot-message");
		let botIcon = document.createElement('img');
		botIcon.classList.add("w-4","mr-1","inline","librekast-chatlog-bot");
		botIcon.src = bot_icon_url;
		l.appendChild(botIcon);
	}
	t.innerText = chatMessage['text'];
	t.classList.add("librekast-chatlog-msg","break-words","text-white");
	l.appendChild(u);
	l.appendChild(t);
	chatlog.appendChild(l);
}
