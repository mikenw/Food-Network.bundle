BASE_URL = 'http://www.foodnetwork.com'
FULLEP_PAGE = 'http://www.foodnetwork.com/videos/players/food-network-full-episodes.html'
VID_PAGE = 'http://www.foodnetwork.com/videos.html'
TOP_VID_PAGE = 'http://www.foodnetwork.com/videos/players/food-network-top-food-videos.html'
SHOW_PAGE = 'http://www.foodnetwork.com/videos/players/food-network-full-episodes.%s.html'
SEARCH = 'http://www.foodnetwork.com/search/search-results.videos.html?searchTerm=%s&page='
RE_JSON = Regex('\{"channels\":.+?\}\]\}\]}', Regex.DOTALL)

####################################################################################################
def Start():

    ObjectContainer.title1 = 'Food Network'
    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler("/video/foodnetwork", "Food Network")
def MainMenu():

    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(ShowFinder, title='Full Episodes', url=FULLEP_PAGE), title='Full Episodes'))
    oc.add(DirectoryObject(key=Callback(VidFinder, title='All Videos'), title='All Videos'))
    oc.add(InputDirectoryObject(key=Callback(Search), title='Search for Videos', summary="Click here to search for videos", prompt="Search for the videos"))
    return oc

####################################################################################################
# This function produces a list of more sections, shows, or videos that are listed below the playlist on a page
@route('/video/foodnetwork/showfinder')
def ShowFinder(title, url):

    oc = ObjectContainer(title2 = title)
    content = HTTP.Request(url).content
    
    # When using the ShowFinder function to pull the list of shows from the FULLEP_PAGE URL, one show is not listed
    # because it is in the player of the page, so we have to pull the info for that show out of the player json so it 
    # will be included in the list of Full Episode Shows. Any other pages sent to this function has already named and
    # produced the playlist for the show in the player.
    if url==FULLEP_PAGE:
        # Use the json to produce the first show that is only listed in the player    
        try: json_data = RE_JSON.search(content).group(0)   
        except: json_data = None  
        if json_data:
            json = JSON.ObjectFromString(json_data)
            show_title = json['channels'][0]['title']
            channel_id = json['channels'][0]['videos'][0]['cmsid']
            show_url = SHOW_PAGE %channel_id
            oc.add(DirectoryObject(key=Callback(ShowBrowse, url=show_url, title=show_title), title=show_title))
    
    page = HTML.ElementFromString(content)
        
    for tag in page.xpath('//ul/li/div[@class="group"]'):
        title = tag.xpath(".//h4//text()")[0].replace(' Full Episodes','').replace(' -', '')
        url = BASE_URL + tag.xpath('.//a/@href')[0]
        oc.add(DirectoryObject(key=Callback(ShowBrowse, url=url, title=title), title=title))

    return oc

####################################################################################################
# This function produces a list of headers from the Video page
@route('/video/foodnetwork/vidfinder')
def VidFinder(title):

    oc = ObjectContainer(title2 = title)
    # This directory below pick up the playlist on the Top Video page
    oc.add(DirectoryObject(key=Callback(ShowBrowse, title='Top Food Videos', url=TOP_VID_PAGE), title='Top Food Videos'))
    page = HTML.ElementFromURL(VID_PAGE, cacheTime = CACHE_1DAY)

    for tag in page.xpath('//section/header/h5/a'):
        title = tag.xpath(".//text()")[0]
        more_link = BASE_URL + tag.xpath('./@href')[0]
        # Make sure it is a video page link
        if '/videos/' in more_link:
            # Send the Full Episode page to create a list of shows with full episodes
            if 'food-network-full-episodes' in more_link:
                oc.add(DirectoryObject(key=Callback(ShowFinder, title=title, url=more_link), title=title))
            # Send the rest to pull the videos for the page with the ShowBrowse function
            else:
                oc.add(DirectoryObject(key=Callback(ShowBrowse, title=title, url=more_link), title=title))
        # If the section does not have a more link, send it to the VidSection to be broken down further
        else:
            continue
            
    return oc

####################################################################################################
# This function produces a list of videos for a URL using the json video list in the player of each page
@route('/video/foodnetwork/showbrowse')
def ShowBrowse(url, title = None):

    oc = ObjectContainer(title2=title)
    content = HTTP.Request(url).content
    page = HTML.ElementFromString(content)
    
    # To prevent any issues with URLs that do not contain the video playlist json, we put the json pull in a try/except
    try:
        json_data = RE_JSON.search(content).group(0)
        #Log('the value of json_data is %s' %json_data)
        json = JSON.ObjectFromString(json_data)
    except: json = None
    #Log('the value of json is %s' %json)
    
    if json:
        for video in json['channels'][0]['videos']:
            title = video['title'].replace('&amp,', '&')
            #title = video['title']
            vid_url = video['embedUrl'].replace('.embed', '')
            # found a few recipes in the video lists
            if '/recipes/' in vid_url:
                continue
            duration = video['length']
            desc = video['description']
            thumb = video['thumbnailUrl'].replace('_92x69.jpg', '_480x360.jpg')

            # A couple shows include a season in the name, but they have stopped putting an episode number on shows, so there is no point in 
            # pulling videos as EpisodeObjects. We just keep the Season info in the title and if there is an episode number, it will be in the title
            oc.add(
                VideoClipObject(
                    url = vid_url,
                    title = title,
                    duration = duration,
                    summary = desc,
                    thumb = Resource.ContentsOfURLWithFallback(url=thumb)
                )
            )

    else:
        # If there is not a video player json, see if there is a video page navigation link on the page and send that back to this function
        try:
            video_url = BASE_URL + page.xpath('//nav/ul/li/a[@title="Videos"]/@href')[0]
            video_title = title + ' Videos'
            oc.add(DirectoryObject(key=Callback(ShowBrowse, title=video_title, url=video_url), title=video_title))
        except:
            return ObjectContainer(header=L('Empty'), message=L('This page does not contain any video'))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list right now.")
    else:
        return oc

####################################################################################################
@route('/video/foodnetwork/search', page=int)
def Search(query='', page=1):

    oc = ObjectContainer()
    local_url = SEARCH %String.Quote(query, usePlus = True) + str(page)
    html = HTML.ElementFromURL(local_url)

    for video in html.xpath('//article[@class="video"]'):
        title = video.xpath("./header/h6/a")[0].text
        summary = video.xpath("./p")[0].text
        url = BASE_URL + video.xpath("./header/h6/a/@href")[0]
        duration_list = video.xpath(".//ul/li//text()")
        duration = duration_list[len(duration_list)-1]
        duration = Datetime.MillisecondsFromString(duration.split('(')[1].split(')')[0])
        thumb = video.xpath(".//img/@src")[0].replace('_126x71.jpg', '_480x360.jpg')
        oc.add(VideoClipObject(
            url = url,
            title = title,
            summary = summary,
            duration = duration,
            thumb = Resource.ContentsOfURLWithFallback(url=thumb)
        ))

    # Paging code. 
    # There is a span code only on previous and next page so if it has an anchor it has a next page
    page_list = video.xpath('//div[@class="pagination"]/ul/li/a/span//text()')
    if page_list and 'Next' in page_list[len(page_list)-1]:
        page = page + 1
        oc.add(NextPageObject(key = Callback(Search, query=query, page=page), title = L("Next Page ...")))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list right now.")
    else:
        return oc
