from bs4 import BeautifulSoup
from urllib import request
import time

fullTeamUrl = 'http://37.59.41.28/7nationsrecompenses/7nationsfusion/DDE/detail.php'
sessionUrl = 'http://37.59.41.28/7nationsrecompenses/7nationsfusion/DDE/index.php' 
targetFile = 'dde24statsFull.csv'
siteFilename = 'dde24sitedata.csv'
noDriver = '--'


#testvars
teamPage = 'Detailed.html'
sessionPage = 'Ranking.html'



#testcases: 
#driving before very first cp '--' in diff, average, record, last
#driving before very first lap finished '--' in avg, rec, last
#driving before driver first cp '--' in 
#driving before driver first lap finished
def parseTeamRanking(soup):
  attributes = soup.find_all('td')
  rank = int(attributes[0].text)
  team = attributes[1].text
  cps = int(attributes[2].text)
  if attributes[3].text == '--': #before first cp
    cpDiff = 0
  else: 
    cpDiff = int(attributes[3].text)
  currentDriver = attributes[4].text
  
  if currentDriver == '--':
    return (rank, team, cps, cpDiff, currentDriver, 0, 0, 0, 0, -1)
  else:  
    sessionLength = timeFromString(attributes[5].text)
    sessionAverage = timeFromString(attributes[6].text)
    sessionRecord = timeFromString(attributes[7].text)
    lastLap = timeFromString(attributes[8].text)
    return [rank, team, cps, cpDiff, currentDriver, sessionLength, sessionAverage, sessionRecord, lastLap, -1]
  

def parseOverviewPage(rawText):
  soup = BeautifulSoup(rawText, "html5lib")
  playerTables = soup.find_all('table', attrs={"class":"features-table"})[:-2]
  
  ranking = []
  for table in playerTables:
    rows = table.find_all('tr')
    for row in rows:
      ranking.append(parseTeamRanking(row))
  return ranking

#TODO add error catching
#TODO check if result is string
#TODO check if response can be passed to bs4 directly
def getSite(url):
  result = ''
  response = request.urlopen(url)
  if response.status == 200:
    result = response.readall()
  return result
  
def parseTeam(teamCell):
  return teamCell.find('font', size="3").getText()
  
#TODO, completely handling milliseconds, getting them back out
def timeFromString(s):
  if s == '--': # catching most common empty value
    return 0
  totalTime = 0.0
  hms = s.split(':')
  for i in hms[:-1]:
    totalTime = (totalTime + int(i)) * 60
  totalTime += float(hms[-1])
    
  return totalTime
  

def parsePlayer(soup, playerID):
  attributes = soup.find_all('td')
  name = attributes[0].getText()
  
  cps = int(attributes[1].text) if attributes[1].text != '--' else 0
  
  # empty fields are set to 0 in timeFromString
  playTime = timeFromString(attributes[2].getText())
  lapRecord = timeFromString(attributes[3].getText())
  lapAverage = timeFromString(attributes[4].getText())
  return [name, cps, playTime, lapRecord, lapAverage, playerID]
  
def parsePlayerTable(soup):
  players = []
  playerID = 0
  for row in soup.find_all('tr')[1:-1]:
    if len(row.find_all('th')) == 0:
      players.append(parsePlayer(row, playerID))#.append(playerID))
      playerID += 1
  activePlayer = parsePlayer(soup.find_all('tr')[-1], -1)
  return players, activePlayer
  

def parseDetailedPage(teamPage):
  soup = BeautifulSoup(teamPage, "html5lib")

  #split up structure
  selection = soup.body.div.center
  teamTables = selection.find_all('table')
  
  #   each team has a table
  playerStats = {}
  sessionStats = []
  for teamTable in teamTables:
    teamName = parseTeam(teamTable.find("td"))
    playerStats[teamName], currentRacer = parsePlayerTable(teamTable)
    if currentRacer[0] != '--':
      sessionStats.append(currentRacer)
  
  return playerStats, sessionStats
  
def mergeActiveDriverStats(overviewEntries, sessionEntries):
  for driver in overviewEntries:
    for extra in sessionEntries:
      if driver[4] == extra[0]: 
        driver[-1] = extra[1] #add session cps
        #driver = driver[:-1] + (extra[1],)
        break
  return overviewEntries

def parsePages(overviewText, detailText):
  teamEntries, sessionEntries = parseDetailedPage(detailText)
  overviewEntries = parseOverviewPage(overviewText)
  sessionEntries = mergeActiveDriverStats(overviewEntries, sessionEntries)
  return (teamEntries, sessionEntries)
  
def getStatChanges(oldStats, newStats):
  if oldStats == 0:
    return newStats[1]
  statChanges = []
  # two things, 1) select updated lines from session. 2) get those same lines from teamstats, need perhaps some smart player checking, or a player id field added during scraping
  for row in newStats[1]:
    team = row[1]
    for oldRow in oldStats[1]:
      if oldRow[1] == team:
        # check overall cps change
        if row[2] != oldRow[2]:
          statChanges.append(row)
  return statChanges
  
def getTeamID(teamName, allTeams):
  sortedTeams = sorted(allTeams)
  return sortedTeams.index(teamName)

