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
 * Twitch live Stream : currently under development

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

## Project state

V1 : 

 * [x] home as django models (for non-technical people)
 * [x] back : sync notificaton from admin 
 * [x] back : admin widget for handling question go 
 * [x] back : reward_fastest
 * [x] front : showWait() reset front
 * [x] front : sync previous question
 * [x] front : bug with polls appearance
 * [x] front : widgets un dashboard
 * [x] Youtube : fetch live streams chat
 * [x] Youtube : poll with chat
 * [x] Youtube : word cloud with chat
 * [x] Youtube : meeting ID instead of URL
 * [x] Youtube : change attendee mangement to be function-oriented instead of object-oriented
 * [x] pie chart at the end of the poll
 * [x] front & back : have dashboard showing pie chart during the vote
 * [x] Youtube : add sponsor attribute in scoreboard
 * [ ] BUG : solve issue with votes counted 3 times ??
 * [ ] BUG : solve error in transition from YT WC to YT poll in prod throwing n exception 

V2 : 

 * [x] FR translation templates
 * [x] FR translation models
 * [x] FR translation JS code
 * [ ] front : change front for a dark mode
 * [ ] front : go back button in dashboard
 * [ ] back: join during a question
 * [ ] Image slides
 * [ ] Twitch : Twitch
 * [ ] Twitch : add attendee is subscriber attribute in dashboard
 * [ ] refactor : make question object-oriented in consumers

 V3 : 

 * [ ] docker wrapping
 * [ ] Youtube : automatically generate short answer for poll & quizz

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
export DISABLE_SOCKET_ENCRYPTION=True 
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
 4. In pollsite/settings.py : 
   * change the default `SECRET_KEY` in settings
   * add a `STATIC_ROOT` variable with the **absolute path for the static files your server is serving**
   * setup `DEBUG = False` 
   * add your server IP/hostname to the `ALLOWED_HOSTS` 
 5. create a superuser and remove the default user (or change its password)
 6. collect static files and migrate them in the server static folder
 7. start the ASGI server
   * *you may need to export `DJANGO_SETTINGS_MODULE`*

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
