#!/usr/local/bin/python3

import re
import math
#import sys

from collections import namedtuple

import pprint

pp = pprint.PrettyPrinter(indent=4)

def get_affinity(irq):
	fn = "/proc/irq/{}/smp_affinity".format(irq)
	with open(fn) as ifs:
		ln = ifs.readline().strip().split(',')
	bitmap = ''.join(ln)
	n = 0
	cpus = []
	for c in reversed(bitmap):
		x = int(c, 16)
		mask = 1
		for i in range(0, 4):
			if x & mask:
				cpus.append(n)
			n += 1
			mask <<= 1
	return cpus

def load_tab(scale):
	fret = 0
	tab = [ 0, 0, 0, 0, 0, 0]
	fn = "tabs/{}.txt".format(scale)
	with open(fn) as ifs:
		fsm = 0
		rows = ifs.readlines()
		for row in rows:
			x = row.strip()
			if not x: continue
			if x.startswith("#"): continue
			if fsm == 0:
				if x == "======":
					fsm = 1
			elif fsm == 1:
				if re.match("^[-*]{6}$", x):
					fret = fret + 1
					for i, ch in enumerate(x[::-1]):
						if ch == "*":
							tab[i] = fret
#						print("c: ", ch, " i: ", i)
#					print("x: ", x)
				else:
					print("no match")
	return tab

def tab_cache():
	cache = {}
	def lookup(scale):
#		pp.pprint(cache)
		if scale in cache:
			return cache[scale]
		tab = load_tab(scale)
		cache[scale] = tab
		return tab
	return lookup

def load_tune(tn):
	fn = "tunes/{}.txt".format(tn)
	tune = [ 60, 60, 60, 60, 60, 60 ]
	string = 0
	with open(fn) as ifs:
		rows = ifs.readlines()
		for row in rows:
			x = row.strip()
			if not x: continue
			if x.startswith("#"): continue
			tune[string] = int(x)
			string = string + 1
			if string > 5:
				return tune
	return tune

def load_pattern(pn, scale):
	fn = "patterns/{}/{}.txt".format(pn, scale)
	bars = []
	extra = {}
	nbars = 0
	string = 0
	with open(fn) as ifs:
		fsm = 0
		rows = ifs.readlines()
		for row in rows:
			x = row.strip()
			if not x: continue
			if x.startswith("#"): continue
			if x.startswith("!"):
				m = re.match("^!([^=]+)=(.*)$", x)
				if m:
					extra[m.group(1)] = m.group(2)
			if not re.match("^[|]([-*0-9]+[|])+$", x): continue
			l = x.split('|')[1:-1]
			n = len(l)
#			pp.pprint(l)
			if fsm == 0:
				fsm = 1
				nbars = n
				for i in range(n):
					bars.append([])
			elif fsm == 1:
				if n != nbars:
					return None
			for i in range(n):
				bars[i].append(list(l[i]))
			string = string + 1
			if string > 5:
				return split_pattern(bars, extra)
	return split_pattern(bars, extra)

def split_pattern(ibars, extra):
	Slot = namedtuple('Slot', ['span', 'chord'])
	BarSlots = namedtuple('BarSlots', ['span', 'slots', 'extra'])
	obars = []
	for bar in ibars:
		fsm = 0
		width = 0
		height = len(bar)
		for row in bar:
			n = len(row)
			if fsm == 0:
				fsm = 1
				width = n
			elif fsm == 1:
				if n != width:
					return None
		span = 1
		bspan = 0
		tip = None
		slots = []
		for w in range(width):
			chord = []
			for string in range(height):
				if bar[string][w] != '-':
					chord.append(string)
#			pp.pprint(voices)
			if len(chord) > 0:
				if tip is not None:
					slots.append(Slot(span, tip))
					bspan = bspan + span
				tip = chord
				span = 1
			else:
				span = span + 1
		if tip is not None:
			slots.append(Slot(span, tip))
			bspan = bspan + span
#		pp.pprint(events)
		obars.append(BarSlots(bspan, slots, extra))
#	pp.pprint(obars)
#		n = len(bar)
#		print('n: ', n)
#		pp.pprint(bar)
	return obars
#	return None

def pattern_cache():
	cache = {}
	def lookup(pn, scale):
#		pp.pprint(cache)
		key = "{}:{}".format(pn, scale)
		if key in cache:
			return cache[key]
		pattern = load_pattern(pn, scale)
		cache[key] = pattern
		return pattern
	return lookup

