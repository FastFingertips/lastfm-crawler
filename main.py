import os
import time
import json
import logging
from datetime import date, datetime
import requests
import urllib.parse
from bs4 import BeautifulSoup
from win10toast import ToastNotifier
from inspect import currentframe #: PMI

## -- SPECIAL DEFS --
def ping(host):
	os.system("cls && ping -n 1 " + host)

def debugLog(def_return=False):
	debugFile = 'debug.log'
	logging.basicConfig(
		filename = debugFile,
		encoding = 'utf-8',
		format = '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
		datefmt = '%Y%m%d%H%M%S',
		level = logging.DEBUG)

	if def_return:
		return getLastLineContent(debugFile)

## -- DO DEFS --

def doSyncControl(user_name, method, json_file=None):
	date_time = date.today().strftime("%Y-%m-%d")
	if json_file == None:
		json_file = f'backups/json/{user_name}-alltime.json'

	jsonContent = getJsonData(json_file) # Dict
	for artistName, artistCount in jsonContent.items():
		artistScrobbleCount = getArtistScrobbleCount(user_name, artistName, date_time, method)
		print(f'{artistName} -> {artistCount}:{artistScrobbleCount} {artistCount==artistScrobbleCount}')
		if jsonContent[artistName] != artistScrobbleCount:
			return False, jsonContent.keys()
	return True, None

def doJsonUpdate(json_path, new_data):
	with open(json_path, 'w') as json_file:
		json.dump(new_data, json_file)

def doAlltimeJsonSync(user_name, artist_names):
	jsonPath = f'backups/json/{user_name}-alltime.json'
	gettingMethod = 'all'
	syncDiff, syncArtistsNames = doSyncControl(user_name, gettingMethod)
	print(syncDiff)
	if not syncDiff:
		newData = {}
		for artistName in artist_names:
			newData[artistName] = getArtistAllScrobbleCount(user_name, artistName)
		doJsonUpdate(jsonPath, newData)

def doRunLastNotifier(current_profile_data):
	printRunningDef(currentframe())
	# Get notifier data
	if current_profile_data["last_tracks"] != None:
		username = current_profile_data["username"]
		song_name = current_profile_data["last_tracks"][0][0]
		artist_name = current_profile_data["last_tracks"][0][1]
		artistCountUrl = f'https://www.last.fm/user/{username}/library/music/+noredirect/{urllib.parse.quote(artist_name)}?date_preset=ALL'
		artistCountDom = getDom(getResponse(artistCountUrl))
		artistCount = artistCountDom.find_all("p", {"class":"metadata-display"})[0].text
		msgLastTrack = f'\nLast track: {song_name} | {artist_name} ({artistCount})'
	else:
		msgLastTrack = ''

	doRunNotifier(
		f'Profile: {current_profile_data["display_name"]} (@{current_profile_data["username"]})', # Title
		f'Current Scrobbles: {current_profile_data["scrobbled_count"]}{msgLastTrack}') # Content

def doCheckChange(current_profile_data, user_name):
	printRunningDef(currentframe())
	while True:	
		print('Process: Syncing profile..')
		newProfileData = getSearchUser(user_name, False) 	
		if current_profile_data != newProfileData:
			print('Process: New profile information has been obtained.')
			if newProfileData["scrobbled_count"] != current_profile_data["scrobbled_count"]:
				doRunLastNotifier(newProfileData)
			printStatus(newProfileData, True)
			current_profile_data = newProfileData
		else:
			print('Process: No changes to profile information.')

def doRunNotifier(title_msg=' ', content_msg=' '):
	printRunningDef(currentframe())
	icoDomain = 'https://www.last.fm'
	imgDir = 'images/media'
	imgName = 'lastfm.ico'
	imgPath = f'{imgDir}/{imgName}'

	if not os.path.exists(imgPath): # ico not exist
		img_url = f'{icoDomain}{getFaviconUrl(icoDomain)}'
		doDownloadImage(imgName, img_url, imgDir)

	notifier = ToastNotifier() # class
	notifier.show_toast(title_msg, content_msg, imgPath) # title="Notification", msg="Here comes the message", icon_path=None, duration=5, threaded=False

