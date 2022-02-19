from bs4 import BeautifulSoup
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
		profileDom 									= _domsDict["profile_dom"]
		profileDict["username"] 					= getUsername(profileDom)
		profileDict["user_avatar"] 					= getUserAvatar(profileDom)
		profileDict["display_name"] 				= getDisplayName(profileDom)
		profileDict["scrobbling_since"] 			= getProfileSince(profileDom)
		profileDict["last_tracks"] 					= getLastScrobs(profileDom, 3)
		profileDict["background_image"] 			= getBackgroundImage(profileDom)
		profileDict["scrobbled_count"]				= int(getHeaderStatus(profileDom)[0].replace(",","")) # Profile Header: Scrobbles
		profileDict["artists_count"]				= int(getHeaderStatus(profileDom)[1].replace(",","")) # Profile Header: Artist Count
		profileDict["likes_count"]					= int(getHeaderStatus(profileDom)[2].replace(",","")) # Profile Header: Loved Tracks
	if all(key in _domsDict for key in ('following_dom', 'followers_dom')): # Ayrı bir post isteği gerekir.
		followsDom									= [_domsDict["following_dom"], _domsDict["followers_dom"]]
		profileDict["follows"] = {}
		profileDict["follows"]["following"] 		=  getUserFollowing(followsDom[0]) # Following
		profileDict["follows"]["followers"] 		=  getUserFollowers(followsDom[1]) # Followers
		profileDict["follows"]["following_counts"] 	=  getUserFollowingCount(followsDom[0]) # Following
		profileDict["follows"]["followers_counts"] 	=  getUserFollowersCount(followsDom[1]) # Followers
	return profileDict

def printStatus(_profileDict, _react, _username):
	print(f'\n{time.strftime("%H:%M:%S")}')
	print(f'Profile: {_profileDict["display_name"]} (@{_profileDict["username"]})')
	print(f'Avatar: {_profileDict["user_avatar"]}')
	print(f'Background: {_profileDict["background_image"]}')
	print(f'Scrobbles: {_profileDict["scrobbled_count"]} | ', end="")
	print(f'Artists: {_profileDict["artists_count"]} | ', end ="")
	print(f'Loved Tracks: {_profileDict["likes_count"]}'),
	print(f'Scrobbling Since: {_profileDict["scrobbling_since"]}')

	if  _profileDict['last_tracks'] != None:
		print(f'Recent Tracks;', end="")
		recentTracks = _profileDict['last_tracks']
		for trackNo in recentTracks:
			print(f'\n[{trackNo+1}]:', end=" ")
			for trackValueNo in range(len(recentTracks[trackNo])):
				print(recentTracks[trackNo][trackValueNo], end= " | ")
		else:
			print()
	elif _profileDict["scrobbled_count"] > 0:
		print("Recent Tracks: realtime tracks is private.")

	if "follows" in _profileDict:
		print(f'Following Count: {_profileDict["follows"]["following_counts"]}, ', end="")
		print(f'Followers Count: {_profileDict["follows"]["followers_counts"]}')
		for user,adress in _profileDict["follows"]["following"].items():
			print(f'Following: @{user}:{adress}')
		for user,adress in _profileDict["follows"]["followers"].items():
			print(f'Follower: @{user}:{adress}')
	
	if _react:
		time.sleep(5)
		checkChange(_profileDict, _username)

def checkChange(currentProfileData, _username):
	while True:	
		newProfileData = searchUser(_username, False) 	
		if currentProfileData != newProfileData:
			currentProfileData = newProfileData
			printStatus(currentProfileData, True, _username)

def getHeaderStatus(_profileDom):
	headerStatus = [0, 0, 0]
	headers = _profileDom.find_all("div", {"class": "header-metadata-display"})
	for i in range(len(headers)):
		headerStatus[i] = headers[i].text.strip()
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
			break
		except:
			continue
	return userFollowing

def getUserFollowersCount(_followersDom):
	while True:
		try:
			topHeader = _followersDom.find("h1", {"class":"content-top-header"}).text # Path
			userFollowers = topHeader[topHeader.find("(")+1:topHeader.find(")")] # Parantez arası değeri
			break
		except:
			continue
	return userFollowers

def getUserFollowing(_followingDom):
	followingDict = {}
	currentFollowingPageDom = _followingDom
	while True:
		following = currentFollowingPageDom.find_all(attrs={"class": "user-list-name"})
		for f in following: # Bir sayfada max 30
			f_username = f.text.strip()
			followingDict[f_username] = f'https://www.last.fm/user/{f_username}'
		if currentFollowingPageDom.find("li", {"class": "pagination-next"}):
			pageNo = currentFollowingPageDom.find("li", {"class": "pagination-next"})
			currentFollowingPageUrl = f"https://www.last.fm/user/{f_username}/following{pageNo.a['href']}"
			currentFollowingPageDom = getDom(getResponse(currentFollowingPageDom))
		else:
			followingCount = len(followingDict)
			followingDict['statics'] = {}
			followingDict['statics']['count'] = followingCount
			return followingDict
	

def getUserFollowers(_followersDom):
	followersDict = {}
	currentFallowersPageDom = _followersDom
	while True:
		followers = currentFallowersPageDom.find_all(attrs={"class": "user-list-name"})
		for f in followers: # Bir sayfada max 30
			f_username = f.text.strip()
			followersDict[f_username] = f'https://www.last.fm/user/{f_username}'
		if currentFallowersPageDom.find("li", {"class": "pagination-next"}):
			pageNo = currentFallowersPageDom.find("li", {"class": "pagination-next"})
			currentFallowersPageUrl = f"https://www.last.fm/user/{f_username}/followers{pageNo.a['href']}"
			currentFallowersPageDom = getDom(getResponse(currentFallowersPageUrl))
		else:
			followersCount = len(followersDict)
			followersDict['statics'] = {}
			followersDict['statics']['count'] = followersCount
			return followersDict

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

searchUser(input('Username: @'))

