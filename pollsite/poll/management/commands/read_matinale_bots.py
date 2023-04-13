#!/bin/python

from django.core.management.base import BaseCommand, CommandError
import sqlite3
import datetime
import os
from poll.management.commands._md_parsing import Actu, Heading, MarkdownParsing
from poll.models import Meeting, MessageBot, PeriodicBot

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
		parser.add_argument("--date", type=str,default=date_article)
		parser.add_argument("--reset", action='store_true')
		# parser.add_argument("--verbose", type=bool,default=False)

	def fetch_source_markdown(self,db_path,date_str):
		connection = sqlite3.connect(db_path)
		if(self.verbosity>1): print('- connected')
		cursor = connection.cursor()
		rows = cursor.execute(f"SELECT content,slug,lead FROM zinnia_entry WHERE creation_date LIKE '{date_str}%'")
		return rows.fetchone()

	def define_bots(self,meeting,actus):
		for h in actus.headings:
			is_categorie = any(c['nom'] == h.title for c in CATEGORIES)
			if(is_categorie):
				categorie = next(c for c in CATEGORIES if c['nom'] == h.title)
				print(f'### {h.title} (found !)')
				# find bot
				bots_candidates = list(meeting.messagebot_set.filter(command=categorie['cmd']))
				bots_candidates += list(meeting.periodicbot_set.filter(name=categorie['cmd']))
				print(bots_candidates)
				bot_text = categorie['bot'] + ' : '
				for a in h.news_list:
					bot_text += a.text+' // '
				for bot in bots_candidates:
					if (self.verbosity > 1):
						print('- bot found')
					bot.message = bot_text[:-4]
				bot.save()
			else:
				print(f'### {h.title} (NOT found)')

	def define_dates(self,meeting):
		pass

	def reset_bots(self):
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
		# print(source_markdown[0])
		debug = self.verbosity>2
		actus = MarkdownParsing(debug=debug)
		actus.read_text(source_markdown[0]) # pass the content key
		actus.parse_bullet_points()
		# this should be the summary already
		meetings = Meeting.objects.filter(title=options['meeting'])
		if(not meetings): 
			self.stdout.write(self.style.ERROR('Error no meeting found'))
			return
		self.define_dates(meetings[0])
		self.define_bots(meetings[0],actus)
		self.stdout.write(self.style.SUCCESS('Successfully executed'))

# fetch_source_markdown(DB_TEST,'2022-02-26')

# TODO 

#  * [x] Parse markdown string
#  * [ ] Connect to models and add bots
#  * [x] Prepare bot text
#  * [x] Match categories and headings