def doDownloadImage(img_name, img_url, img_dir=None, open_mode='wb'): # doDownloadImage('images/avatars', 'MyAvatar', 'AvatarUrl')
	printRunningDef(currentframe())
	if img_dir != None:
		doDirCreate(img_dir)
		img_name = f'{img_dir}/{img_name}'

	if '.' not in img_name: # Dosya uzantısı isimde yoksa url sonundan alınır.
		img_name = f"{img_name}{img_url[img_url.rfind('.'):]}"

	if not os.path.exists(img_name):
		imgResponse = getResponse(img_url)
		imgContent = imgResponse.content
		with open(img_name, open_mode) as file:
			file.write(imgContent)

def doDirCreate(dir_name):
	printRunningDef(currentframe())
	dirList = dir_name.split('/')
	for d in dirList:
		try:
			if d == dirList[-1] :
				os.mkdir(dir_name)
			else:
				os.mkdir(d) # Directory Created
		except FileExistsError:
			pass # Directory already exists

def doCalcAlltimeTodayCount(first_alltime, today_box): # total contribution to artists listened to today
	print(first_alltime)
	print(today_box)

def doDictJsonSave(json_name, save_dict, json_dir='backups/json', open_mode='w'):
	json_ex = '.json'

	if json_dir != None:
		doDirCreate(json_dir)
		json_name = f'{json_dir}/{json_name}'

	if json_ex not in json_name[-5:]:
		json_name = f'{json_name}{json_ex}'

	with open(json_name, open_mode) as json_file:
		json.dump(save_dict, json_file)

## -- GET DEFS -- (RETURN)

def getSearchUser(user_name, status_print=True, refresh_bool=True, follow_print=True):
	printRunningDef(currentframe())
	if user_name:
		urlDict, domsDict, responsesDict = {},{},{}
		urlDict['user_url'] = "https://www.last.fm/user/" + user_name
		# Get profile page
		responsesDict["profile_dom"] = getResponse(urlDict['user_url'])
		# Get follow pages
		if follow_print:
			urlDict['fallowing_url'] = urlDict['user_url']+'/following'
			urlDict['fallowers_url'] = urlDict['user_url']+'/followers'
			responsesDict["following_dom"] = getResponse(urlDict['fallowing_url'])
			responsesDict["followers_dom"] = getResponse(urlDict['fallowers_url'])
		# Get response doms
		for responseKey, responseValue in responsesDict.items():
			domsDict[responseKey] = getDom(responseValue)
		userProfileInfos = getProfileInfos(domsDict) # Get profile infos
		# Prints
		if status_print:
			printStatus(userProfileInfos, refresh_bool)
		return userProfileInfos

def getProfileInfos(doms_dict):
	printRunningDef(currentframe())
	profileDict = {}
	if "profile_dom" in doms_dict:
		profileDom = doms_dict["profile_dom"]
		profileDict["username"] = getUsername(profileDom)
		profileDict["user_avatar"] = getUserAvatar(profileDom)
		profileDict["display_name"] = getDisplayName(profileDom)
		profileDict["scrobbling_since"] = getProfileSince(profileDom)
		profileDict["last_tracks"] = getLastScrobs(profileDom, 3)
		profileDict["background_image"] = getBackgroundImage(profileDom)
		### !!!
		profileDict["scrobbled_count"] = int(getHeaderStatus(profileDom)[0]) # Profile Header: Scrobbles
		profileDict["artists_count"] = int(getHeaderStatus(profileDom)[1]) # Profile Header: Artist Count
		profileDict["likes_count"] = int(getHeaderStatus(profileDom)[2]) # Profile Header: Loved Tracks
		### !!!
		profileDict['today_artists'], profileDict['today_tracks'], profileDict['old_today_tracks'] = getTodayListening(profileDict["username"])
		profileDict['artist_count_alltime'] = getArtistAllTimeCount(profileDict["username"], profileDict['today_tracks'], profileDict['old_today_tracks']) # username, today_tracks, old_today_tracks
	
	if all(key in doms_dict for key in ('following_dom', 'followers_dom')): # Ayrı bir post isteği gerekir.
		followsDom = [doms_dict["following_dom"], doms_dict["followers_dom"]]
		profileDict["follows"] = {}
		profileDict["follows"]["following"] = getUserFollowing(followsDom[0]) # Following
		profileDict["follows"]["followers"] = getUserFollowers(followsDom[1]) # Followers
		profileDict["follows"]["following_gt"] = getUserGT(profileDict["follows"]["following"], profileDict["follows"]["followers"])
		# Get Counts
		profileDict["follows"]["following_counts"] = int(getUserFollowingCount(followsDom[0])) # Following
		profileDict["follows"]["followers_counts"] = int(getUserFollowersCount(followsDom[1])) # Followers
		profileDict["follows"]["fb_count"] = int(getDictValueCount(profileDict["follows"]["following_gt"], True))
		profileDict["follows"]["no_fb_count"] = int(profileDict["follows"]["following_counts"] - profileDict["follows"]["fb_count"])
	return profileDict

