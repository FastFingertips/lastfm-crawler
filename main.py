import os
import time
import json
import logging
from datetime import date, datetime
import requests
from bs4 import BeautifulSoup
from win10toast import ToastNotifier

defStatus = True

## -- DO DEFS --
def getLastLine(file_name):
	with open(file_name, 'r') as f:
		return f.readlines()[-1][:14]

def debugLog(return_bool = False):
	debugFile = 'debug.log'
	logging.basicConfig(filename = debugFile,
						encoding = 'utf-8',
						format = '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
						datefmt = '%Y%m%d%H%M%S',
						level = logging.DEBUG)
	if return_bool:
		return getLastLine(debugFile)

def doRunLastNotifier(current_profile_data):
	if defStatus:
		print(f'Process: {doRunLastNotifier.__name__}')

	# Get notifier data
	if current_profile_data["last_tracks"] != None:
		username = current_profile_data["username"]
		song_name = current_profile_data["last_tracks"][0][0]
		artist_name = current_profile_data["last_tracks"][0][1]
		artistCountUrl = f'https://www.last.fm/user/{username}/library/music/{artist_name}?date_preset=ALL'
		artistCountDom = getDom(getResponse(artistCountUrl))
		artistCount = artistCountDom.find_all("p", {"class":"metadata-display"})[0].text
		msgLastTrack = f'\nLast track: {song_name} | {artist_name} ({artistCount})'
	else:
		msgLastTrack = ''

	doRunNotifier(f'Profile: {current_profile_data["display_name"]} (@{current_profile_data["username"]})',
	f'Current Scrobbles: {current_profile_data["scrobbled_count"]}{msgLastTrack}')

def doCheckChange(current_profile_data, user_name):
	if defStatus:
		print(f'Process: {doCheckChange.__name__}')
	
	while True:	
		newProfileData = getSearchUser(user_name, False) 	
		if current_profile_data != newProfileData:
			if newProfileData["scrobbled_count"] != current_profile_data["scrobbled_count"]:
				doRunLastNotifier(newProfileData)
			current_profile_data = newProfileData
			printStatus(current_profile_data, True)

def doRunNotifier(title_msg=' ', content_msg=' '):
	if defStatus:
		print(f'Process: {doRunNotifier.__name__}')

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
	if defStatus:
		print(f'Process: {doDownloadImage.__name__}')
	
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
	if defStatus:
		print(f'Process: {doDirCreate.__name__}')

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
	
	if defStatus:
		print(f'Process: {getSearchUser.__name__}')

	if user_name:
		urlDict, domsDict, responsesDict = {},{},{}
		urlDict['user_url'] = "https://www.last.fm/user/" + user_name
		profileResponseCode = getResponse(urlDict['user_url'])
		# Get profile page
		if profileResponseCode.status_code in range(200,299):
			responsesDict["profile_dom"] = profileResponseCode
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
	if defStatus:
		print(f'Process: {getProfileInfos.__name__}')

	profileDict = {}
	if "profile_dom" in doms_dict:
		profileDom = doms_dict["profile_dom"]
		profileDict["username"] = getUsername(profileDom)
		profileDict["user_avatar"] = getUserAvatar(profileDom)
		profileDict["display_name"] = getDisplayName(profileDom)
		profileDict["scrobbling_since"] = getProfileSince(profileDom)
		profileDict["last_tracks"] = getLastScrobs(profileDom, 3)
		profileDict["background_image"] = getBackgroundImage(profileDom)
		profileDict["scrobbled_count"] = int(getHeaderStatus(profileDom)[0]) # Profile Header: Scrobbles
		profileDict["artists_count"] = int(getHeaderStatus(profileDom)[1]) # Profile Header: Artist Count
		profileDict["likes_count"] = int(getHeaderStatus(profileDom)[2]) # Profile Header: Loved Tracks
		profileDict['artists_today'], profileDict['today_listening'] = getTodayListening(profileDict["username"])
		profileDict['artist_count_alltime'] = getArtistAllTimeCount(profileDict["username"], profileDict['artists_today'], None) # Need: username, [artistsList]
	
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
	if defStatus:
		print(f'Process: {getResponse.__name__}')

	return requests.get(response_url)

def getDom(response_code):
	if defStatus:
		print(f'Process: {getDom.__name__}')

	return BeautifulSoup(response_code.content, 'html.parser')

def getFaviconUrl(site_url): # Belirtilen sayfadaki iconu çeker.
	if defStatus:
		print(f'Process: {getFaviconUrl.__name__}')

	while True:
		iconResponse = getResponse(site_url)
		if iconResponse.status_code in range(200,299):
			iconDom = getDom(iconResponse)
			iconUrl = iconDom.find("link", {"rel":"icon"})['href']
			return iconUrl # return '/static/images/favicon.702b239b6194.ico'

def getBackgroundImage(profile_dom):
	if defStatus:
		print(f'Process: {getBackgroundImage.__name__}')

	backgroundPath = 'images/background'
	backgroundName = f'{getUsername(profile_dom)}-bg-{getCurrentSession()}'
	try:
		backgroundImageUrl = profile_dom.find("div", {"class":"header-background header-background--has-image"})["style"][22:-2]
		doDownloadImage(backgroundName, backgroundImageUrl, backgroundPath)
	except:
		backgroundImageUrl = "No Background (Last.fm default background)"
	return backgroundImageUrl # Replaced: background-image: url();

