import os
import time
from datetime import date, datetime
import requests
from bs4 import BeautifulSoup
from win10toast import ToastNotifier

def searchUser(_username, _statusPrint=True, _react=True, _fw=True):
	if _username:
		urlDict, domsDict, responsesDict = {},{},{}
		urlDict['user_url'] = "https://www.last.fm/user/" + _username
		profileResponseCode = getResponse(urlDict['user_url'])
		# Get profile page
		if profileResponseCode.status_code in range(200,299):
			responsesDict["profile_dom"] = profileResponseCode
		# Get follow pages
		if _fw:
			urlDict['fallowing_url'] = urlDict['user_url']+'/following'
			urlDict['fallowers_url'] = urlDict['user_url']+'/followers'
			responsesDict["following_dom"] = getResponse(urlDict['fallowing_url'])
			responsesDict["followers_dom"] = getResponse(urlDict['fallowers_url'])
		# Get response doms
		for responseKey, responseValue in responsesDict.items():
			domsDict[responseKey] = getDom(responseValue)
		userProfileInfos = getProfileInfos(domsDict) # Get profile infos
		# Prints
		if _statusPrint:
			printStatus(userProfileInfos, _react)
		return userProfileInfos

def getResponse(_url):
	return requests.get(_url)

def getDom(responsesCode):
	return BeautifulSoup(responsesCode.content, 'html.parser')

def getProfileInfos(_domsDict):
	profileDict = {}
	if "profile_dom" in _domsDict:
		profileDom = _domsDict["profile_dom"]
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
		profileDict['artist_count_alltime'] = getArtistAllTimeCount(profileDict["username"], profileDict['artists_today'], 10) # Need: username, [artistsList]
	
	if all(key in _domsDict for key in ('following_dom', 'followers_dom')): # Ayrı bir post isteği gerekir.
		followsDom = [_domsDict["following_dom"], _domsDict["followers_dom"]]
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

def printStatus(upi, _react): # printStatus(userProfileInfos, _react)
	print(f'\n*** {time.strftime("%H:%M:%S")} ***')
	upi_acot = upi['artist_count_alltime']
	upi_lts = upi["last_tracks"]
	upi_sc = upi["scrobbled_count"]
	upi_ac = upi["artists_count"]
	upi_lc = upi["likes_count"]
	upi_tl = upi['today_listening']
	upi_bi = upi["background_image"]
	upi_ua = upi["user_avatar"]
	upi_ss = upi["scrobbling_since"]
	upi_dn = upi["display_name"]
	upi_un = upi["username"]
	if "follows" in upi:
		# Following
		upi_fgc = upi["follows"]["following_counts"]
		upi_fg = upi["follows"]["following"]
		# Followers
		upi_fsc = upi["follows"]["followers_counts"]
		upi_fs = upi["follows"]["followers"]
		# Followback
		upi_fb = upi["follows"]["following_gt"]
		upi_fbc = upi["follows"]["fb_count"]
		upi_nofbc = upi["follows"]["no_fb_count"]
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

	if _react:
		time.sleep(5) # 5 sec
		checkChange(upi, upi_un)

def checkChange(currentProfileData, _username): # checkChange(upi, upi_un)
	while True:	
		newProfileData = searchUser(_username, False) 	
		if currentProfileData != newProfileData:
			if newProfileData["scrobbled_count"] != currentProfileData["scrobbled_count"]:

				# Get notifier data
				if currentProfileData["last_tracks"] != None:
					song_name = currentProfileData["last_tracks"][0][0]
					artist_name = currentProfileData["last_tracks"][0][1]
					artistCountUrl = f'https://www.last.fm/user/{_username}/library/music/{artist_name}?date_preset=ALL'
					artistCountDom = getDom(getResponse(artistCountUrl))
					artistCount = artistCountDom.find_all("p", {"class":"metadata-display"})[0].text
					msgLastTrack = f'\nLast track: {song_name} | {artist_name} ({artistCount})'
				else:
					msgLastTrack = ''

				runNotifier(f'Profile: {currentProfileData["display_name"]} (@{currentProfileData["username"]})',
				f'Current Scrobbles: {newProfileData["scrobbled_count"]}{msgLastTrack}')

			currentProfileData = newProfileData
			printStatus(currentProfileData, True)