def writeTeamFiles(teamStats):
  teamFile = open('teams.csv', 'w', encoding='utf8')
  
  teamFile.write('ID,teamName,playerID,playerName\n')
  for teamName in teamStats:
    teamID = getTeamID(teamName, teamStats.keys())
    for player in teamStats[teamName]:
      teamFile.write('{0},\"{1:s}\",{2[5]},\"{2[0]:s}\"\n'.format(teamID, teamName, player))
  teamFile.close()
  
def writeFullHeaders(filename):
  f = open(filename, 'w', encoding='utf8')
  f.write('time, rank, team, total cps, cp diff, driver, session time, session average, session record, last lap, session cps, total driver cps, total time, total record, total average\n')
  f.close()
  
def writeFullUpdate(filename, time, updatedStats, teamStats):
  f = open(filename, 'a', encoding='utf8')
  for entry in updatedStats:
    #get correct teamStats
    totalMemberStats = ('--', 0, 0, 0, 0)
    for member in teamStats[entry[1]]:
      if member[0] == entry[4]:
        totalMemberStats = member
        break
    #write correct output according to headers
    s = '{0:.3f},{1[0]},{1[1]},{1[2]},{1[3]},{1[4]},{1[5]:.3f},{1[6]:.3g},{1[7]:.3g},{1[8]:.3g},{1[9]},{2[1]},{2[2]:.3f},{2[3]:.3g},{2[4]:.3g}\n'.format(time, entry, totalMemberStats)
    f.write(s)
  f.close()
    

def getPlayerID(playerName, teamName, teams):
  for teamMember in teams[teamName]:
    if playerName == teamMember[0]:
      return teamMember[5]   
  return -1 #If no active players

#test this 
def buildSiteStats(scrapeTime, prevStats, stats, sessionDict):
  data = []
  #time, session, teamID, playerID, rank, lastLap, cps(total), cpdiff(to last time)
  for i in range(len(stats[1])):
    playRecord = stats[1][i]
    team = playRecord[1]
    
    session = 0
    try:
      session = sessionDict[team]
    except:
      sessionDict[team] = 0
      
    playerID = getPlayerID(playRecord[4], team, stats[0])
    teamRecord = stats[0][team]
    currentCPDiff = teamRecord[playerID][1]
    if prevStats != 0:
      for prevRecord in prevStats[1]:
        if prevRecord[1] == team:
          prevTeamRecord = prevStats[0][team]
          currentCPDiff -= prevTeamRecord[playerID][1]
          
          if playRecord[4] != prevRecord[4]: #player changed
            prevPlayerID = getPlayerID(prevRecord[4], team, prevStats[0])
            prevPlayerCPDiff = teamRecord[prevPlayerID][1] - prevTeamRecord[prevPlayerID][1]
            
            previousPlayerLine = [scrapeTime, session, getTeamID(team, stats[0].keys()), prevPlayerID, prevRecord[0], prevRecord[-2], prevRecord[2], prevPlayerCPDiff]
            data.append(previousPlayerLine)
            session += 1
            sessionDict[team] = session
            pass
          break
      
    currentPlayerLine = [scrapeTime, session, getTeamID(team, stats[0].keys()), playerID, playRecord[0], playRecord[-2], playRecord[2], currentCPDiff]
    data.append(currentPlayerLine)
  return data
  
def writeSiteHeaders(filename):
  #time, session, teamID, playerID, rank, lastLap, cps(total), cpdiff(to last time)
  f = open(filename, 'w', encoding='utf8')
  f.write('time,session,teamID,playerID,rank,lastLap,cpsTotal,cpsChange\n')
  f.close()
    
def writeSiteData(filename, entries):
  #time, session, teamID, playerID, rank, lastLap, cps(total), cpdiff(to last time)
  pass
  f = open(filename, 'a', encoding='utf8')
  for entry in entries:
    s = '{0[0]:.3f},{0[1]},{0[2]},{0[3]},{0[4]},{0[5]:.3g},{0[6]},{0[7]}\n'.format(entry)
    f.write(s)
  f.close()
  
def runScrapeLoop(duration=1440, interval=60):
  print("Running for {0} minutes with an interval of {1} seconds".format(duration, interval))
  startTime = time.time()
  prevStats = 0
  sessionDict = {}
  writeFullHeaders(targetFile)
  writeSiteHeaders(siteFilename)
  currentScrapeTime = 0
  
  while currentScrapeTime < duration*60:
    currentScrapeTime = time.time() - startTime
    print('scraping round at time {0}'.format(currentScrapeTime))
    
    sessionPageRaw = getSite(sessionUrl)
    fullTeamPageRaw = getSite(fullTeamUrl)
    
    stats = parsePages(sessionPageRaw, fullTeamPageRaw)
    updatedStats = getStatChanges(prevStats, stats)
    
    siteData = buildSiteStats(currentScrapeTime, prevStats, stats, sessionDict)
    writeSiteData(siteFilename, siteData)
    
    prevStats = stats
    
    writeTeamFiles(stats[0])
    writeFullUpdate(targetFile, currentScrapeTime, updatedStats, stats[0])
    print('sleeping for {0} s.'.format(currentScrapeTime + startTime + interval - time.time()))
    time.sleep(currentScrapeTime + startTime + interval - time.time())


def main():
  runScrapeLoop()

if __name__ == '__main__':
  main()
