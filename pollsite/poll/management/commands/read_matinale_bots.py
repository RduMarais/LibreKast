#!/bin/python

import sqlite3
import datetime
import os

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from poll.management.commands._md_parsing import Actu, Heading, MarkdownParsing
from poll.models import Meeting, MessageBot, PeriodicBot
from pprint import pprint

# ARCHI de la DB
# "id" integer
# "title" varchar
# "slug" varchar
# "status" integer
# "start_publication" datetime
# "end_publication" datetime
# "creation_date" datetime
# "last_update" datetime
# "content" text
# "comment_enabled" bool
# "pingback_enabled" bool
# "trackback_enabled" bool
# "comment_count" integer
# "pingback_count" integer
# "trackback_count" integer
# "excerpt" text
# "image" varchar
# "featured" bool
# "tags" varchar
# "login_required" bool
# "password" varchar
# "content_template" varchar
# "detail_template" varchar
# "image_caption" text
# "lead" text
# "publication_date" datetime

# query 
# cursor.execute("SELECT * FROM zinnia_entry WHERE creation_date LIKE '2022-02-26%'")
# récupère les résultats
# res_list = rows.fetchall()

DB_TEST = "../../refonte_pour_info_no_sync/pourinfo/db.sqlite3"
DB_PROD = "../../pour-info.tech/pourinfo/db.sqlite3"
BOT_TEXT_LIMIT = 600
BLOG_URL = "https://pour-info.tech/blog/"

CATEGORIES = [
	{'nom':'La UNE',								'cmd':'une',			'bot':'la UNE de cette semaine'				},
	{'nom':'Attaques et Piratages',					'cmd':'attaques',		'bot':'les attaques cette semaine'			},
	{'nom':'Annonces',								'cmd':'annonces',		'bot':'les annonces cette semaine'			},
	{'nom':'Géopolitique',							'cmd':'géopo',			'bot':'la géopolitique cette semaine'		},
	{'nom':'Threat Intel',							'cmd':'cti',			'bot':'les actus threat intel'				},
	{'nom':'Data Sécu',								'cmd':'secu',			'bot':'protection des données cette semaine'},
	{'nom':'Vulnérabilités',						'cmd':'vulns',			'bot':'les vulnérabilités cette semaine'	},
	{'nom':'Data Leak',								'cmd':'dataleak',		'bot':'les fuites de données cette semaine' },
	{'nom':'Des échanges de cryptoactifs piratés ?','cmd':'cryptos',		'bot':'des crypto échanges piratéés ?'		},
	{'nom':'Les Outils',							'cmd':'outils',			'bot':'les outils dont on peut parler'		},
	{'nom':'Les Articles',							'cmd':'articles',		'bot':'les articles dont on peut parler' 	}
	]