def getResponse(response_url):
	while True:
		printRunningDef(currentframe())
		# urlPart1, urlPart2, urlPart3 = response_url.partition("+noredirect/")
		# if "/" in urlPart3:
		# 	urlPart3 = urlPart3.replace('/','%2F')
		# response_url = f'{urlPart1}{urlPart2}{urlPart3}'	
		response = requests.get(response_url)
		responseCode = response.status_code
		print(f'Request: {response_url[:]} : {responseCode}')

		if responseCode in range(200,299):
			if "https://www.last.fm/" in response_url:
				pageContent = getDom(response)
				ogUrl = pageContent.find("meta", property="og:url")['content']
				print(f'responseUrl = ogUrl {response_url == ogUrl}')
				if response_url != ogUrl:
					print('Url değişimi algılangı istek düzeltiliyor..')
					response_url = ogUrl
					continue
			return response
		print(f'Trying to reconnect to {response_url[19:]} address..')

def getDom(response):
	while True:
		printRunningDef(currentframe())
		pageContent = BeautifulSoup(response.content, 'html.parser')
		return pageContent

def getFaviconUrl(site_url): # Belirtilen sayfadaki iconu çeker.
	printRunningDef(currentframe())
	while True:
		iconResponse = getResponse(site_url)
		if iconResponse.status_code in range(200,299):
			iconDom = getDom(iconResponse)
			iconUrl = iconDom.find("link", {"rel":"icon"})['href']
			return iconUrl # return '/static/images/favicon.702b239b6194.ico'

def getBackgroundImage(profile_dom):
	printRunningDef(currentframe())
	backgroundPath = 'images/background'
	backgroundName = f'{getUsername(profile_dom)}-bg-{getCurrentSession()}'
	try:
		backgroundImageUrl = profile_dom.find("div", {"class":"header-background header-background--has-image"})["style"][22:-2]
		doDownloadImage(backgroundName, backgroundImageUrl, backgroundPath)
	except:
		backgroundImageUrl = "No Background (Last.fm default background)"
	return backgroundImageUrl # Replaced: background-image: url();

def getUserAvatar(profile_dom):
	printRunningDef(currentframe())
	avatarPath = 'images/avatar'
	avatarName =  f'{getUsername(profile_dom)}-av-{getCurrentSession()}'
	defaultAvatarId = "818148bf682d429dc215c1705eb27b98"
	# defaultImageUrl:("https://lastfm.freetls.fastly.net/i/u/avatar170s/818148bf682d429dc215c1705eb27b98.png") 
	profileAvatarUrl = profile_dom.find("meta", property="og:image")["content"]
	if defaultAvatarId in profileAvatarUrl:
		profileAvatarUrl = "No Avatar (Last.fm default avatar)"
	else:
		doDownloadImage(avatarName, profileAvatarUrl, avatarPath)
	return profileAvatarUrl 

def getHeaderStatus(profile_dom):
	printRunningDef(currentframe())
	headerStatus = [0, 0, 0]
	headers = profile_dom.find_all("div", {"class": "header-metadata-display"})
	for i in range(len(headers)):
		headerStatus[i] = headers[i].text.strip()
		headerStatus[i] = getRemoval(headerStatus[i],',', int) # {} içerisindeki {}'i kaldır ve {} olarak geri al.
	return headerStatus

def getRemoval(inside_obj, find_obj=' ', return_type=None):
	if return_type == None:
		return_type = type(inside_obj)
    
	if type(inside_obj) != str: # int'de işlem yapılamaz
		inside_obj = str(inside_obj)
    
	if type(find_obj) != str:
		find_obj = str(find_obj)

	if find_obj in inside_obj:
		inside_obj = inside_obj.replace(find_obj,'')
		
	if return_type != type(inside_obj):
		if return_type == int:
			inside_obj = int(inside_obj)
		elif return_type == float:
			inside_obj = float(inside_obj)
	# print(f'{inside_obj}: {type(inside_obj)}')
	return inside_obj

