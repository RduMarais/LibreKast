from pprint import pprint
from markdown_it import MarkdownIt
from mdformat.renderer import MDRenderer

class Heading:
	# headings = [{'id':0,'heading':'INTRO','news_list':[]}]
	def __init__(self,heading_id,title,news_list):
		self.heading_id = heading_id
		self.title = title
		self.news_list = news_list
		self.size = 0
		self.properties = []

	def __str__(self):
		return self.title+' ('+str(self.size)+')'

	def __repr__(self):
		return self.title+' ('+str(self.size)+')'

	def compute_size(self):
		self.size = len(self.news_list)

	def append_actu(self,actu):
		self.news_list.append(actu)
		self.size +=1

	def set_property(self,key,value):
		prop = {'type':key,'value':value}
		self.properties.append(prop)


class Actu:
	# actu = {'id':self.actu_count,'text':news_text,'links':news_links,'category':self.heading_text}
	def __init__(self,actu_id,text,links,category):
		self.id = actu_id
		self.text = text
		self.links = links
		self.category = category
		self.summary = None
		self.sub_actus = None

	def __str__(self):
		if(self.summary): 
			return self.summary
		else:
			return self.text[0:50]

	def __repr__(self):
		if(self.summary): 
			return self.summary
		else:
			return self.text[0:50]

	def get_sub_actus(self):
		return self.sub_actus

	def add_sub_actu(self,sub_actu):
		if(self.sub_actus):
			self.sub_actus.append(sub_actu)
		else:
			self.sub_actus = [sub_actu]

class MarkdownParsing:
	def __init__(self,debug=False):
		self.debug = debug
		intro = Heading(0,'INTRO',[])
		self.headings = [intro]
		self.index = 0
		self.heading_id = 0 # for heading creation
		self.heading_text = ''
		self.ongoing_category = self.headings[0]
		self.actu_count = 0
		self.tokens = []

	def print_headings(self):
		print('\nHeadings :')
		for h in self.headings:
			print(' - '+str(h))
			for actu in h.news_list:
				print('    * '+str(actu.id)+' : '+actu.category+' || '+actu.text[0:20])

	def get_test_summary(self,actu):
		return '(temp) ' + actu.text[0:50]


	def get_list_item_content(self, index):
		news_text = ''
		news_links = []
		if(not self.tokens[index].children):
			return 
		for child in self.tokens[index].children: #body # self.index+2 is inline
			if(child.type == 'text'):
				news_text += child.content
			# self.index += 2
			if(child.type == 'link_open'):
				news_links.append(child.attrs['href'])
		return news_text,news_links

	def parse_bullet_points(self):
		while self.index < len(self.tokens):
			token = self.tokens[self.index]
			
			# handle headings
			if(token.type == 'heading_open' and token.tag == 'h3'):
				a = self.tokens[self.index+1]
				# if(self.debug): pprint(a)
				self.heading_text = ''
				for child in a.children: #choper tous les enfants de type text
					if(child.type == 'text'):
						self.heading_text += child.content
				already_listed = any(h.title == self.heading_text for h in self.headings)

				if(not already_listed): # this is a new heading
					if(self.debug): print('fin de categ '+self.ongoing_category.title)
					if(self.debug): print('debut de '+self.heading_text+' (non créée)')
					# on cloture la categorie précédente
					self.ongoing_category.compute_size()
					# on crée une nouvelle categorie
					self.heading_id += 1
					self.ongoing_category = Heading(heading_id=self.heading_id,title=self.heading_text,news_list=[])
					# self.ongoing_category = {'id':self.heading_id,'heading':self.heading_text,'news_list':[]}
					self.headings.append(self.ongoing_category)
				else:
					if(self.debug): print('fin de categ '+self.ongoing_category.title)
					if(self.debug): print('début de '+self.heading_text+' (existante)')
					# on cloture la categorie précédente
					self.ongoing_category.compute_size()
					# on trouve la categorie et on la sélectionne
					self.ongoing_category = next(h for h in self.headings if h.title == self.heading_text)

			# handle items
			if(token.type == 'list_item_open'):
				if(self.tokens[self.index+1].type != 'paragraph_open'):
					print('[!] Error in index browsing : no list_item_open > paragraph_open')
				if(self.tokens[self.index+2].type != 'inline'):
					print('[!] Error in index browsing : no list_item_open > paragraph_open > inline')
				

				if(self.get_list_item_content(self.index+2)):
					news_text,news_links = self.get_list_item_content(self.index+2)
				else:
					break
				self.actu_count += 1
				actu = Actu(actu_id = self.actu_count,text=news_text,links=news_links,category=self.heading_text)

				if(self.tokens[self.index+4].type=='bullet_list_open'):
					if(self.debug) : print(news_text[0:20]+' -> sub bullet list à traiter')
					self.index = self.index + 10
					sub_actus = []
					if(self.tokens[self.index].type == 'list_item_open'):
						while(self.tokens[self.index].type == 'list_item_open'):
							sub_news_text,sub_news_links = self.get_list_item_content(self.index+2)
							sub_actu = {'text':sub_news_text,'links':sub_news_links}
							if(self.debug) : print(' - sub new : '+sub_news_text[0:20])
							# sub_actus.append(sub_actu)
							actu.add_sub_actu(sub_actu)
							self.index = self.index + 5
					# actu['sub_actus'] = sub_actus
				if(self.tokens[self.index+4].type=='list_item_close'):
					if(self.debug) : print(news_text[0:20]+' -> news done')

				self.ongoing_category.append_actu(actu)

			# handle options in html comms
			if(token.type == 'html_block'):
				if(token.content.startswith('<!--') and token.content.endswith('-->\n')):
					prop_type = token.content[4:-4].split(': ')[0]
					prop_value = token.content[4:-4].split(': ')[1]
					# a = {'type':a_type,'value':a_value}
					self.ongoing_category.set_property(prop_type,prop_value)
					if(self.debug): print(f' --- property : {prop_type} set to {prop_value}')

			self.index = self.index+1 # main iterator

		self.ongoing_category.compute_size()

	def read_file(self,date_str,filename='sources_rsb.md'):
		with open(date_str+'/'+filename,'r') as filein:
			source_markdown = filein.read()
			self.read_text(source_markdown)

	def read_text(self,source_str):
		md = MarkdownIt("commonmark")
		tokens = md.parse(source_str)
		self.tokens = tokens

	def get_test_summary(self,actu):
		return '(temp) ' + actu.text[0:50]

	# parcours en O(n) en rab mais why not
	def fetch_summaries(self):
		for heading in self.headings:
			for actu in heading.news_list:
				actu.summary = self.get_test_summary(actu)

	def write_output(self,date_str):
		output_str = f"# Sources pour la matinale cyber du {date_str}\n"
		# headings = [{'id':0,'heading':'INTRO','news_list':[]}]
		# actu = {'id':self.actu_count,'text':news_text,'links':news_links,'category':self.heading_text}
		for heading in self.headings:
			output_str += '\n### '+heading.title +'\n\n'
			for actu in heading.news_list:
				if(actu.links):
					output_str += ' * ['+ actu.summary+']('+actu.links[0]+')\n'
				else:
					output_str += ' * '+ actu.summary+'\n'

				# what if sub_actus
				# what if différents links
		return output_str