def getFaviconUrl(_url): # Belirtilen sayfadaki iconu çeker.
	iconResponse = getResponse(_url)
	if iconResponse.status_code in range(200,299):
		iconDom = getDom(iconResponse)
		iconUrl = iconDom.find("link", {"rel":"icon"})['href']
		return iconUrl # return '/static/images/favicon.702b239b6194.ico'
	return False

def runNotifier(l1=' ', l2=' '):
	ico_domain = 'https://www.last.fm'
	img_dir = 'images/media'
	img_name = 'lastfm.ico'
	img_path = f'{img_dir}/{img_name}'

	if not os.path.exists(img_path): # ico not exist
		img_url = f'{ico_domain}{getFaviconUrl(ico_domain)}'
		downloadImage(img_dir, img_name, img_url)

	notifier = ToastNotifier()
	notifier.show_toast(l1, l2, icon_path=img_path)

def downloadImage(img_dir, img_name, img_url, mode='wb'): # downloadImage('images/avatars', 'MyAvatar', 'AvatarUrl')
	if img_dir != None:
		dirCreate(img_dir)
		img_name = f'{img_dir}/{img_name}'

	if '.' not in img_name: # Dosya uzantısı isimde yoksa url sonundan alınır.
		img_name = f"{img_name}{img_url[img_url.rfind('.'):]}"

	if not os.path.exists(img_name):
		img_response = getResponse(img_url)
		img_content = img_response.content
		with open(img_name, mode) as handler:
			handler.write(img_content)
		alreadyFile = False
	else:
		alreadyFile = True
	return alreadyFile 

def getBackgroundImage(_profileDom):
	try:
		backgroundImageUrl = _profileDom.find("div", {"class":"header-background header-background--has-image"})["style"][22:-2]
		downloadImage('images/background', f'{getUsername(_profileDom)}-bg-{getCurrentSession()}', backgroundImageUrl)
	except:
		backgroundImageUrl = "No Background (Last.fm default background)"
	return backgroundImageUrl # Replaced: background-image: url();

def getUserAvatar(_profileDom):
	defaultAvatarId = "818148bf682d429dc215c1705eb27b98"
	# defaultImageUrl:("https://lastfm.freetls.fastly.net/i/u/avatar170s/818148bf682d429dc215c1705eb27b98.png") 
	profileAvatarUrl = _profileDom.find("meta", property="og:image")["content"]
	if defaultAvatarId in profileAvatarUrl:
		profileAvatarUrl = "No Avatar (Last.fm default avatar)"
	else:
		downloadImage('images/avatar', f'{getUsername(_profileDom)}-av-{getCurrentSession()}', profileAvatarUrl)
	return profileAvatarUrl 

def dirCreate(dirName):
	dirList = dirName.split('/')
	for d in dirList:
		try:
			if d == dirList[-1] :
				os.mkdir(dirName)
			else:
				os.mkdir(d) # Directory Created
		except FileExistsError:
			pass # Directory already exists

def getHeaderStatus(_profileDom):
	headerStatus = [0, 0, 0]
	headers = _profileDom.find_all("div", {"class": "header-metadata-display"})
	for i in range(len(headers)):
		headerStatus[i] = headers[i].text.strip()
		try:
			headerStatus[i] = headerStatus[i].replace(",","")
		except:
			pass
	return headerStatus

def getUsername(_profileDom):
	profileOwner = _profileDom.find("h1", {"class":"header-title"})
	return profileOwner.text.strip()

def getDisplayName(_profileDom):
	profileDisplayName= _profileDom.find("span", {"class":"header-title-display-name"})
	return profileDisplayName.text.strip()

def getCurrentSession():
	return datetime.now().strftime('%Y%m%d')