def getUsername(profile_dom):
	printRunningDef(currentframe())
	profileUserName = profile_dom.find("h1", {"class":"header-title"})
	return profileUserName.text.strip()

def getDisplayName(profile_dom):
	printRunningDef(currentframe())
	profileDisplayName = profile_dom.find("span", {"class":"header-title-display-name"})
	return profileDisplayName.text.strip()

def getCurrentSession(get_length=None):
	printRunningDef(currentframe())
	'''
		get_length 14 = %Y%m%d%H%M%S
		get_length 12 = %Y%m%d%H%M
		get_length 10 = %Y%m%d%H
		get_length 8 = %Y%m%d (Default: None)
		get_length 6 = %Y%m
		get_length 4 = %Y
	'''
	session = datetime.now().strftime('%Y%m%d%H%M%S') #YearMonthDayHourMinuteSecond
	if get_length == None:
		session = session[0:8] # %Y%m%d
	else:
		session = session[:get_length]
	return session

def getUserFollowingCount(following_dom):
	printRunningDef(currentframe())
	while True:
		try:
			topHeader = following_dom.find("h1", {"class":"content-top-header"}).text # Path
			userFollowing = topHeader[topHeader.find("(")+1:topHeader.find(")")] # Parantez arası değeri
			try:
				userFollowing = int(userFollowing) # Sayı değilse
			except:
				userFollowing = 0
			return userFollowing
		except:
			continue	

def getUserFollowersCount(followers_dom):
	printRunningDef(currentframe())
	while True:
		try:
			topHeader = followers_dom.find("h1", {"class":"content-top-header"}).text # Path
			userFollowers = topHeader[topHeader.find("(")+1:topHeader.find(")")] # Parantez arası değeri
			try:
				userFollowers = int(userFollowers) # Sayı değilse
			except:
				userFollowers = 0
			return userFollowers
		except:
			continue

def getUserFollowing(following_dom):
	printRunningDef(currentframe())
	followingDict = {}
	while True:
		following = following_dom.find_all(attrs={"class": "user-list-name"})
		for userName in following: # Bir sayfada max 30
			userName = userName.text.strip()
			followingDict[userName] = True
		if following_dom.find("li", {"class": "pagination-next"}):
			pageNo = following_dom.find("li", {"class": "pagination-next"})
			currentFollowingPageUrl = f"https://www.last.fm/user/{getUsername(following_dom)}/following{pageNo.a['href']}"
			following_dom = getDom(getResponse(currentFollowingPageUrl)) # current followers page dom
		else:
			return followingDict
	
def getUserFollowers(followers_dom):
	printRunningDef(currentframe())
	followersDict = {}
	while True:
		followers = followers_dom.find_all(attrs={"class": "user-list-name"})
		for userName in followers: # Bir sayfada max 30
			userName = userName.text.strip()
			followersDict[userName] =  True
		if followers_dom.find("li", {"class": "pagination-next"}):
			pageNo = followers_dom.find("li", {"class": "pagination-next"})
			currentFollowersPageUrl = f"https://www.last.fm/user/{getUsername(followers_dom)}/followers{pageNo.a['href']}"
			followers_dom = getDom(getResponse(currentFollowersPageUrl)) # current followers page dom
		else:
			return followersDict

def getUserGT(following_box, followers_box):
	printRunningDef(currentframe())
	userGt = {}
	for userName in following_box:
		if userName in followers_box:
			userGt[userName] = True
		else:
			userGt[userName] = False
	return userGt

def getProfileSince(profile_dom):
	printRunningDef(currentframe())
	profileSince = profile_dom.find("span", {"class":"header-scrobble-since"})
	return profileSince.text.partition("• scrobbling since")[2].strip() # Sonrasını al

