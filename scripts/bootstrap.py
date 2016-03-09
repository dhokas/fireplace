#!/usr/bin/env python

import os
import re
import sys; sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from xml.dom import minidom
from xml.etree import ElementTree
from hearthstone.enums import GameTag


def add_hero_power(card, id):
	e = ElementTree.Element("HeroPower")
	e.attrib["cardID"] = id
	card.xml.append(e)
	print("%s: Adding hero power %r" % (card, id))


def create_card(id, tags):
	print("%s: Creating card with %r" % (id, tags))
	e = ElementTree.Element("Entity")
	e.attrib["CardID"] = id
	for tag, value in tags.items():
		e.append(_create_tag(tag, value))
	return e


def _create_tag(tag, value):
	e = ElementTree.Element("Tag")
	if isinstance(value, bool):
		e.attrib["value"] = "1" if value else "0"
		e.attrib["type"] = "Bool"
	elif isinstance(value, int):
		e.attrib["value"] = str(int(value))
		e.attrib["type"] = "Int"
	elif isinstance(value, str):
		e.text = value
		e.attrib["type"] = "String"
	else:
		raise NotImplementedError(value)
	e.attrib["enumID"] = str(int(tag))
	return e


def set_tag(card, tag, value):
	e = _create_tag(tag, value)
	card.xml.append(e)
	print("%s: Setting %r = %r" % (card.name, tag, value))
	return e


def remove_tag(card, tag):
	e = card._find_tag(tag)
	card.xml.remove(e)
	print("%s: Removing %r tag" % (card.name, tag))


def load_dbf(path):
	db = {}
	hero_powers = {}
	guid_lookup = {}
	with open(path, "r") as f:
		xml = ElementTree.parse(f)
		for record in xml.findall("Record"):
			id = int(record.find("./Field[@column='ID']").text)
			long_guid = record.find("./Field[@column='LONG_GUID']").text
			mini_guid = record.find("./Field[@column='NOTE_MINI_GUID']").text
			hero_power_id = int(record.find("./Field[@column='HERO_POWER_ID']").text or 0)

			guid_lookup[long_guid] = mini_guid
			db[id] = mini_guid
			if hero_power_id:
				hero_powers[mini_guid] = hero_power_id

	for k, v in hero_powers.items():
		hero_powers[k] = db[v]

	# Some hero powers are missing from the DBF, wtf :(
	missing = {
		"BRM_027h": "BRM_027p",
		"EX1_323h": "EX1_tk33",
	}

	for k, v in missing.items():
		assert k not in hero_powers
		hero_powers[k] = v

	return guid_lookup, hero_powers


def main():
	from hearthstone.cardxml import load
	from fireplace.utils import _custom_cards, get_script_definition

	if len(sys.argv) < 3:
		print("Usage: %s <in> <out/CardDefs.xml>" % (sys.argv[0]))
		exit(1)

	db, xml = load(os.path.join(sys.argv[1], "CardDefs.xml"))
	guids, hero_powers = load_dbf(os.path.join(sys.argv[1], "DBF", "CARD.xml"))
	for id, card in db.items():
		if id in hero_powers:
			add_hero_power(card, hero_powers[id])

		if "Can't be targeted by spells or Hero Powers." in card.description:
			set_tag(card, GameTag.CANT_BE_TARGETED_BY_ABILITIES, True)
			set_tag(card, GameTag.CANT_BE_TARGETED_BY_HERO_POWERS, True)

		if "50% chance to attack the wrong enemy." in card.description:
			if not card.forgetful and id != "GVG_112":
				set_tag(card, GameTag.FORGETFUL, True)

	# xml = db[next(db.__iter__())].xml
	path = os.path.realpath(sys.argv[2])
	with open(path, "w", encoding="utf8") as f:
		root = ElementTree.Element("CardDefs")
		for e in xml.findall("Entity"):
			# We want to retain the order so we can't just use db.keys()
			id = e.attrib["CardID"]
			card = db[id]
			root.append(card.xml)

		# dummy call
		get_script_definition("")

		# Create all registered custom cards
		for id, cls in _custom_cards.items():
			e = create_card(id, cls.tags)
			root.append(e)

		outstr = ElementTree.tostring(root)
		# Reparse for clean indentation
		outstr = minidom.parseString(outstr).toprettyxml(indent="\t")
		outstr = "\n".join(line for line in outstr.split("\n") if line.strip())
		f.write(outstr)
		print("Written to", path)


if __name__ == "__main__":
	main()