def getUserFollowingCount(_followingDom):
	while True:
		try:
			topHeader = _followingDom.find("h1", {"class":"content-top-header"}).text # Path
			userFollowing = topHeader[topHeader.find("(")+1:topHeader.find(")")] # Parantez arası değeri
			try:
				userFollowing = int(userFollowing) # Sayı değilse
			except:
				userFollowing = 0
			return userFollowing
		except:
			continue	

def getUserFollowersCount(_followersDom):
	while True:
		try:
			topHeader = _followersDom.find("h1", {"class":"content-top-header"}).text # Path
			userFollowers = topHeader[topHeader.find("(")+1:topHeader.find(")")] # Parantez arası değeri
			try:
				userFollowers = int(userFollowers) # Sayı değilse
			except:
				userFollowers = 0
			return userFollowers
		except:
			continue

def getUserFollowing(_followingDom):
	followingDict = {}
	currentFollowingPageDom = _followingDom
	username = getUsername(currentFollowingPageDom)
	while True:
		following = currentFollowingPageDom.find_all(attrs={"class": "user-list-name"})
		for f in following: # Bir sayfada max 30
			f_username = f.text.strip()
			followingDict[f_username] = True
		if currentFollowingPageDom.find("li", {"class": "pagination-next"}):
			pageNo = currentFollowingPageDom.find("li", {"class": "pagination-next"})
			currentFollowingPageUrl = f"https://www.last.fm/user/{username}/following{pageNo.a['href']}"
			currentFollowingPageDom = getDom(getResponse(currentFollowingPageUrl))
		else:
			return followingDict
	
def getUserFollowers(_followersDom):
	followersDict = {}
	currentFollowersPageDom = _followersDom
	username = getUsername(currentFollowersPageDom)
	while True:
		followers = currentFollowersPageDom.find_all(attrs={"class": "user-list-name"})
		for f in followers: # Bir sayfada max 30
			f_username = f.text.strip()
			followersDict[f_username] =  True
		if currentFollowersPageDom.find("li", {"class": "pagination-next"}):
			pageNo = currentFollowersPageDom.find("li", {"class": "pagination-next"})
			currentFollowersPageUrl = f"https://www.last.fm/user/{username}/followers{pageNo.a['href']}"
			currentFollowersPageDom = getDom(getResponse(currentFollowersPageUrl))
		else:
			return followersDict

def getUserGT(_following, _followers):
	user_gt = {}
	for user in _following:
		if user in _followers:
			user_gt[user] = True
		else:
			user_gt[user] = False
	return user_gt

def getProfileSince(_profileDom):
	profileSince = _profileDom.find("span", {"class":"header-scrobble-since"})
	return profileSince.text.partition("• scrobbling since")[2].strip() # Sonrasını al

def getLastScrobs(_profileDom, _x):
	lastTracks = {}
	for x in range(_x): # X kadar al.
		try:
			lastTrackDom = _profileDom.find_all("tr", {"class":"chartlist-row chartlist-row--with-artist chartlist-row--with-buylinks js-focus-controls-container"})[x]
			lastTrackSongName = lastTrackDom.find("td", {"class":"chartlist-name"}).text.strip()
			lastTrackArtist = lastTrackDom.find("td", {"class":"chartlist-artist"}).text.strip()
			lastTrackDate = lastTrackDom.find("td", {"class":"chartlist-timestamp"}).text.strip()
			lastTracks[x] = [lastTrackSongName,lastTrackArtist,lastTrackDate]
		except Exception as e:
			lastTracks =  None
			break
	return lastTracks

def getDictValueCount(dicti, key):
	return sum(key for _ in dicti.values() if _)

def followDict(_following, _followers, _fb):
	f = {}
	for username in _following:
		f[username] = {}
		f[username]['following'] = True
		if username in _followers:
			f[username]['follower'] = True # 2. true takip ettiği / false etmediği
			f[username]['user_fb'] = _fb[username]
		else:
			f[username]['follower'] = False
			f[username]['user_fb'] = _fb[username]
		f[username]['link'] = f'https://last.fm/user/{username}'
	for username in _followers:
		f[username] = {}
		f[username]['follower'] = True
		if username in _following:
			f[username]['following'] = True # 2. true takip ettiği / false etmediği
			f[username]['user_fb'] = _fb[username]
		else:
			f[username]['following'] = False
			f[username]['user_fb'] = False
		f[username]['link'] = f'https://last.fm/user/{username}'
	return f

