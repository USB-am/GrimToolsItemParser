# -*- coding: utf-8 -*-

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as bs

import json


ITEM_TYPES = [
	'helms',
	'shoulders',
	'chest',
	'gloves',
	'belts',
	'pants',
	'boots',
	'swords',
	'axes',
	'maces',
	'daggers',
	'scepters',
	'ranged1h',
	'shields',
	'offhands',
	'swords2h',
	'axes2h',
	'maces2h',
	'ranged2h',
	'rings',
	'amulets',
	'medals',
	'relics',
	'augments'
]
URL = 'https://www.grimtools.com/db/category/{}/items'
URL = 'https://www.grimtools.com/db-mod-gl3/category/{}/items'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.85 YaBrowser/21.11.2.773 Yowser/2.5 Safari/537.36'}

STATUS = 'not browser'
if STATUS == 'browser':
	driver = webdriver.Chrome(ChromeDriverManager().install())
else:
	from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
	options = webdriver.ChromeOptions()
	options.add_argument('headless')
	driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=options)


class ParseInfo:
	__slots__ = ('name', 'func', 'tag')

	def __init__(self, name, func, tag):
		self.name = name
		self.func = func
		self.tag = tag


def __parse_item_param(block, class_name):
	if block[class_name] is None:
		return
	return block[class_name].text


def __parse_wrapper_divs(block, class_name):
	block_with_wrapper_divs = block[class_name]
	if block_with_wrapper_divs is None:
		return

	wrapper_divs = block_with_wrapper_divs.find_all('div')

	# ['Text 1 <span>Text 2</span>'] -> ['Text 2']
	spans = [tag.find('span') if tag.find('span') is not None else tag \
		for tag in wrapper_divs]
	# print(f'Spans: "{type(spans[0].text)}"')

	# ['Text 1 <span>Text 2</span>'] -> [('Text 1', 'Text 2')]
	divs_params_tuple = [tag.text.partition(span.text) \
		for tag, span in zip(wrapper_divs, spans)]

	# [('+1', 'Damage', '')] -> [{'state' : '+1', 'state_name' : 'Damage'}]
	divs_params = [{'state': p1 if p1 else p3, 'state_name': p2} \
		for p1, p2, p3 in divs_params_tuple]

	return divs_params


def __parse_item_color(block, class_name):
	item_color_block = block[class_name]
	if item_color_block is None:
		return

	item_color = item_color_block.get('class')[-1][3:]

	return item_color


def __parse_item_set_parts(block, class_name):
	set_parts_block = block[class_name]
	if set_parts_block is None:
		return

	set_parts_tags = set_parts_block.find_all('a', attrs={'class': 'item-set-part'})
	set_parts = [tag.text for tag in set_parts_tags]

	return set_parts


def __parse_item_image(block, class_name):
	image_block = block[class_name]
	if image_block is None:
		return

	global_container, image_container = image_block.find_all('div')
	item_image_class_name = image_container.get('class')[-1]
	style = driver.find_element_by_class_name(f'{item_image_class_name}')

	width = style.value_of_css_property('width')
	height = style.value_of_css_property('height')

	image_bias_x = style.value_of_css_property('background-position-x')
	image_bias_y = style.value_of_css_property('background-position-y')

	size = {
		'width' : width,
		'height' : height,
		'bias' : {
			'x' : image_bias_x,
			'y' : image_bias_y
		}
	}

	return size


def __parse_item_req(block, class_name):
	req_block = block[class_name]
	if req_block is None:
		return

	req_block_divs = req_block.find_all('div')
	item_req = [tag.text for tag in req_block_divs]

	return item_req


parse_info = {
	'item-name' : ParseInfo('name', __parse_item_param, 'a'),
	'item-bitmap-background' : ParseInfo('color', __parse_item_color, 'div'),
	'item-description-text' : ParseInfo('description', __parse_item_param, 'div'),
	'item-type' : ParseInfo('type', __parse_item_param, 'div'),
	'item-base-stats' : ParseInfo('base_stat', __parse_wrapper_divs, 'div'),
	'tooltip-skill-params' : ParseInfo('skill_params', __parse_wrapper_divs, 'div'),
	'item-set-name' : ParseInfo('set_name', __parse_item_param, 'a'),
	'item-set-stats' : ParseInfo('set_parts', __parse_item_set_parts, 'div'),
	'item-req' : ParseInfo('access_condition', __parse_item_req, 'div'),
	'dlc-badge' : ParseInfo('dlc_name', __parse_item_param, 'div'),
	'item-bitmap-container' : ParseInfo('image', __parse_item_image, 'div')
}


def get_html(url:str) -> str:
	driver.get(url)

	return driver.page_source


def get_items_html(html:str) -> list:
	soup = bs(html, 'html.parser')
	equip_blocks = soup.find_all('div', attrs={'class' : 'item-card'})

	return equip_blocks


def get_item_params_blocks(item_block) -> dict:
	result = {class_name: item_block.find(block_name.tag, attrs={'class': class_name}) \
		for class_name, block_name in parse_info.items()}

	return result


def get_item_params(item_params_blocks):
	result = {key: block.func(item_params_blocks, key) \
		for key, block in parse_info.items()}

	return result


class Item:
	def __init__(self, params: dict):
		self.__dict__.update(params)

		self.__update_keys()


	def __update_keys(self):
		for key in parse_info.keys():
			new_key = parse_info[key].name
			self.__dict__[new_key] = self.__dict__.pop(key)


def get_all_items(item_type: str) -> list:
	result = []

	url = URL.format(item_type)
	html = get_html(url)
	items_html = get_items_html(html)

	for item in items_html:
		params = get_item_params_blocks(item)
		item_params = get_item_params(params)
		item_params.update({'equip_type': item_type})
		item = Item(item_params)

		result.append(item.__dict__)
	print(result[-1])

	return result


def save_to_json(file_name: str, items: list) -> None:
	with open(file_name, mode='w', encoding='utf-8') as file:
		json.dump(items, file)


def ___test_parse():
	url = URL.format('shields')
	html = get_html(url)

	#with open('temp.html', mode='w', encoding='utf-8') as file:
	#	file.write(html)

	#with open('temp.html', mode='r', encoding='utf-8') as file:
	#	html = file.read()

	items_html = get_items_html(html)

	for item in items_html:
		params = get_item_params_blocks(item)
		item_params = get_item_params(params)
		item_params.update({'equip_type': 'shields'})
		item = Item(item_params)
	print(item.__dict__)


def main():
	for item_type in ITEM_TYPES:
		# url = URL.format(item_type)
		print(item_type)
		items = get_all_items(item_type=item_type)

		save_to_json(f'db/{item_type}.json', items)


if __name__ == '__main__':
	main()
	# ___test_parse()