def is_multiple(x, spans):
	for y in spans:
		if x != math.gcd(x, y):
			return False
	return True

def xlate_pattern(ibars, tab, frets, codes):
	obars = []
	for bar in ibars:
#		slots = len(bar.slots)
		spans = map(lambda x: x.span, bar.slots)
		q = min(spans)
		if 'beats' in bar.extra:
			beats = int(bar.extra['beats'])
		else:
			beats = int(bar.span / q)
		if beats >= len(bar.slots):
			if is_multiple(q, spans):
#				print('is_multiple')
#				x = xlate_voice(q, bar.slots, tab, frets, codes)
#				pp.pprint(x)
				obars.append(xlate_voice(q, bar.slots, tab, frets, codes))
			else:
				print('!is_multiple')
#			pp.pprint(q)
#		beats = bar.span / min(list(map(lambda x: x.span, bar.slots)))
#		pp.pprint(l)
#		pp.pprint(beats)
	return obars

def octave_shift(i, j):
	if j > i:
		return '>'*(j-i)
	elif i > j:
		return '<'*(i-j)
	return ''

def xlate_voice(q, slots, tab, frets, codes):
	voice = []
	octave = 4
	voice.append("o{}".format(octave))
	for slot in slots:
		rests = int(slot.span / q) - 1
		chord = []
		for string in slot.chord:
			fret = tab[string]
			code = frets[string][fret]
			note = codes[code]
			chord.append("{}{}".format(octave_shift(octave, note.octave), note.shrp))
			octave = note.octave
		voice.append('/'.join(chord))
		for i in range(rests):
			voice.append('r')
	return ' '.join(voice)

def make_code_notes():
	'''
	https://studiocode.dev/resources/midi-middle-c/

	'''
	shrp = [ 'c', 'c+', 'd', 'd+', 'e', 'f', 'f+', 'g', 'g+', 'a', 'a+', 'b' ]
	flat = [ 'c', 'd-', 'd', 'e-', 'e', 'f', 'g-', 'g', 'a-', 'a', 'b-', 'b' ]
	octave = 0
	ip = 9
	op = 21
	lut = {}
	Note = namedtuple('Note', ['octave', 'shrp', 'flat'])
	for k in range(88):
		lut[op] = Note(octave, shrp[ip], flat[ip])
		op = op + 1
		ip = ip + 1
		if ip > 11:
			ip = 0
			octave = octave + 1
	return lut

def make_fret_codes(tune, nfrets = 12):
	lut = []
	for string in range(6):
		x = []
		base = tune[string]
		for i in range(nfrets + 1):
			x.append(base + i)
		lut.append(x)
	return lut

#def pretty_tab(scale):
#	itab = load_tab(scale)

def main():
#	t1 = load_tab('Am')
#	pp.pprint(t1)
#	x = make_midi_note_lut()
#	pp.pprint(x)
	codes = make_code_notes()

	tune = load_tune('EADGBE')
#	x = make_fret_note_lut(tune)
#	pp.pprint(x)
	frets = make_fret_codes(tune)

	tabs = tab_cache()
#	x = tabs('Am')
#	pp.pprint(x)
#	x = tabs('Dm')
#	pp.pprint(x)
#	x = tabs('C')
#	pp.pprint(x)

	patterns = pattern_cache()

#	x = load_pattern('p1', scale)
#	pp.pprint(x)

#	scale = 'Am'
#	p1 = patterns('p1', scale)
#	x = xlate_pattern(p1, tabs(scale), frets, codes)
#	print(' | '.join(x))

#	scale = 'G'
#	p1 = patterns('p1', scale)
#	x = xlate_pattern(p1, tabs(scale), frets, codes)
#	print(' | '.join(x))

	pattern = 'p1'
	scales = [ 'Am', 'Dm', 'E', 'Am', 'Am', 'Dm', 'E', 'Am', 'A7', 'Dm', 'G', 'C', 'Am', 'Dm', 'E', 'Am' ]
	for scale in scales:
		p = patterns(pattern, scale)
		x = xlate_pattern(p, tabs(scale), frets, codes)
		print(' ', ' | '.join(x))

#	scale = 'G'
#	x = patterns('p1', scale)
#	pp.pprint(x)

	return

if __name__ == '__main__':
	main()