class Command(BaseCommand):
	help = "Test with video list (--date YYYY-MM-DD --db-path '../../db.sqlite3')"
	verbosity = 0

	def add_arguments(self, parser):
		yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
		date_article = yesterday.strftime("%Y-%m-%d")
		debug_env = os.getenv('DEBUG', default=False)
		if(debug_env):
			default_db_path = DB_TEST
			default_meeting = 'Test Twitch'
		else:
			default_db_path = DB_PROD
			default_meeting = 'Matinale cyber'
		parser.add_argument("--db-path", type=str,default=default_db_path)
		parser.add_argument("--meeting", type=str,default=default_meeting)
		parser.add_argument("--date", type=str,default=date_article,help="date in format YYYY-MM-DD")
		parser.add_argument("--reset", action='store_true')
		# parser.add_argument("--verbose", type=bool,default=False)

	def fetch_source_markdown(self,db_path,date_str):
		connection = sqlite3.connect(db_path)
		if(self.verbosity>1): print('- connected')
		cursor = connection.cursor()
		rows = cursor.execute(f"SELECT content,slug,lead FROM zinnia_entry WHERE creation_date LIKE '{date_str}%'")
		# if(self.verbosity>2):
		# 	for row in rows:
		# 		print(f'row : {row}')
		a = rows.fetchone()
		if(self.verbosity > 2):
			print(a)
			print(type(a))
			print(type(a[0]))
			print(type(a[1]))
			print(type(rows))
		return a

	def define_bots(self,meeting,actus):
		for h in actus.headings:
			is_categorie = any(c['nom'] == h.title for c in CATEGORIES)
			if(is_categorie):
				categorie = next(c for c in CATEGORIES if c['nom'] == h.title)
				print(f'### {h.title} (categ found !)')
				# find bot
				bots_candidates = list(meeting.messagebot_set.filter(command=categorie['cmd']))
				bots_candidates += list(meeting.periodicbot_set.filter(name=categorie['cmd']))
				print(bots_candidates)
				bot_text = categorie['bot'] + ' : '
				for a in h.news_list:
					if(len(bot_text)+len(a.text) >= BOT_TEXT_LIMIT):
						bot_text += a.text+' // '
				for bot in bots_candidates:
					if (self.verbosity > 1):
						print('- bot found and set up')
					bot.message = bot_text[:-4]
				bot.save()
				if (self.verbosity > 1):
					print(f'- bot {bot} saved ')
			else:
				print(f'### {h.title} (NOT found)')
	
	# A TESTER
	def define_sources(self,meeting,slug):
		print(f'- defining date :{slug}')
		if(meeting.messagebot_set.filter(command='sources')):
			bot_src = meeting.messagebot_set.filter(command='sources')[0]
			bot_src.message = f'les sources de la matinale : {BLOG_URL}{slug}/'
			bot_src.save()
		if(meeting.periodicbot_set.filter(name='sources')):
			bot_src = meeting.periodicbot_set.filter(name='sources')[0]
			bot_src.message = f'les sources de la matinale : {BLOG_URL}{slug}/'
			bot_src.save()

	def define_dates(self,meeting):
		if(self.verbosity>1): print('- time reset')
		today_iso_str = timezone.now().strftime("%Y-%m-%d")
		time_start_iso_str = ' 07:00:00+02:00'
		time_end_iso_str = ' 12:00:00+02:00'
		meeting.date_start = timezone.datetime.fromisoformat(today_iso_str + time_start_iso_str)
		meeting.date_end = timezone.datetime.fromisoformat(today_iso_str + time_end_iso_str)
		meeting.save()
		if(self.verbosity>2): print(f'  -> start time {meeting.date_start}')
		if(self.verbosity>2): print(f'  -> end time {meeting.date_end}')

	def reset_bots(self):
		if(self.verbosity>1): print('- reset')
		for bot in [MessageBot.objects.get(pk=4),MessageBot.objects.get(pk=5),PeriodicBot.objects.get(pk=4)]:
			bot.message = 'BLABLBALBALBALA'
			bot.save()

	def handle(self, *args, **options):
		if(options['reset']):
			self.reset_bots()
			self.style.SUCCESS('Bot reset')
			return
		self.verbosity = options['verbosity']
		source_markdown = None
		if(self.verbosity>1): print('- start')
		if(self.verbosity>2): print(options)
		try:
			source_markdown = self.fetch_source_markdown(options['db_path'],options['date'])
		except Exception as e:
			self.stdout.write(self.style.ERROR('Error in fetching data'))
			if(self.verbosity>2):
				raise e
			else:
				return
		if(self.verbosity>1): print('- source markdown fetched')
		if(self.verbosity >2): print(source_markdown)
		if(self.verbosity >2): print(type(source_markdown[0]))
		debug = self.verbosity>2
		actus = MarkdownParsing(debug=debug)
		actus.read_text(source_markdown[0]) # pass the content key
		# # test
		# pprint(actus.tokens[:15])
		actus.parse_bullet_points()
		if(self.verbosity > 0):
			print("Properties : ")
			for prop in actus.headings[0].properties:
				print(" - "+prop['type']+' : '+prop['value'])
		# this should be the summary already
		meetings = Meeting.objects.filter(title=options['meeting'])
		if(not meetings): 
			self.stdout.write(self.style.ERROR('Error no meeting found'))
			return
		self.define_dates(meetings[0])
		self.define_bots(meetings[0],actus)
		self.define_sources(meetings[0],source_markdown[1])
		self.stdout.write(self.style.SUCCESS('Successfully executed'))

# fetch_source_markdown(DB_TEST,'2022-02-26')

# TODO 

#  * [x] Parse markdown string
#  * [ ] Connect to models and add bots
#  * [x] Prepare bot text
#  * [x] Match categories and headings