def getUserAvatar(profile_dom):
	if defStatus:
		print(f'Process: {getUserAvatar.__name__}')

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
	if defStatus:
		print(f'Process: {getHeaderStatus.__name__}')

	headerStatus = [0, 0, 0]
	headers = profile_dom.find_all("div", {"class": "header-metadata-display"})
	for i in range(len(headers)):
		headerStatus[i] = headers[i].text.strip()
		headerStatus[i] = getRomoval(headerStatus[i],',', int) # {} içerisindeki {}'i kaldır ve {} olarak geri al.
	return headerStatus

def getRomoval(inside_obj, find_obj=' ', return_type=None):
	if defStatus:
		print(f'Process: {getRomoval.__name__}')

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
	if defStatus:
		print(f'Process: {getUsername.__name__}')

	profileUserName = profile_dom.find("h1", {"class":"header-title"})
	return profileUserName.text.strip()

def getDisplayName(profile_dom):
	if defStatus:
		print(f'Process: {getDisplayName.__name__}')
	
	profileDisplayName = profile_dom.find("span", {"class":"header-title-display-name"})
	return profileDisplayName.text.strip()

def getCurrentSession(get_length=None):
	if defStatus:
		print(f'Process: {getCurrentSession.__name__}')
	
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
	if defStatus:
		print(f'Process: {getUserFollowingCount.__name__}')

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
	if defStatus:
		print(f'Process: {getUserFollowersCount.__name__}')
	
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
	if defStatus:
		print(f'Process: {getUserFollowing.__name__}')

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
	if defStatus:
		print(f'Process: {getUserFollowers.__name__}')

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
	if defStatus:
		print(f'Process: {getUserGT.__name__}')

	userGt = {}
	for userName in following_box:
		if userName in followers_box:
			userGt[userName] = True
		else:
			userGt[userName] = False
	return userGt

def getProfileSince(profile_dom):
	if defStatus:
		print(f'Process: {getProfileSince.__name__}')

	profileSince = profile_dom.find("span", {"class":"header-scrobble-since"})
	return profileSince.text.partition("• scrobbling since")[2].strip() # Sonrasını al

def getLastScrobs(profile_dom, get_count):
	if defStatus:
		print(f'Process: {getLastScrobs.__name__}')

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
	if defStatus:
		print(f'Process: {getDictValueCount.__name__}')

	return sum(key for _ in dicti.values() if _)

def getFollowDict(following_box, followers_box, followback_box):
	if defStatus:
		print(f'Process: {getFollowDict.__name__}')

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
	if defStatus:
		print(f'Process: {getTodayListening.__name__}')

	today = date.today()
	today = today.strftime("%Y-%m-%d")
	pageNo = 1
	todayTracks = {}
	todayArtist = []
	while True:
		todayListeningUrl = f'https://www.last.fm/user/{user_name}/library/artists?from={today}&rangetype=1day&page={pageNo}'
		todayListeningDom = getDom(getResponse(todayListeningUrl))
		try:
			todayListeningDomTracks = todayListeningDom.find_all("tr", "chartlist-row")
			for i in todayListeningDomTracks:
				artistName = i.find("td","chartlist-name").text.strip()
				artistCount = i.find("span","chartlist-count-bar-value").text.strip()
				todayArtist.append(artistName)
				todayTracks[artistName] = artistCount[:artistCount.rfind(' ')] # Boşluğun hemen öncesine kadar al. (123 scrobbles)
		except:
			pass # Bir hata gerçekleşirse dict boş gönderilir.

		if todayListeningDom.find("li", {"class": "pagination-next"}):
			pageNo += 1
		else:
			return todayArtist, todayTracks

def getArtistAllTimeCount(user_name, artists_box, process_loop=None): # total contribution to artists listened to today
	if defStatus:
		print(f'Process: {getArtistAllTimeCount.__name__}')

	jsonDir = 'backups/json'
	jsonName = f'{user_name}-alltime-{appSession}.json'
	jsonPath = f'{jsonDir}/{jsonName}'

	if not os.path.exists(jsonPath): # ico not exist
		if isinstance(artists_box, dict): # Sözlük gönderildiyse keys ile işlem yapılır
			artists_box = artists_box.keys()
		
		artistCount = {}
		for artistName in artists_box:
			if process_loop != None:
				if process_loop != 0:
					process_loop -= 1
				else:
					break

			artistCountUrl = f'https://www.last.fm/user/{user_name}/library/music/{artistName}?date_preset=ALL'
			artistCountDom = getDom(getResponse(artistCountUrl))
			artistScrobbles = artistCountDom.find_all("p", {"class":"metadata-display"})[0].text
			artistCount[artistName] = artistScrobbles # library_header_title, metadata_display

		doDictJsonSave(jsonName, artistCount)
		print('new')
	else:
		with open(jsonPath) as jsonFile:
			artistCount = json.load(jsonFile)
		print('old')
	return artistCount	

def getDictKeyNo(key, d): # key, dict
	if defStatus:
		print(f'Process: {getDictKeyNo.__name__}')

	dictKeys = d.keys()
	dictKeysList = list(dictKeys)
	keyIndexNo = dictKeysList.index(key) + 1
	return keyIndexNo

## -- PRINT DEFS --
def printDefStatus():
	pass # Not Yet.

def printStatus(upi_dict, refresh_bool): # printStatus(userProfileInfos, react)
	print(f'\n*** {time.strftime("%H:%M:%S")} ***')
	upi_acot = upi_dict['artist_count_alltime']
	upi_lts = upi_dict["last_tracks"]
	upi_sc = upi_dict["scrobbled_count"]
	upi_ac = upi_dict["artists_count"]
	upi_lc = upi_dict["likes_count"]
	upi_tl = upi_dict['today_listening']
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
	printTodayAllTime(upi_acot, upi_tl) # Total, Today Prints
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

appSession = debugLog(True)
getSearchUser(input('Username: @'))

