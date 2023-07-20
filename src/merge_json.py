import sys
import os
import json 
import re
from common import *
from PyQt5.QtCore import QSettings

EncodeName = 'utf-8'
OnceLinesCount = 0 #为0则需要读入filenameList缓存
Postfix = '.json'

#var
workpath = ''
filename = ''

allJson = [
	{}, # 0 字典
	[] # 1 列表
]
jsonType = 0
filenameList = []

def writeMerge():
	#print(filename)
	name = None
	if OnceLinesCount == 0:
		name = 'merge' + Postfix
	else:
		name = re.sub(r'\.[0-9]+', '', filename)
		name = name + '.merge' + Postfix
	filepath = os.path.join(workpath, name)
	fileNew = open(filepath, 'w', encoding=EncodeName)
	json.dump(allJson[jsonType], fileNew, ensure_ascii=False, indent=2)
	fileNew.close()
	print('Write done:', name)
	#保存合并信息
	filenameList.append([0, name])
	cache = json.dumps(filenameList, indent=2)
	settings = QSettings('config.ini', QSettings.IniFormat)
	settings.setValue('filenameList', cache)

def writeSeprate(seq):
	name = None
	if OnceLinesCount == 0:
		name = filenameList[seq][1] + Postfix
	else:
		name = filename + '.' + str(seq) + Postfix
	filepath = os.path.join(workpath, name)
	fileNew = open(filepath, 'w', encoding=EncodeName)
	json.dump(allJson[jsonType], fileNew, ensure_ascii=False, indent=2)
	fileNew.close()
	print('Write done:', name)

def read(funcIndex):
	global jsonType
	print('Load', filename)
	filepath = os.path.join(workpath, filename+Postfix)
	fileOld = open(filepath, 'r', encoding=EncodeName)
	content = json.load(fileOld)
	fileOld.close()
	if isinstance(content, dict):
		jsonType = 0
		#字典
		if funcIndex == 0:
			mergeDic(content)
		else:
			seprateDic(content)
	elif isinstance(content, list):
		jsonType = 1
		#列表
		if funcIndex == 0:
			mergeList(content)
		else:
			seprateList(content)
	else:
		print('请检查Json格式。')
		return
	# 合并时缓存信息
	if funcIndex == 0:
		item = [len(content), filename] #行数，文件名
		filenameList.append(item)
		if filename.endswith('merge'):
			print('\033[33m合并前已存在merge.json，请确定操作是否重复\033[0m')

def mergeDic(content):
	for key, value in content.items():
		allJson[0][key] = value

def mergeList(content):
	for item in content:
		allJson[1].append(item)

def seprateDic(content):
	count = 0
	seq = 0
	for key, value in content.items():
		allJson[0][key] = value
		count += 1
		if count >= OnceLinesCount:
			seq += 1
			writeSeprate(seq)
			count = 0
			allJson[0].clear()
	if count != 0:
		seq += 1
		writeSeprate(seq)

def seprateList(content):
	count = 0
	seq = 0
	for item in content:
		allJson[1].append(item)
		count += 1
		if count >= getOnceLinesCount(seq):
			writeSeprate(seq)
			seq += 1
			count = 0
			allJson[1].clear()
	if count != 0:
		writeSeprate(seq)
		seq += 1

def getOnceLinesCount(seq):
	if OnceLinesCount > 0: return OnceLinesCount
	item = filenameList[seq]
	return item[0]

def loadFilenameList(funcIndex):
	global filenameList
	filenameList.clear()
	if funcIndex == 1 and OnceLinesCount == 0:
		settings = QSettings('config.ini', QSettings.IniFormat)
		cache = settings.value('filenameList')
		filenameList = json.loads(cache)

#args: { workpath, funcIndex, lineCount }
def mergeTool(args):
	if len(args) < 3:
		print("参数错误")
		return
	path = args['workpath']
	funcIndex = args['funcIndex'] # 0合并 1分割
	global OnceLinesCount
	OnceLinesCount = args['lineCount']
	#print(path)
	global workpath
	global filename
	if os.path.isdir(path):
		workpath = path
		#print(workpath)
		allJson[0].clear()
		allJson[1].clear()
		loadFilenameList(funcIndex)
		for name in os.listdir(workpath):
			#print('Load', name)
			filename = name.replace(Postfix, '')
			filepath = os.path.join(workpath, filename+Postfix)
			if os.path.isfile(filepath):
				#print(filepath)
				read(funcIndex)
				#break
		if funcIndex == 0:
			writeMerge()
		print('处理结束')
	else:
		print('未找到主目录')

#args: { workpath }
def createDicTool(args):
	global OnceLinesCount
	global workpath
	OnceLinesCount = 0
	workpath = args['workpath']
	ret = createDic('all.orig.json', 'all.trans.json')
	if ret == 1:
		ret = createDic('key.json', 'value.json')

def createDic(keyName, valueName):
	print('开始查找key/value文件:', keyName, valueName)
	keyPath = os.path.join(workpath, keyName)
	valuePath = os.path.join(workpath, valueName)
	if not os.path.isfile(keyPath) or not os.path.isfile(valuePath):
		print('未找到key/value文件', keyName, valueName)
		return 1
	print('找到key/value文件')
	fileOld = open(keyPath, 'r', encoding=EncodeName)
	keyContent = json.load(fileOld)
	fileOld.close()
	fileOld = open(valuePath, 'r', encoding=EncodeName)
	valueContent = json.load(fileOld)
	fileOld.close()
	if not isinstance(keyContent, list) or not isinstance(valueContent, list):
		print('key/value文件不是列表形式')
		return 2
	if len(keyContent) != len(valueContent):
		print('key/value文件长度不一致')
		return 3
	allJson[0].clear()
	for i in range(len(keyContent)):
		keyItem = keyContent[i]
		valueItem = valueContent[i]
		# item: 字符串
		if isinstance(keyItem, str):
			allJson[0][keyItem] = valueItem
		# item: 字典
		elif isinstance(keyItem, dict):
			keys = list(keyItem.values())
			values = list(valueItem.values())
			for i in range(len(keys)):
				key = keys[i]
				value = values[i]
				allJson[0][key] = value
	#导出
	filenameList.clear()
	writeMerge()
	return 0