def getLastScrobs(profile_dom, get_count):
	printRunningDef(currentframe())
	lastTracks = {}
	for x in range(get_count): # X kadar al.
		try:
			lastTrackDom = profile_dom.find_all("tr", {"class":"chartlist-row chartlist-row--with-artist chartlist-row--with-buylinks js-focus-controls-container"})[x]
			lastTrackSongName = lastTrackDom.find("td", {"class":"chartlist-name"}).text.strip()
			lastTrackArtist = lastTrackDom.find("td", {"class":"chartlist-artist"}).text.strip()
			lastTrackDate = lastTrackDom.find("td", {"class":"chartlist-timestamp"}).text.strip()
			lastTracks[x] = [lastTrackSongName,lastTrackArtist,lastTrackDate]
		except:
			lastTracks =  None
			break
	return lastTracks

def getDictValueCount(dicti, key):
	printRunningDef(currentframe())
	return sum(key for _ in dicti.values() if _)

def getFollowDict(following_box, followers_box, followback_box):
	f = {}
	for username in following_box:
		f[username] = {}
		f[username]['following'] = True
		if username in followers_box:
			f[username]['follower'] = True # 2. true takip ettiği / false etmediği
			f[username]['user_fb'] = followback_box[username]
		else:
			f[username]['follower'] = False
			f[username]['user_fb'] = followback_box[username]
		f[username]['link'] = f'https://last.fm/user/{username}'
	for username in followers_box:
		f[username] = {}
		f[username]['follower'] = True
		if username in following_box:
			f[username]['following'] = True # 2. true takip ettiği / false etmediği
			f[username]['user_fb'] = followback_box[username]
		else:
			f[username]['following'] = False
			f[username]['user_fb'] = False
		f[username]['link'] = f'https://last.fm/user/{username}'
	return f

def getTodayListening(user_name):
	printRunningDef(currentframe())
	jsonDir = 'backups/json'
	jsonName = f'{user_name}-today-{appSession}.json'
	jsonPath = f'{jsonDir}/{jsonName}'
	today = date.today()
	today = today.strftime("%Y-%m-%d")
	pageNo = 1
	todayTracks = {}

	if os.path.exists(jsonPath): # Önceden bir today jsonu varsa
		oldTodayTracks = getJsonData(jsonPath) # Eskisini kaydet
	else:
		oldTodayTracks = None

	while True:
		todayListeningUrl = f'https://www.last.fm/user/{user_name}/library/artists?from={today}&rangetype=1day&page={pageNo}'
		todayListeningDom = getDom(getResponse(todayListeningUrl))
		try:
			todayListeningDomTracks = todayListeningDom.find_all("tr", "chartlist-row")
			for i in todayListeningDomTracks:
				artistName = i.find("td","chartlist-name").text.strip()
				artistCount = i.find("span","chartlist-count-bar-value").text.strip()
				todayTracks[artistName] = getRemoval(artistCount[:artistCount.rfind(' ')], ',', int) # Boşluğun hemen öncesine kadar al. (123 scrobbles)
		except:
			pass # Bir hata gerçekleşirse dict boş gönderilir.

		if todayListeningDom.find("li", {"class": "pagination-next"}):
			pageNo += 1
		else:
			doDictJsonSave(jsonName, todayTracks) # Json save
			todayArtists = list(todayTracks.keys()) # Bugün dinlenen sanatçıların isimleri
			return todayArtists, todayTracks, oldTodayTracks

def getArtistAllCount(user_name, artist_names):
	artistScrobbs = {}
	for artistName in artist_names:
		artistCountUrl = f'https://www.last.fm/user/{user_name}/library/music/+noredirect/{urllib.parse.quote(artistName)}' # Artist alltime details
		artistCountDom = getDom(getResponse(artistCountUrl))
		artistScrobbleCount = getRemoval(artistCountDom.find_all("p", {"class":"metadata-display"})[0].text, ',', int)
		artistScrobbs[artistName] = artistScrobbleCount # library_header_title, metadata_display
	return artistScrobbs

def getJsonData(json_path):
		with open(json_path) as jsonFile:
			return json.load(jsonFile)