def getTodayListening(_username):
	today = date.today()
	today = today.strftime("%Y-%m-%d")
	pageNo = 1
	todayTracks = {}
	todayArtist = []
	while True:
		todayListeningUrl = f'https://www.last.fm/user/{_username}/library/artists?from={today}&rangetype=1day&page={pageNo}'
		todayListeningDom = getDom(getResponse(todayListeningUrl))
		try:
			todayListeningDomTracks = todayListeningDom.find_all("tr", "chartlist-row")
			for i in todayListeningDomTracks:
				artist_name = i.find("td","chartlist-name").text.strip()
				artist_count = i.find("span","chartlist-count-bar-value").text.strip()
				todayArtist.append(artist_name)
				todayTracks[artist_name] = artist_count[:artist_count.rfind(' ')] # Boşluğun hemen öncesine kadar al. (123 scrobbles)
		except:
			pass # Bir hata gerçekleşirse dict boş gönderilir.

		if todayListeningDom.find("li", {"class": "pagination-next"}):
			pageNo += 1
		else:
			return todayArtist, todayTracks

def getArtistAllTimeCount(_username, _artist, process_loop=None):
	if isinstance(_artist, dict): # Sözlük gönderildiyse keys ile işlem yapılır
		_artist = _artist.keys()

	artistCount = {}
	for artist_name in _artist:
		if process_loop != None:
			if process_loop != 0:
				process_loop -= 1
			else:
				break
		artistCountUrl = f'https://www.last.fm/user/{_username}/library/music/{artist_name}?date_preset=ALL'
		artistCountDom = getDom(getResponse(artistCountUrl))
		artist_scrobbles = artistCountDom.find_all("p", {"class":"metadata-display"})[0].text
		artistCount[artist_name] = artist_scrobbles # library_header_title, metadata_display
	return artistCount

def printTodayAllTime(_alltime, _today):
	print(f'\nYour total contribution to the artist today;')
	artist_rank = 1
	for artist_name, today_count in _today.items():
		try:
			alltime_count = ' ' + _alltime[artist_name]
		except:
			alltime_count = ''
		print(f'[{artist_rank}]: {artist_name} - {alltime_count} (Today: {today_count})')
		artist_rank += 1

def printTodayListening(_todayTracks):
	if bool(_todayTracks): # Dict boş dönmezse
		print('Today Listening Artists;')
		artist_rank = 1
		for artist_name, artist_count in _todayTracks.items():
			print(f'{artist_rank}: {artist_name} ({artist_count})')
			artist_rank += 1
	else: # Dict boş ise false döndürür.
		print('Bugün dinlenmedi.')

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

def printDictValue(_dict):
	for key, value in _dict.items():
		print(f'{key} ({value})')

def printus(dict_name, user_dict, count_dict):
	print(f'{dict_name}: ({count_dict});')
	for user,b in user_dict.items(): # user, bool
		print(f'[{b}]: {user}')

def printFollowStat(fg, fs, fb, fgc, fsc, fbc, nofbc):
	print(f'\nFollows;')
	if False:
		printus("Following", fg, fgc) # Following
		printus("Followers", fs, fsc) # Followers
		printus("Followback", fb, fbc)

	print(f"Following: {fgc}, Followers: {fsc}, Followback: {fbc}")
	if fgc != fbc:
		print(f"Users who don't follow you back ({nofbc});")
		f = followDict(fg, fs, fb)
		for user in f:
			if f[user]['following'] == True and f[user]['follower'] == False:
				print(f"FG:[{f[user]['following']}], FR:[{f[user]['follower']}], FB:[{f[user]['user_fb']}] | {f[user]['link']}, @{user}")
	elif fgc != 0:
		print(f'{fbc} users you follow are following you.')

searchUser(input('Username: @'))

