# LibreKast

**A nice and free web app to gamify and animate your meetings, build with django channels and anychart free.**

I am not a developper, so this code is far from perfect ! Although it runs, please bear in mind that the design of LibreKast is driven by what I managed to do, and not really what I planned to do (in terms of design).

[![GitHub license](https://img.shields.io/github/license/RduMarais/LibreKast)](https://github.com/RduMarais/LibreKast/blob/master/LICENSE)


## Functionnalities

There are 4 types of question you can show in the app : 

 * text-only
 * word cloud : displays a chart with all submitted words
 * poll : asks a question. on question close, shows the number of votes each choice got.
 * Quizz : asks a question. One of the answers is marked as 'correct', all attendants that chose the correct answer receive 1 point, the first one to answer receives an additionnal point.

The meeting organizer can access a special dashboard with live scoreboard, live results and buttons to navigate between questions.

You can connect in the admin interface with user : `defaultsuperuser` and password `LibreKast`

## Project state

 * `channels` branch
	 * [ ] front : showWait() reset front
	 * [ ] front : show previous question
	 * [ ] back : sync notificaton from admin 
	 * [ ] back : admin widget for handling question go 
		 * https://stackoverflow.com/questions/17919361/how-can-i-add-a-button-into-django-admin-change-list-view-page
		 * or define a view with `from django.contrib.admin.views.decorators import staff_member_required` into `@staff_member_required`
		 * ideally dashboard with : 
			 * scoreboard
			 * question list and button Next, previous, stop, results
			 * show results in real-time
	 * [ ] some failsafes in front end
 * [ ] TUTO deployment & customization
 * [ ] testing
 * [x] home as django models (for non-technical people)
 * [ ] FR translation
 * [ ] docker wrapping
 * [ ] django app wrapping
 * [ ] dark mode with tailwind CSS

## Current State diagram 

based on current implem (not the final goal)

```
CLIENT									 SERVER						   GROUP
  |										   |							   |
  |		  --> question-start -->		   |							   |
  |									get current question				   |
  |			 <-- question-go <--		   |							   |
 if Poll/Quizz :							  |							   |
 showQuestion								 |							   |
  |										   |							   |
  |		  --> vote -->					 |							   |
  |				<-- voted <--			  |							   |
  |										 if Poll :						 |
  |				<-- results <--			|   --> notify-update-poll -->  |
showResultsPoll							   |						   updatePoll
  |										end : results					  |   TODO
  |				<-- results <--			|	--> results -->			|
  |										   |							   |
  |									 end : close						   | TODO
  |										   |	--> question-close -->	 | TODO
  |										   |							   |
 if Word Cloud :							  |							   |
 showWordCloud								|							   |
  |		  --> word-cloud-add -->		   |							   |
  |										add vote						   |
  |										   |   --> notify-update-cloud-->  |
  |										end : close						|   TODO
  |										   |	--> question-close -->	 | TODO
  |										   |							   |
  |										   |							   |
  wait for results							|							   |
  |		  --> debug-results  -->		   |							   |
  |				<-- results <--			|							   |
  |										   |							   |
 wait for score							   |							   |
  |		  --> debug-score  -->			 |							   |
  |		   <-- update-score <--			|							   |
  |										   |							   |
```

## How to run on your computer

__pre-requisites : python(3.8 or above) and pip must be installed__ 



**0. create and activate a virtual environment inside a new directory**

It is highly recommended to use virtual environments when yout set up a new project. If you are new to virtual environments read [python-3 official docs](https://docs.python.org/3/library/venv.html) 

**1. clone this repo `django-polling-site` in your directory**

```
git clone https://github.com/RduMarais/LibreKast.git
```

**2. install the requirements**

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

> Note that this step runs an ASGI server. If you are used to deploy WSGI server, this involves a few differences !!

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
 6. create a superuser and remove the default user
 7. collect static files and migrate them in the server static folder
 
