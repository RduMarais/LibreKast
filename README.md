# LibreKast

**A nice and free web app to gamify and animate your meetings, build with django channels and anychart free.**

> forked from https://github.com/aahnik/django-polling-site
>
> **BE AWARE THAT THERE IS A DEFAULT SUPERUSER CREATED ON THE ORIGINAL PROJECT**



[![GitHub license](https://img.shields.io/github/license/RduMarais/LibreKast)](https://github.com/RduMarais/LibreKast/blob/master/LICENSE)


[**see screenshots**](https://github.com/aahnik/django-polling_site/tree/master/ScreenShots)

## Project state

 * `channels` branch
     * [ ] front : showWait()
     * [x] poll results synchros
     * [x] WC 
     * [ ] front : showWait and show previous question
     * [ ] back : sync notificaton from admin 
     * [ ] back : admin widget for handling question order
     * [ ] some failsafes in front end
 * [ ] TUTO deployment & customization
 * [ ] testing
 * [ ] home as django models (for non-technical people)
 * [ ] FR translation
 * [ ] docker wrapping
 * [ ] django app wrapping
 * [ ] dark mode with tailwind CSS

## (channels branch) State diagram 

based on current implem (not the final goal)
```
CLIENT                                     SERVER                           GROUP
  |                                           |                               |
  |          --> question-start -->           |                               |
  |                                    get current question                   |
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
  |                                           |                               |
 if Word Cloud :                              |                               |
 showWordCloud                                |                               |
  |          --> word-cloud-add -->           |                               |
  |                                        add vote                           |
  |                                           |   --> notify-update-cloud-->  |
  |                                           |                               |
  |                                           |                               |
  wait for results                            |                               |
  |          --> debug-results  -->           |                               |
  |                <-- results <--            |                               |
  |                                           |                               |
 wait for score                               |                               |
  |          --> debug-score  -->             |                               |
  |           <-- update-score <--            |                               |
  |                                           |                               |
```

## How to run on your computer

__pre-requisites : python(3.8 or above) and pip must be installed__ 



**1. create and activate a virtual environment inside a new directory**

if you are new to virtual environments read [python-3 official docs](https://docs.python.org/3/library/venv.html) 

**2. clone this repo `django-polling-site` in your directory, and install the requirements**

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

**5. Collect Static files needed**

```
python manage.py collectstatic
```

**6. Inside the `home` app directory , configure the homePage.yaml according to your wish**
Inside `views.py` of same directory, put the absolute path of homePage.yaml in the place instructed. 

**7. now run the server**

```
python manage.py runserver
```

Go to  http://127.0.0.1:8000/ . This is where Django starts server by default

**HOLA !! ENJOY YOU HAVE SUCCESSFULLY RUN THE SERVER**

Click on Admin button on top right corner to go the the Django Administration page.
You can add team members , change or add questions and choices


*Vist DJANGO'S OFFICIAL WEBSITE FOR MORE DETAILS..*

__you can now play around with the code your self__

