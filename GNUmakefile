#

nop:

ALDA:=$(shell echo *.alda)

MIDI:=${ALDA:alda=midi}

midi: ${MIDI}

${ALDA}:

%.midi: %.alda GNUmakefile
	cat $< | alda export > $@
