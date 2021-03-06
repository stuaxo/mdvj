import pygame
import pygame.midi
from pygame.locals import *
from mdvj.giantwin32 import * # keypressing stuff
import configparser

class Controller():

	def __init__(self,inp,out,event_get,binds,descs,db,gui,debug=True,twitch=True):
		self.inp = inp
		self.out = out
		self.event_get = event_get
		self.binds = binds
		self.descs = descs
		self.db = db
		self.gui = gui
		self.debug = debug
		self.reset_mode = 0
		self.my_dict = {}
		self.stored_n = {}
		self.stored_diff = {}
		self.ws = []
		self.currgroups = [0,1]
		self.desc_dict = {}
		for i in range(len(binds)):
			self.desc_dict[binds[i]] = descs[i]
		self.lastpad = [-1, -1, -1]
		self.twitch = twitch
		self.setup()

	def setup(self):
		# import config as dictionary
		Config = configparser.RawConfigParser()
		Config.optionxform = str 
		Config.read('vj_config.ini')
		for o in self.binds:
			try:
				v = Config.get('Control',o)
				p = Config.get('SorC',o)
				if p == 'w': 
					self.ws.append(o)
					self.stored_diff[o] = 0
				self.my_dict[v] = [o,p]
				self.stored_n[o] = -1
				
			except:
				if self.debug: print(o,' failed')
		self.start()
	

	## KEYS
	
	def key_parser(self,k,o,n=1,slow=2.5):

		if o == 's': #simple
			if n > 64:
				for _ in range((128-n)):		
					typer(k[0])
			else:
				for _ in range(n):
					typer(k[1])
		elif o == 'c' or o == 'w': #complex or sWiper
			oldn = self.stored_n[k]
			if oldn == -1: 
				self.stored_n[k] = n
			else:
				self.stored_n[k] = n 
				n = n - oldn
				while n > 4 or n < -4:
					n = int(n // slow) + 1
				if o == 'w': 
					self.stored_diff[k] = self.stored_diff[k] - n			
				if n > 0:
					for _ in range(n):
						typer(k[0])
				else:
					for _ in range(-1*n):
						typer(k[1])

		elif o == 'p': #pad
			if n == 127:
				if self.debug: print("set {} pad {}".format(k[0],k[1]))
				preset = self.db[self.currgroups[int(k[0])]][int(k[1])]
				self.lastpad = self.light(k[0],k[1],15,'g')
				self.select_preset(preset)
				for w in self.ws:
					self.stored_diff[w] = 0

	def select_preset(self,preset):
		name = preset.get_name()
		typer('l')
		press('home')
		print(name)
		fast_press('down_arrow',preset.get_n())
		press('enter','esc')

	def advance(self,n):
		if self.currgroups[0] + n >= 0 and self.currgroups[1] + n < len(self.db):
			temp = self.lastpad
			self.light(*temp)
			self.currgroups = [self.currgroups[0]+n, self.currgroups[1]+n]
			self.gui.place_presets(self.db,*self.currgroups)
			#if temp[2] > 0:
			if temp[0] + n == 2:
				self.light(0,temp[1],temp[2])
			elif temp[0] + n == -1:
				self.light(1,temp[1],temp[2])

	def reset(self,k,o,n):
		if o == 'c':
			if self.debug: print('resetting',k)    	
			self.stored_n[k] = -1
		elif o == 'w':
			self.stored_n[k] = 0
			d = self.stored_diff[k]
			if self.debug: print('swiper reset',k,d)
			self.key_parser(k,o,d)
			self.stored_diff[k] = 0
			self.stored_n[k] = -1
		else:
			self.key_parser(k,o,n)

	def light(self,n,m,i=5,rga='r'): # n - set num, m - pad num, i - intensity, rga - color
		if i < 0: i = 0
		elif i > 15: i = 15
		# red add 0
		if rga == 'a': i += 64 # amber
		elif rga == 'g': i += 112 # green
		newpad = [int(n),int(m), i]
		if not self.twitch: return newpad # break if not twitch 
		self.out.write([[[151+newpad[0],60+newpad[1],newpad[2]],pygame.midi.time()]])
		if self.lastpad != [-1, -1, -1] and self.lastpad != newpad:
			self.out.write([[[151+self.lastpad[0],60+self.lastpad[1],0],pygame.midi.time()]])
		return newpad

	def start(self):
		if self.debug:
			for k,v in self.my_dict.items():
				print(k,v)
			#for k,v in self.desc_dict.items():
			#	print(k,v)
		self.gui.place_presets(self.db,*self.currgroups)
		going = True
		
		while going:
		
		        events = self.event_get()
		        for e in events:
		                if e.type in [QUIT]:
		                        going = False
		                elif e.type==VIDEORESIZE:	
		                	self.gui.resize(*e.dict['size'])
		
		        if self.inp.poll():
		                midi_events = self.inp.read(10)
		                the_key = str([midi_events[0][0][0],midi_events[0][0][1]])
		                n = int(midi_events[0][0][2])
		                try:
		                	#if self.debug: print(the_key,n)
		                	self.gui.write_text(self.desc_dict[self.my_dict[the_key][0]],0,0)
		                	if self.my_dict[the_key][1] == 'r': 
		                		if n == 127: self.reset_mode = 1 #(self.reset_mode + 1) % 4
		                		elif n == 0: self.reset_mode = 0
		                	if self.reset_mode != 0:  	
		                		self.reset(self.my_dict[the_key][0],self.my_dict[the_key][1],n)
		                		#self.reset_mode = 0
		                	elif self.my_dict[the_key][1] == 'a' and n == 0: #advance
		                		self.advance(1)
		                	elif self.my_dict[the_key][1] == 'd' and n == 0: #decrease
		                		self.advance(-1)
		                	else: 
		                		self.key_parser(self.my_dict[the_key][0],self.my_dict[the_key][1],n)
		                except:
		                	if self.debug: print(the_key,n)
		
