from bs4 import BeautifulSoup
from win10toast import ToastNotifier
import requests
import time

def searchUser(_username, _statusPrint=True, _react=True, _fw=True):
	if _username:
		urlDict, domsDict, responsesDict = {},{},{}
		urlDict['user_url'] = "https://www.last.fm/user/" + _username
		profileResponseCode = getResponse(urlDict['user_url'])
		if profileResponseCode.status_code in range(200,299):
			responsesDict["profile_dom"] = profileResponseCode

		if _fw:
			urlDict['fallowing_url'] = urlDict['user_url']+'/following'
			urlDict['fallowers_url'] = urlDict['user_url']+'/followers'
			responsesDict["following_dom"] = getResponse(urlDict['fallowing_url'])
			responsesDict["followers_dom"] = getResponse(urlDict['fallowers_url'])

		for responseKey, responseValue in responsesDict.items():
			domsDict[responseKey] = getDom(responseValue)

		userProfileInfos = getProfileInfos(domsDict)

		if _statusPrint:
			printStatus(userProfileInfos, _react, _username)

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
		profileDict['today_artists'], profileDict['today_listening'] = getTodayListening(profileDict["username"])
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

def printStatus(_profileDict, _react, _username): # _profileDict, _react, _username
	print(f'\n*** {time.strftime("%H:%M:%S")} ***')
	# Follow Prints
	if "follows" in _profileDict:
		# Following
		pd_followingCounts = _profileDict["follows"]["following_counts"]
		pd_following = _profileDict["follows"]["following"]
		# Followers
		pd_followersCounts = _profileDict["follows"]["followers_counts"]
		pd_followers = _profileDict["follows"]["followers"]
		# Followback
		pd_followingFB = _profileDict["follows"]["following_gt"]
		pd_fbCounts = _profileDict["follows"]["fb_count"]
		pd_nofbCounts = _profileDict["follows"]["no_fb_count"]
		print(f'\nFollows;')
		# Prints
		if False:
			printus("Following", pd_following, pd_followingCounts) # Following
			printus("Followers", pd_followers, pd_followersCounts) # Followers
			printus("Followback", pd_followingFB, pd_fbCounts)
		print(f"Following: {pd_followingCounts}, Followers: {pd_followersCounts}, Followback: {pd_fbCounts}")
		if pd_followingCounts != pd_fbCounts:
			print(f"Users who don't follow you back ({pd_nofbCounts});")
			f = followDict(pd_following, pd_followers, pd_followingFB)
			for user in f:
				if f[user]['following'] == True and f[user]['follower'] == False:
					print(f"FG:[{f[user]['following']}], FR:[{f[user]['follower']}], FB:[{f[user]['user_fb']}] | {f[user]['link']}, @{user}")
		else:
			print(f'{pd_fbCounts} users you follow are following you.')
	
	# Last Tracks Prints
	if _profileDict['last_tracks'] != None:
		print(f'\nRecent Tracks;', end='')
		recentTracks = _profileDict['last_tracks']
		for trackNo in recentTracks:
			print(f'\n[{trackNo+1}]:', end=" ")
			for trackValueNo in range(len(recentTracks[trackNo])):
				print(recentTracks[trackNo][trackValueNo], end= " | ")
		else:
			print()
	elif _profileDict["scrobbled_count"] > 0:
		print("\nRecent Tracks: realtime tracks is private.")

	printTodayListening(_profileDict['today_listening']) # Need: {artist:artist_count}
	getArtistAllTimeCount(_username, _profileDict['today_artists']) # Need: username, [artistsList]
	
	# Adresses
	print(f'\nProfile: {_profileDict["display_name"]} (@{_profileDict["username"]})')
	print(f'Scrobbling Since: {_profileDict["scrobbling_since"]}')
	print(f'Avatar: {_profileDict["user_avatar"]}')
	print(f'Background: {_profileDict["background_image"]}')
	# Headers
	print(f'Scrobbles: {_profileDict["scrobbled_count"]} | ', end="")
	print(f'Artists: {_profileDict["artists_count"]} | ', end ="")
	print(f'Loved Tracks: {_profileDict["likes_count"]}'),

	if _react:
		time.sleep(5) # 5 sec
		checkChange(_profileDict, _username)

