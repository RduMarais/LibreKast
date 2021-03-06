# LibreKast

**A nice and free web app to gamify and animate your meetings, build with django channels and anychart free.**

I am not a developper, so this code is far from perfect ! Although it runs, please bear in mind that the design of LibreKast is driven by what I managed to do, and not really what I planned to do (in terms of design).

[![GitHub license](https://img.shields.io/github/license/RduMarais/LibreKast)](https://github.com/RduMarais/LibreKast/blob/master/LICENSE)


## Functionnalities

There are 4 types of question you can show in the app : 

 * **Text-only** : displays only text (ideal for start and end of the meeting)
 * **word cloud** : displays a chart with all submitted words
 * **poll** : asks a question. on question close, shows the number of votes each choice got.
 * **Quizz** : asks a question. One of the answers is marked as 'correct', all attendants that chose the correct answer receive 1 point, the first one to answer receives an additionnal point.

The meeting organizer can access a special dashboard with live scoreboard, live results and buttons to navigate between questions.

There are 3 types of meetings : 

 * IRL meetings : those are beekast-like meetings. You need to register as explained below to join the meeting.
 * Youtube Live Stream : the chat is automatically fetched by Youtube
 * Twitch live Stream : the chat is fetched with Twitch Helix API (needs API tokens)

To connect to a meeting, participants only need to go to Meetings > choose the meetings. A meeting code is needed to register, by default it is `Pour1nf0`.

You can connect in the admin interface with user : `defaultsuperuser` and password `LibreKast`. To pass some questions, just mark them as done in the admin panel. Every request gets the next question by fetching the first question in order that has no already be done.

#### demo

 * Admin : `defaultsuperuser` : `LibreKast`
 * Join Meeting code : `Pour1nf0`

#### Screenshots

![](screenshots/dashboard.png)

You can find screenshots : 

 * [of quizz correction](screenshots/quizz.png)
 * [of home page](screenshots/home.png)

## Project roadmap

v0.4.0 : more functionnalities

 * [ ] add Image slides
 * [ ] back : automatically generate short answer for poll & quizz
 * [x] back : setup bots commands models
 * [x] back : setup bots commands for Twitch and Youtube
 * [ ] back : go back button in dashboard
 * [ ] back : generate QR code
 * [ ] Youtube : automatically generate short answer for poll & quizz
 * [ ] Youtube : setup alert for Youtube creds
 * [x] Youtube : Revolution bots support
 * [x] Youtube : Bug : has several subscirber
 * [x] Youtube : handle refresh token renewal
 * [ ] Twitch : add attendee is subscriber attribute in dashboard
 * [x] front : Revolution bots (with sound)
 * [x] front : Revolution bots (with transparency)
 * [ ] front : go back button in dashboard
 * [ ] front : have a nicer dashboard
 * [ ] front : change admin interface to be modular
 * [ ] front : create a meeting admin interface
 * [ ] front : type de question : appr??ciation /100 (??chelle)
 * [ ] front : type de question : vote bay??sien = plusieurs appr??ciation sur 5)
 * [ ] BUG : reproduce & solve error in transition from YT WC to YT poll in prod throwing an exception

v0.5.0 : installation and Quality of Life

 * [x] install script
 * [ ] Youtube : setup oauth redirection for API
 * [ ] refactor : make question object-oriented in consumers
 * [ ] refactor : code wrapping and documentation
 * [ ] back : join during a question
 * [ ] refactor : use proper logging
 * [ ] docker wrapping
 * [ ] readthedocs
 * [ ] documentation on Google & Twitch API
 * [ ] documentation on OBS integration
 * [ ] dulicate question and meetings
 * [ ] make twitch and youtube an interface and have bot logic in a separate file

#### code architecture

The code is a django project named 'pollsite', made with 2 apps : 

 * `home` : hosts all the appearance of the home page as models.
 * `polls` : hosts all the core functionalities of the app.
 * `static`
 * `templates`

In `polls` app, the different URLs are handled in the `views.py` file. All websockets communications are handled (synchronously) in the `consumers.py` file.
The difference between question types is handled using a `question_type` attribute, which can be `TO`, `QZ`, `QZ` or `WC`.

For the meeting types, I went with optional fields instead of a complex heritage model, in order to get quickly something worrking. Yes it's lame, but hey - it works.

## How to deploy test instance with docker

> Please note that the docker version only uses developpement server and is not ready for production environment !

Copy all the files by cloning the repo with : 

```
git clone https://github.com/RduMarais/LibreKast.git --depth 1
```

Simply run : 

```bash
cd Librekast
docker-compose up
```


> Please note that as of today, the server in docker is the development sever. Next push will be gunicorn/uvicorn.


## How to deploy for developpment

__pre-requisites : python(3.8 or above) and pip must be installed__ 



**0. create and activate a virtual environment inside a new directory**

It is highly recommended to use virtual environments when yout set up a new project. If you are new to virtual environments read [python-3 official docs](https://docs.python.org/3/library/venv.html) 

**1. clone this repo `django-polling-site` in your directory**

```bash
git clone https://github.com/RduMarais/LibreKast.git
```

**2. install the requirements**

The requirements listed are the versions I used to test & develop the app. Feel free to tamper with the versions, just keep in mind that different package versions have not been tested !

```bash
# debian/Ubuntu etc
sudo apt-get install libmagic1
# MacOs : 
brew install libmagic

# install python packages 
pip install -r requirements.txt
```

**3. move inside the `pollsite` directory and make migrationS**

```bash
python manage.py makemigrations home
python manage.py makemigrations poll
python manage.py migrate
```

**4. Security settings**

create a superuser , with your own username and password

```bash
python manage.py createsuperuser
```
A default superuser exists, named `defaultsuperuser` with password `LibreKast`.

Then create a secure secret key:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; \
            print(get_random_secret_key())'
export SECRET_KEY="<your secret key>"
```

**5. Collect Static files needed**

```bash
python manage.py collectstatic
```

**6. Run Redis in a docker container**

check [here](https://www.docker.com/get-started) if you need to install docker.

```bash
docker run -p 6379:6379 -d redis:5
```

**7. Setup env variables**


```bash
export ALLOWED_HOSTS_LOCAL="<the url you plan to serve the app to>"
export DJANGO_SETTINGS_MODULE="pollsite.settings"

# only if this is for debugging
export DEBUG=True
# is your server does not have a valid certificate (some browser will throw errors if this is not enforced)
# this removes secure web socket and secure cookies
export DISABLE_ENCRYPTION=True 
```

**8. now run the server**

```bash
python manage.py runserver
```

> Note that this step runs an ASGI server. If you are used to deploy WSGI server, this involves a few differences !! Especially when dealing with sockets, be sure to install `uvicorn[standard]` and not `uvicorn` to deal with these.

Go to http://127.0.0.1:8000/. This is where Django starts server by default

**Enjoy**

Click on Admin button on top right corner to go the the Django Administration page.
You can add meetings, change or add questions and choices etc.


## How to deploy in production

In order to setup LibreKast in an deployment envionment, one needs to :

 1. setup a web server (such as Apache or Nginx), 
 2. setup an ASGI server for delivering a django app 
   * *please note that you have to redirect not only HTTP, but also websockets !*
 3. clone the repository to start the app. 
 4. _By defaults, all environments variables are setup for prod_, but you should setup some more variables :  : 
	 * `SECRET_KEY` : generate a secure key with the following code : 
		```bash
		 python -c 'from django.core.management.utils import get_random_secret_key; \
            print(get_random_secret_key())'
		 export SECRET_KEY="<your secret key>"
		```
	 * `ALLOWED_HOSTS_LOCAL` : add your server IP/hostname. I recommend setting up a dedicated subdomain (such as _librekast.domainname.com_)
	 * `TWITCH_CLIENT_ID` : generate a client ID for the account you are using to fetch the chat. this can be done [in the Twitch console](https://dev.twitch.tv/console)
	 * `TWITCH_CLIENT_SECRET` : this too should be done [in the Twitch console](https://dev.twitch.tv/console)
	 * `TWITCH_OAUTH_TOKEN` : this should be requested on [Twitch Chat OAuth Password Generator](https://twitchapps.com/tmi/) and grants authorization to use the account for LibreKast.
	 * `NGINX_PROXY` : it's a good practice to have an nginx reverse proxy adding `X-Forwarded-Proto` headers. if you do, it's better to setup this var to `True`
	 * `DJANGO_SETTINGS_MODULE=pollsite.settings` because why not
	 * add your server IP/hostname to the `ALLOWED_HOSTS` 
 5. create a superuser and remove the default user (or change its password)
 6. collect static files and migrate them in the server static folder
 	 * it is a good practice to serve **static files** and **media files** separately using your end server (such as nginx reverse proxy)
 7. start the ASGI server
	 * you may need to export `DJANGO_SETTINGS_MODULE` or other env variables in the command running the server

With Gunicorn/uvicorn, the last step is the following : 

```bash
export DJANGO_SETTINGS_MODULE=pollsite.settings
gunicorn pollsite.asgi -b 127.0.0.1:8010 -w 2 -k uvicorn.workers.UvicornWorker --chdir ./pollsite/ -e DJANGO_SETTINGS_MODULE=pollsite.settings --log-file librekast.log
```

> lmk if you need my redirection setup for nginx or a docker image
 
## Current State diagram 

based on current implem (not the final goal)

```
CLIENT                                      SERVER                          GROUP
  |                                           |                               |
  |          --> question-start -->           |                               |
  |                                    get current question                   |
  |                                           |                               |
  |          <-- question-ready <--           |                               |
showWait                                      |                               |
  |                                           or                              |
  |             <-- question-go <--           |                               |
 if Poll/Quizz :                              |                               |
 showQuestion                                 |                               |
  |                                           |                               |
  |          --> vote -->                     |                               |
  |                <-- voted <--              |                               |
  |                                         if Poll :                         |
  |                <-- results <--            |   --> notify-update-poll -->  |
showResultsPoll                               |                           updatePoll
  |                                           |                               |
  |                                        end : results                      |   
  |                <-- results <--            |    --> results -->            |
  |                                           |                               |
  |                                     end : close                           | 
  |                                           |    --> question-close -->     | 
  |                                           |                               |
 if Word Cloud :                              |                               |
 showWordCloud                                |                               |
  |          --> word-cloud-add -->           |                               |
  |                                        add vote                           |
  |                                           |   --> notify-update-cloud-->  |
  |                                           |                          updateWordCloud
  |                                           |                               |
  |                                        end : close                        |   
  |                                           |    --> question-close -->     | 
  |                                           |                             showWait
  |                                           |                               |
  |                                           if                              |
  |                                           |    --> next-question -->      | 
  |                                           |                             showWait
  |                                           |                               |
  |                                           |                               |
 wait for score                               |                               |
  |            --> get-score  -->             |                               |
  |           <-- update-score <--            |                               |
updateScore                                   |                               |
  |                                           |                               |
```
