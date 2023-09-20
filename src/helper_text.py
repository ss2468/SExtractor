import math
import os
import re
from common import *

__all__ = ['splitToTransDic', 'splitToTransDicAuto', 'generateTunnelJis', 'generateTunnelJisMap']

#----------------------------------------------------------
#编码生成目标长度的字节数组，会截断和填充字节
def generateBytes(text, lenOrig, NewEncodeName):
	transData = None
	if ExVar.tunnelJis:
		transData = generateTunnelJis(text)
	else:
		try:
			transData = text.encode(NewEncodeName)
		except Exception as ex:
			print(ex)
			return None
	if ExVar.cutoff == False:
		return transData
	# 检查长度
	count = lenOrig - len(transData)
	#print('Diff', count)
	if count < 0:
		if ExVar.tunnelJis:
			#使用隧道时,cutoffDic字典不生效
			printWarning('译文长度超出原文，请手动修正', text)
			return None
		dic = ExVar.cutoffDic
		if text not in dic:
			if ExVar.cutoffCopy:
					dic[text] = [text, count]
			else:
				dic[text] = ['', count]
		elif dic[text][0] != '':
			#从cutoff字典读取
			transData = dic[text][0].encode(NewEncodeName)
			count = lenOrig - len(transData)
			dic[text][1] = count #刷新长度
		if count < 0:
			printWarning('译文长度超出原文，部分截断', text)
			transData = transData[0:lenOrig]
			try:
				transData.decode(NewEncodeName)
			except Exception as ex:
				#print('\033[31m截断后编码错误\033[0m')
				return None
	if count > 0:
		# 右边补足空格
		#print(transData)
		empty = bytearray(count)
		for i in range(int(count)):
			empty[i] = 0x20
		transData += empty
	return transData

#----------------------------------------------------------
#sep = '\r\n'
sepLen = 2
symbolPattern = '[\\u3000-\\u303F\\uFF00-\\uFF65\\u2000-\\u206F]'
searchCount = 10

#固定分割
def splitToTransDic(orig, trans):
	if trans == '': return #整体译文为空则不处理
	if ExVar.splitAuto:
		#重新分割
		splitToTransDicAuto(orig, trans) 
		return
	sep = ExVar.splitParaSep
	listMsgOrig = re.split(sep, orig)
	listMsgTrans = re.split(sep, trans)
	for j in range(len(listMsgOrig)):
		msgOrig = listMsgOrig[j]
		msgTrans = ExVar.addSpace
		if j<len(listMsgTrans) and listMsgTrans[j] != '':
			msgTrans = listMsgTrans[j]
		if  msgOrig not in ExVar.transDic or \
			ExVar.transDic[msgOrig] == '' or \
			ExVar.transDic[msgOrig] == '　' or \
			ExVar.transDic[msgOrig] == ' ':
			if len(msgTrans) > ExVar.maxCountPerLine:
				printWarning('长度超过设置阈值', msgTrans)
			ExVar.transDic[msgOrig] = msgTrans

#自动重新分割
def splitToTransDicAuto(orig, trans):
	listMsgOrig, listMsgTrans = redistributeTrans(orig, trans)
	for j in range(len(listMsgOrig)):
		msgOrig = listMsgOrig[j]
		msgTrans = listMsgTrans[j]
		if len(msgTrans) > ExVar.maxCountPerLine:
			printWarning('长度超过设置阈值', msgTrans)
		ExVar.transDic[msgOrig] = msgTrans

#重新分割
def redistributeTrans(orig:str, trans:str):
	sep = ExVar.splitParaSep
	#分割原文
	origList = re.split(sep, orig)
	newTrans = re.sub(sep, '', trans)
	if len(origList) == 1:
		return origList, [newTrans]
	if ExVar.ignoreSameLineCount:
		transList = re.split(sep, trans)
		if len(origList) == len(transList):
			return origList, transList
	#查询译文符号
	transSymbolList = []
	matches = re.finditer(symbolPattern, newTrans)
	for match in matches:
		transSymbolList.append(match.end()) #右区间，不包含
	#找出最接近的下标
	transSepList = []
	if len(transSymbolList) <= len(origList):
		#符号数量不大于原文行数
		for index in range(len(origList)):
			if index < len(transSymbolList):
				transSepList.append(transSymbolList[index])
			else:
				transSepList.append(len(newTrans))
	else:
		#符号数量大于原文行数
		scale = len(trans) / len(orig)
		origSepList = []
		length = 0
		for seq in range(len(origList) - 1):
			length += len(origList[seq])
			pos = math.floor(length * scale)
			origSepList.append(pos)
		#查找
		transIndexList = []
		for j, pos in enumerate(origSepList):
			index = findNearestIndex(transSymbolList, pos)
			if j>0 and index <= transIndexList[j-1]:
				index = transIndexList[j-1] + 1
			transIndexList.append(index)
		transIndexList.append(len(transSymbolList)-1)
		#修正尾部重复
		for j in range(len(transIndexList) - 2, -1, -1):
			if transIndexList[j] >= transIndexList[j+1]:
				transIndexList[j] = transIndexList[j+1] - 1
			else:
				break
		#分配
		for index in transIndexList:
			transSepList.append(transSymbolList[index])
	#分割译文
	transList = []
	start = 0
	for end in transSepList:
		if start == end:
			transList.append(ExVar.addSpace)
			#printWarningGreen('添加空行', trans)
		else:
			transList.append(newTrans[start:end])
		start = end
	return origList, transList

# ------------------------------------------------------------
tunnelJisList = []
tunnelUnicodeList = []
lowBytesToAvoid = [ ord('\t'), ord('\n'), ord('\r'), ord(' '), ord(',') ]
#生成VNT的Jis表
def generateJisList():
	lst = list(range(0x81, 0xA0)) + list(range(0xE0, 0xFE))
	for i in lst:
		for j in range(0x01, 0x40):
			if j in lowBytesToAvoid: continue
			tunnelJisList.append(i.to_bytes(1) + j.to_bytes(1))
		
generateJisList()

#插入VNT的字符表，生成JIS编码文本
def generateTunnelJis(text):
	data = bytearray()
	for wchar in text:
		try:
			b = wchar.encode('cp932')
		except Exception as ex:
			if wchar in tunnelUnicodeList:
				#已存在
				index = tunnelUnicodeList.index(wchar)
			else:
				#新增
				index = len(tunnelUnicodeList)
				tunnelUnicodeList.append(wchar)
			#获取转换字符
			b = tunnelJisList[index]
		#导出
		data.extend(b)
	return data

def generateTunnelJisMap(filepath=''):
	data = bytearray()
	for wchar in tunnelUnicodeList:
		bs = wchar.encode('utf-16-le')
		data.extend(bs)
	if filepath != None:
		if filepath == '':
			filepath = os.path.join(ExVar.workpath, 'ctrl', 'sjis_ext.bin')
		fileOutput = open(filepath, 'wb')
		fileOutput.write(data)
		fileOutput.close()
	return data
	