def getArtistAllTimeCount(user_name, artists_box, old_artists_box): # total contribution to artists listened to today
	printRunningDef(currentframe())
	jsonDir = 'backups/json'
	jsonName = f'{user_name}-alltime-{appSession}.json'
	jsonPath = f'{jsonDir}/{jsonName}'

	if old_artists_box == None:
		if os.path.exists(jsonPath):
			syncBool, syncArtistNames = doSyncControl(user_name, 'all')
			if not syncBool:
				doAlltimeJsonSync(user_name, syncArtistNames)

	if not os.path.exists(jsonPath): # ico not exist
		artistNames = artists_box.keys()
		alltimeJson = getArtistAllCount(user_name, artistNames)
	else:
		alltimeJson = getJsonData(jsonPath)
		for artistName, artistCount in artists_box.items():
			if old_artists_box == None:
				oldCount = artists_box[artistName]
			else:
				if artistName in old_artists_box: # Sanatçı önceden dinlendiyse
					oldCount = old_artists_box[artistName] # Sanatçının önceden kayıtlı olan dinlenme sayısı
				else: # Yeni bir sanatçı dinlendiyse
					oldCount = artists_box[artistName] # Sanatçının önceden kayıtlı olan dinlenme sayısı

			if artistName in alltimeJson: # Artist kullanıcının tüm zamanlarına önceden kaydedilmişse
				alltimeJson[artistName] += (artistCount-oldCount)
			else: # Önceden kayıt edilmemiş kişiler.
				alltimeJson[artistName] = getArtistAllCount(user_name, [artistName])[artistName]

	doDictJsonSave(jsonName, alltimeJson)
	return alltimeJson	

def getDictDiff(dict_x, dict_y): # Not yet
	dict_diff = None
	return dict_diff

def getDictKeyNo(key, d): # key, dict
	dictKeys = d.keys()
	dictKeysList = list(dictKeys)
	keyIndexNo = dictKeysList.index(key) + 1
	return keyIndexNo

def getArtistScrobbleCount(user_name, artist_name, date_time, method):
	if method == 'today':
		return getArtistTodayScrobbleCount(user_name, artist_name, date_time)
	elif method == 'all':
		return getArtistAllScrobbleCount(user_name, artist_name)

def getArtistTodayScrobbleCount(user_name, artist_name, from_set):
	artistTodayScrobbleUrl =  f'https://www.last.fm/tr/user/{user_name}/library/music/+noredirect/{urllib.parse.quote(artist_name)}?from={from_set}&rangetype=1day'
	artistTodayScrobbleDom = getDom(getResponse(artistTodayScrobbleUrl))
	artistTodayScrobbleElement = artistTodayScrobbleDom.find_all("p", {"class":"metadata-display"})[0].text
	artistTodayScrobbleCount = getRemoval(artistTodayScrobbleElement, ',', int)
	return artistTodayScrobbleCount
	
def getArtistAllScrobbleCount(user_name, artist_name):

	artistCountUrl = f'https://www.last.fm/user/{user_name}/library/music/+noredirect/{urllib.parse.quote(artist_name)}'
	artistCountDom = getDom(getResponse(artistCountUrl))
	artistScrobbleCount = getRemoval(artistCountDom.find_all("p", {"class":"metadata-display"})[0].text, ',', int)
	print(artist_name, artistScrobbleCount)
	return artistScrobbleCount # library_header_title, metadata_display

def getLastLineContent(file_name):
	with open(file_name, 'r') as f:
		return f.readlines()[-1][:14]

## -- PRINT DEFS --
def printRunningDef(def_info):
	if True:
		time.sleep(0.03)
		currentLine = def_info.f_back.f_lineno
		defName = def_info.f_code.co_name
		with open('main.py', 'r') as f:
			mainLinesLength = len(str(len(f.readlines())))
			currentLineLength = len(str(currentLine))
			print(f"Process: [{'0'*(mainLinesLength-currentLineLength)+str(currentLine) if currentLineLength < mainLinesLength else currentLine}]:{defName}")