def printus(dict_name, user_dict, pd_counts): # dict, counts
	print(f'{dict_name}: ({pd_counts});')
	for user,b in user_dict.items(): # user, bool
		print(f'[{b}]: {user}')

def checkChange(currentProfileData, _username):
	while True:	
		newProfileData = searchUser(_username, False) 	
		if currentProfileData != newProfileData:
			if newProfileData["scrobbled_count"] != currentProfileData["scrobbled_count"]:

				# Notifier
				if currentProfileData["last_tracks"] != None:
					song_name = currentProfileData["last_tracks"][0][0]
					artist_name = currentProfileData["last_tracks"][0][1]
					artistCountUrl = f'https://www.last.fm/user/{_username}/library/music/{artist_name}?date_preset=ALL'
					artistCountDom = getDom(getResponse(artistCountUrl))
					artistCount = artistCountDom.find_all("p", {"class":"metadata-display"})[0].text
					msgLastTrack = f'\nLast track: {song_name} | {artist_name} ({artistCount})'

				else:
					msgLastTrack = ''

				notifier = ToastNotifier()
				notifier.show_toast(
					f'Profile: {currentProfileData["display_name"]} (@{currentProfileData["username"]})',
					f'Current Scrobbles: {newProfileData["scrobbled_count"]}{msgLastTrack}',
					icon_path='lastfm.ico')

			currentProfileData = newProfileData
			printStatus(currentProfileData, True, _username)

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

def getBackgroundImage(_profileDom):
	try:
		backgroundImageUrl = _profileDom.find("div", {"class":"header-background header-background--has-image"})["style"][22:-2]
	except:
		backgroundImageUrl = "No Background (Last.fm default background)"
	return backgroundImageUrl # Replaced: background-image: url();

def getUsername(_profileDom):
	profileOwner = _profileDom.find("h1", {"class":"header-title"})
	return profileOwner.text.strip()

def getDisplayName(_profileDom):
	profileDisplayName= _profileDom.find("span", {"class":"header-title-display-name"})
	return profileDisplayName.text.strip()

def getUserAvatar(_profileDom):
	defaultAvatarId = "818148bf682d429dc215c1705eb27b98"
	# defaultImageUrl:("https://lastfm.freetls.fastly.net/i/u/avatar170s/818148bf682d429dc215c1705eb27b98.png") 
	profileAvatarUrl = _profileDom.find("meta", property="og:image")["content"]
	if defaultAvatarId in profileAvatarUrl:
		profileAvatarUrl = "No Avatar (Last.fm default avatar)"
	return profileAvatarUrl 

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
	from datetime import date
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

def printTodayListening(_todayTracks):
	if bool(_todayTracks): # Dict boş dönmezse
		print('Today Listening Artists;')
		artist_rank = 1
		for artist_name, artist_count in _todayTracks.items():
			print(f'{artist_rank}: {artist_name} ({artist_count})')
			artist_rank += 1
	else: # Dict boş ise false döndürür.
		print('Bugün dinlenmedi.')

def getArtistAllTimeCount(_username, _artist):
	if isinstance(_artist, dict): # Sözlük gönderildiyse keys ile işlem yapılır
		_artist = _artist.keys()

	artistCount = {}
	for artist_name in _artist:
		artistCountUrl = f'https://www.last.fm/user/{_username}/library/music/{artist_name}?date_preset=ALL'
		artistCountDom = getDom(getResponse(artistCountUrl))
		artist_scrobbles = artistCountDom.find_all("p", {"class":"metadata-display"})[0].text
		artistCount[artist_name] = artist_scrobbles # library_header_title, metadata_display
	return artistAllTimeCount
	
searchUser(input('Username: @'))

