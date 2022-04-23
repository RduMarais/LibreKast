#!/bin/sh

echo "\n### 1. creating virtual environment ###\n"
mkdir ./env
source ./env/bin/activate

echo "\n### 2. installing needed packages ###\n"
pip install -r ./requirements.txt

echo "\n### 3. setting up environment variables ###\n"
SECRET_KEY=`python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`

touch ./librekast.log

echo -n "Please enter the hostname :"
read filename
export ALLOWED_HOSTS_LOCAL=$filename

echo "\n### 4. creating database ###\n"
python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser

echo "\n### 5. Starting REDIS ###\n"
docker run -p 6379:6379 -d redis:5

echo "\n### 6. Checking that everything is allright ###\n"
python manage.py test


echo -n "\nEverything is ready! You can run the server with the following commands : "
echo -n "source ./env/bin/activate"
echo -n "gunicorn pollsite.asgi -b 127.0.0.1:8000 -w 2 -k uvicorn.workers.UvicornWorker --chdir ./pollsite/ -e DJANGO_SETTINGS_MODULE=pollsite.settings --log-file librekast.log -e -SECRET_KEY=$SECRET_KEY -e ALLOWED_HOSTS_LOCAL=$filename"
echo -n "source ./env/bin/activate" > ./start.sh
echo -n "gunicorn pollsite.asgi -b 127.0.0.1:8000 -w 2 -k uvicorn.workers.UvicornWorker --chdir ./pollsite/ -e DJANGO_SETTINGS_MODULE=pollsite.settings --log-file librekast.log -e -SECRET_KEY=$SECRET_KEY -e ALLOWED_HOSTS_LOCAL=$filename &" >> ./start.sh

echo -n "you may set additional properties with the following env variables :\n- DEBUG\n- ADMIN_URL\n- SHOW_ADMIN\n- DISABLE_ENCRYPTION\n"