def printStatus(upi_dict, refresh_bool): # printStatus(userProfileInfos, react)
	print(f'\n*** {time.strftime("%H:%M:%S")} ***')
	upi_acot = upi_dict['artist_count_alltime']
	upi_lts = upi_dict["last_tracks"]
	upi_sc = upi_dict["scrobbled_count"]
	upi_ac = upi_dict["artists_count"]
	upi_lc = upi_dict["likes_count"]
	upi_tt = upi_dict['today_tracks']
	upi_bi = upi_dict["background_image"]
	upi_ua = upi_dict["user_avatar"]
	upi_ss = upi_dict["scrobbling_since"]
	upi_dn = upi_dict["display_name"]
	upi_un = upi_dict["username"]
	if "follows" in upi_dict:
		# Following
		upi_fgc = upi_dict["follows"]["following_counts"]
		upi_fg = upi_dict["follows"]["following"]
		# Followers
		upi_fsc = upi_dict["follows"]["followers_counts"]
		upi_fs = upi_dict["follows"]["followers"]
		# Followback
		upi_fb = upi_dict["follows"]["following_gt"]
		upi_fbc = upi_dict["follows"]["fb_count"]
		upi_nofbc = upi_dict["follows"]["no_fb_count"]
		printFollowStat(upi_fg, upi_fs , upi_fb, upi_fgc, upi_fsc, upi_fbc, upi_nofbc)
	printRecentTracks(upi_lts, upi_sc) # Last Tracks Prints
	printTodayAllTime(upi_acot, upi_tt) # Total, Today Prints
	# Adresses
	print(f'\nProfile: {upi_dn} (@{upi_un})')
	print(f'Scrobbling Since: {upi_ss}')
	print(f'Avatar: {upi_ua}')
	print(f'Background: {upi_bi}')
	# Headers
	print(f'Scrobbles: {upi_sc} | ', end="")
	print(f'Artists: {upi_ac} | ', end ="")
	print(f'Loved Tracks: {upi_lc}'),

	if refresh_bool:
		refresh_time = 5
		print(f'\nIt will be checked again in {refresh_time} seconds..')
		time.sleep(refresh_time) # 5 sec
		doCheckChange(upi_dict, upi_un)

def printTodayAllTime(artists_alltime, artists_today):
	if len(artists_today) > 0:
		print(f'\nYour total contribution to the artist today;')
		for todayArtistName, todayArtistCount in artists_today.items():
			todayArtistNo = getDictKeyNo(todayArtistName, artists_today) # belirtilen anahtarın sözlükte kaçıncı sırada olduğunu çek
			try:
				count_msg = f'{artists_alltime[todayArtistName]} (Today: {todayArtistCount})'
			except:
				count_msg = f'Today: {todayArtistCount}'
			finally:
				print(f'[{todayArtistNo}]: {todayArtistName} - {count_msg}')

def printTodayListening(tracks_today):
	if bool(tracks_today): # Dict boş dönmezse
		print('Today Listening Artists;')
		for todayArtistName, todayArtistCount in tracks_today.items():
			todayArtistRank = getDictKeyNo(todayArtistName, tracks_today) # belirtilen anahtarın sözlükte kaçıncı sırada olduğunu çek
			print(f'{todayArtistRank}: {todayArtistName} ({todayArtistCount})')
	else: # Dict boş ise false döndürür.
		print('No songs were listened to today.')

def printRecentTracks(last_tracks, scrobbled_count):
	if last_tracks != None:
		print(f'\nRecent Tracks;', end='')
		recentTracks = last_tracks
		for trackNo in recentTracks:
			print(f'\n[{trackNo+1}]:', end=" ")
			for trackValueNo in range(len(recentTracks[trackNo])):
				print(recentTracks[trackNo][trackValueNo], end= " | ")
		else:
			print()
	elif scrobbled_count > 0:
		print("\nRecent Tracks: realtime tracks is private.")

def printDictValue(print_dict):
	for key, value in print_dict.items():
		print(f'{key} ({value})')

def printus(dict_name, user_dict, count_dict):
	print(f'{dict_name}: ({count_dict});')
	for user, value in user_dict.items(): # user, bool
		print(f'[{value}]: {user}')

def printFollowStat(fg, fs, fb, fgc, fsc, fbc, nofbc):
	print(f'\nFollows;')
	if False:
		printus("Following", fg, fgc) # Following
		printus("Followers", fs, fsc) # Followers
		printus("Followback", fb, fbc)

	print(f"Following: {fgc}, Followers: {fsc}, Followback: {fbc}")
	if fgc != fbc:
		print(f"Users who don't follow you back ({nofbc});")
		f = getFollowDict(fg, fs, fb)
		for user in f:
			if f[user]['following'] == True and f[user]['follower'] == False:
				print(f"FG:[{f[user]['following']}], FR:[{f[user]['follower']}], FB:[{f[user]['user_fb']}] | {f[user]['link']}, @{user}")
	elif fgc != 0:
		print(f'{fbc} users you follow are following you.')

if __name__ == '__main__':
	appSession = debugLog(True)
	# ping("www.last.fm")
	getSearchUser(input('Username: @'))

