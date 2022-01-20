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

To connect to a meeting, participants only need to go to Meetings > choose the meetings. A meeting code is needed to register, by default it is `Pour1nf0`.

You can connect in the admin interface with user : `defaultsuperuser` and password `LibreKast`. To pass some questions, just mark them as done in the admin panel. Every request gets the next question by fetching the first question in order that has no already be done.

##### Screenshots

![](screenshots/dashboard.png)

You can find screenshots : 

 * [of quizz correction](screenshots/quizz.png)
 * [of home page](screenshots/home.png)

## Project state

 * [x] home as django models (for non-technical people)
 * [x] front : showWait() reset front
 * [x] back : sync notificaton from admin 
 * [x] back : admin widget for handling question go 
 * [x] front : sync previous question
 * [x] front : bug with polls appearance
 * [ ] front : some failsafes in dashboard
 * [ ] testing
 * [ ] FR translation
 * [ ] docker wrapping
 * [ ] join during a question (and a bit of socket security)
 * [ ] dashboard ugly when there are big titles
 * re-test : 
   * [ ] test update score
   * [ ] test when already answered, poll creates 2nd row with results
   * [ ] test previous question
   * pip uvicorn[standard]


## How to run on your computer

__pre-requisites : python(3.8 or above) and pip must be installed__ 



**0. create and activate a virtual environment inside a new directory**

It is highly recommended to use virtual environments when yout set up a new project. If you are new to virtual environments read [python-3 official docs](https://docs.python.org/3/library/venv.html) 

**1. clone this repo `django-polling-site` in your directory**

```
git clone https://github.com/RduMarais/LibreKast.git
```

**2. install the requirements**

The requirements listed are the versions I used to test & develop the app. Feel free to tamper with the versions, just keep in mind that different package versions have not been tested !

```
pip install -r requirements.txt
```

**3. move inside the `pollsite` directory and make migrationS**

```
python manage.py makemigrations home
python manage.py makemigrations poll
python manage.py migrate
```

**4. create a superuser , with your own username and password**

```
python manage.py createsuperuser
```
A default superuser exists, named `defaultsuperuser` with password `LibreKast`.

**5. Collect Static files needed**

```
python manage.py collectstatic
```

**6. Run Redis in a docker container**

check [here](https://www.docker.com/get-started) if you need to install docker.

```
docker run -p 6379:6379 -d redis:5
```

**7. now run the server**

```
python manage.py runserver
```

> Note that this step runs an ASGI server. If you are used to deploy WSGI server, this involves a few differences !! Especially when dealing with sockets, be sure to install `uvicorn[standard]` and not `uvicorn` to deal with these.gti 

Go to http://127.0.0.1:8000/. This is where Django starts server by default

**Enjoy**

Click on Admin button on top right corner to go the the Django Administration page.
You can add meetings, change or add questions and choices etc.


## How to deploy in production

In order to setup LibreKast in an deployment envionment, one needs to :

 1. setup a web server (such as Apache or Nginx), 
 2. setup an ASGI server for delivering a django app 
 3. clone the repository to start the app. 
 4. change the default SECRET_KEY in settings
 5. setup DEBUG = False
 6. create a superuser and remove the default user (or change its password)
 7. collect static files and migrate them in the server static folder

lmk if you need my redirection setup for nginx or a docker image
 
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
