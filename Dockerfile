FROM python:3.9

WORKDIR ./app

COPY . .

RUN mkdir ./venv && python -m venv ./venv && pip install --upgrade pip && pip install -r ./requirements.txt

EXPOSE 8000

ENV VIRTUAL_VEN /env
ENV PATH /env/bin:$PATH


# creates a secret key (how to append)
RUN python -c 'from django.core.management.utils import get_random_secret_key; print("SECRET_KEY="+get_random_secret_key())' >> deploy.env

RUN python ./pollsite/manage.py makemigrations && python ./pollsite/manage.py migrate


CMD ["gunicorn","pollsite.asgi","-b","127.0.0.1:8000","-w","2","-k","uvicorn.workers.UvicornWorker","--chdir","./pollsite/","--log-file","-","-e","DJANGO_SETTINGS_MODULE=pollsite.settings"]