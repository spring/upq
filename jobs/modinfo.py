# modinfo.py, taken from
# http://springrts.com/phpbb/viewtopic.php?f=44&t=27987
# written by beherith

import os
import sys
only=''
if len(sys.argv)>1:
	only=sys.argv[1]

unitdir='\\units\\'

def getkvlua(line): #get key, value pair from a line
	k=line.partition('=')[0]
	v=line.partition('=')[2]
	k=k.strip().lower()
	v=v.strip().strip(',').strip()
	if '\"' in v:
		v=v.strip('\"')
	if '\'' in v:
		v=v.strip('\'')
	return (k,v)

def getkvtdf(line): #get key, value pair from a line
	k=line.partition('=')[0]
	v=line.partition('=')[2]
	k=k.strip()#.lower()
	v=v.strip().strip(';').strip()
	if '\"' in v:
		v=v.strip('\"')
	return (k,v)


def parselua (fln, l,d): #parse a lua table
	main={}
	while(l<len(fln)):# and '}' not in fln[l]):
		k,v=getkvlua(fln[l])
		# print '	'*d,k,v
		l+=1
		if '}' in k or '}' in v:
			break
		if v=='{':
			a,b=parselua(fln,l,d+1)
			main[k]=a
			l=b
		else:
			main[k]=v
	return main,l

def parsetdf (fln, l,d): #parse a lua table
	main={}
	while(l<len(fln)):# and '}' not in fln[l]):
		k,v=getkv(fln[l])
		print '	'*d,k,v
		l+=1
		if '[' in k or ']' in k:
			break
		if '[' in k:
			l+=1
			a,b=parselua(fln,l,d+1)
			main[k]=a
			l=b
		else:
			main[k]=v
	return main,l

def td(file,entry,params=''):
	file.write('<td '+params+'>'+entry+'</td>')

def srow(file,params=''):
	file.write('<tr '+params+'>')

def erow(file):
	file.write('</tr>\n')
def starthtml(file,t):
	file.write('<html>\n<title>'+t+'</title>\n<body>\n')
def endhtml(file):
	file.write('</body></html>\n')
def link(file,url,text):
	file.write('<a href='+url+'>'+text+'</a>')
def tdlink(file,url,text):
	file.write('<td><a href='+url+'>'+text+'</a></td>')
def br(file):
	file.write('<br/>\n')
def unitimg(file,unitname):
	link(file,unitname+'.html','<img title=\"rape\" src=\"'+unitname+'.png\" />')

def tdunitimg(file,unitname,tooltip=''):
	tdlink(file,unitname+'.html','<img title=\"'+tooltip+'\" src=\"'+unitname+'.png\" />')
# read modinfo
f=open('modinfo.lua','r')
fln=f.readlines()
f.close()
modinfo,z=parselua(fln,1,0)

#read explosions:
explosions={}
for filename in os.listdir(os.getcwd()+'/weapons/'):
	f=open('weapons/'+filename,'r')
	fln=f.readlines()
	f.close()
	if '.lua' in filename:
		weapon,z=parselua(fln,2,0)
	else:
		weapon,z=parselua(fln,2,0)
	explosions[filename.partition('.')[0]]=weapon

# for filename in os.listdir(os.getcwd()+'/unitpics/'):
	# if '.dds' in filename:
		# cmd='convert unitpics/'+filename+' '+filename.partition('.')[0]+'.png'
		# print cmd
		# os.system(cmd)


#read units:
units={}
for filename in os.listdir(os.getcwd()+'/units/'):
	if only in filename:
		f=open('units/'+filename,'r')
		fln=f.readlines()
		f.close()
		if '.lua' in filename:
			unit,z=parselua(fln,2,0)
		else:
			unit,z=parselua(fln,2,0)
		units[filename.partition('.')[0]]=unit


# f=open('armcom.lua','r')
# fln=f.readlines()
# f.close()
# unitinfo,z=parselua(fln,2,0)
# unitinfo=unitinfo.sort()
#print unitinfo
# for key in sorted(unitinfo.iterkeys()):
	# print key, unitinfo[key]

def makeheader(outf):
	starthtml(outf, modinfo['name']+' '+modinfo['version'])
	outf.write('<br/><h1>'+modinfo['name']+' '+modinfo['version']+'</h1>\n')
	br(outf)
	link(outf,'index.html','Index')
	outf.write('	')
	link(outf,'arm.html','Arm')
	outf.write('|')
	link(outf,'core.html','Core')
	br(outf)

#make main page:
def makelist(fname,filter):
	outf=open(fname,'w')
	makeheader(outf)
	outf.write('<table border=\"0\">')
	srow(outf)

	outf.write('<td><table border=\"0\">')
	srow(outf)
	cnt=0
	for key in sorted (units.iterkeys()):
		if filter in key:
			cnt+=1
	td(outf,str(cnt)+' units in list')
	erow(outf)

	srow(outf, 'bgcolor=#aaaaff')
	td(outf,'Name')
	td(outf,'Unitname')
	td(outf,'Description')
	erow(outf)
	i=0
	for key in sorted (units.iterkeys()):
		if filter not in key:
			continue
		i+=1
		if i%2==0:
			p='bgcolor=#ddddff'
		else:
			p=''
		srow(outf,p)
		tdlink(outf,key+'.html',key)
		td(outf,units[key]['name'])
		td(outf,units[key]['description'])
		erow(outf)
	outf.write('</table></td><td valign=\"top\"><table border=\"0\"><tr><td>')
	#plants
	outf.write('Plants:</td></tr>')

	for key in sorted (units.iterkeys()):
		if filter not in key:
			continue
		if 'builder' in units[key] and 'acceleration' in units[key] and units[key]['builder']=='true' and units[key]['acceleration']=='0':
			outf.write('<tr>')
			tdunitimg(outf,key,key+' - '+units[key]['name'])
			outf.write('</tr>')
	outf.write('</table>')
	outf.write('</td>')


	outf.write('<td valign=\"top\">')
	outf.write('<table border=\"0\"><tr><td>Builders:</td></tr>')

	for key in sorted (units.iterkeys()):
		if filter not in key:
			continue
		if 'buildoptions' in units[key] and 'acceleration' in units[key] and units[key]['builder']=='true' and units[key]['acceleration']!='0':
			outf.write('<tr>')
			tdunitimg(outf,key,key+' - '+units[key]['name'])
			outf.write('</tr>')
	outf.write('</table>')
	outf.write('</td>')
	outf.write('</td>')
	erow(outf)
	outf.write('</table>')
	outf.write('</table>')
	endhtml(outf)

makelist('index.html','')
makelist('arm.html','arm')
makelist('core.html','cor')
def writel(outf,mainl,id,header):
	mainl.sort()
	i=0
	outf.write('<tr><th colspan=\"2\">'+header+'</th><tr>')
	for l in mainl:
		if l not in units[id]:
			continue
		i+=1
		if i%2==1:
			srow(outf)
		else:
			srow(outf,'bgcolor=#ddddff')
		td(outf,l)
		td(outf,units[id][l])
		erow(outf)
def bold(str):
	return '<b>'+str+'</b>'
def hr(outf):
	outf.write('<tr><td colspan=\"2\"><hr/></td></tr>\n')
def writeweapon(outf,k,v):
	hr(outf)
	srow(outf,'bgcolor=#aaaaff')
	td(outf,'Weapon name')
	td(outf,k)
	erow(outf)
	i=0
	for k2 in sorted(v.iterkeys()):
		if type(v[k2]).__name__!='dict':
			i+=1
			if i%2==1:
				srow(outf)
			else:
				srow(outf,'bgcolor=#ddddff')
			td(outf,k2)
			td(outf,v[k2])
			erow(outf)
		else:
			srow(outf)
			td(outf,k2)
			outf.write('<td><table border=\"0\" cellspacing="0">') ## TABLE 5 START
			srow(outf,'bgcolor=#aaaaff')
			td(outf,'Target')
			td(outf,'Damage')
			td(outf,'DPS')
			erow(outf)
			for k3, v3 in v[k2].iteritems():
				srow(outf,'bgcolor=#ffaaaa')
				td(outf,k3)
				td(outf,v3)
				if 'reloadtime' in v:
					td(outf,'%.2f'%(float(v3)/float(v['reloadtime'])))
				else:
					td(outf,'-')
				erow(outf)

			outf.write('</table>')#TABLE 5 END
			erow(outf)

def unitpage(id):
	outf=open(id+'.html','w')
	makeheader(outf)
	outf.write('<table border=\"0\">')## TABLE 1 START
	srow(outf, 'bgcolor=#aaaaff')
	td(outf,'<h3>'+bold(units[id]['name'])+' - '+units[id]['description']+'</h3>\n','colspan=\"3\"')
	erow(outf)
	srow(outf)
	outf.write('<td valign=\"top\"><table border=\"0\" cellspacing="0">') ## TABLE 2 START
	srow(outf)
	tdunitimg(outf,id,id+' - '+units[id]['name'])
	erow(outf)
	srow(outf)
	td(outf,id)
	erow(outf)
	if 'buildoptions' in units[id]:
		srow(outf)
		td(outf,bold('Can Build:'))
		erow(outf)
		for k,v in units[id]['buildoptions'].iteritems():
			srow(outf)
			tdunitimg(outf,v,v+' - '+units[v]['name'])
			erow(outf)
	srow(outf)
	td(outf,bold('Built by:'))
	erow(outf)
	for key in sorted (units.iterkeys()):
		if 'buildoptions' in units[key] and id in units[key]['buildoptions'].viewvalues():
			srow(outf)
			tdunitimg(outf,key,key+' - '+units[key]['name'])
			erow(outf)
	outf.write('</table></td><td align=\"left\" valign=\"top\"><table border=\"0\" cellspacing="0">') ## TABLE 2 end TABLE 3 START

	mainl=['commander','maxdamage','buildcostenergy','buildcostmetal','buildtime','maxvelocity','category']
	writel(outf,mainl,id,'Basic settings:')

	hr(outf)
	detectionl=['sightdistance','radardistance','sonardistance','cloakcost','cloakcostmoving','mincloakdistance','seismicsignature','radardistancejam','stealth']
	writel(outf,detectionl,id,'Detection settings:')
	hr(outf)

	pathl=['acceleration','brakerate','footprintx','footprintz','maxslope','maxvelocity','maxwaterdepth','movementclass','turnrate','canmove']
	writel(outf,pathl,id,'Pathfinding and movement related:')
	hr(outf)


	conl=['builder','workertime','cancapture','builddistance','metalmake','energymake','energyuse','activatewhenbuilt','onoffable','extractsmetal','metalstorage']
	writel(outf,conl,id,'Construction settings:')
	hr(outf)
	otherlist=[]
	for k in sorted(units[id].iterkeys()):
		if k not in mainl and k not in detectionl and k not in pathl and k not in conl and type(units[id][k]).__name__!='dict':
			otherlist.append(k)

	writel(outf,otherlist,id,'Other settings:')
	hr(outf)

	outf.write('</table>')#TABLE 3 END
	outf.write('</td>')

	outf.write('<td align=\"left\" valign=\"top\"><table border=\"0\" cellspacing="0">') ## TABLE 4 START
	outf.write('<tr><th colspan=\"2\">'+'Weapon Definitions'+'</th><tr>')
	if 'weapondefs' in units[id]:
		for k,v in units[id]['weapondefs'].iteritems():
			writeweapon(outf,k,v)

	if 'explodeas' in units[id]:
		writeweapon(outf,units[id]['explodeas'],explosions[units[id]['explodeas'].lower()])
	if 'selfdestructas' in units[id]:
		writeweapon(outf,units[id]['selfdestructas'],explosions[units[id]['selfdestructas'].lower()])
	outf.write('</table>')#TABLE 4 END
	outf.write('</td>')
	erow(outf)
	outf.write('</table>')#TABLE 1 END


	endhtml(outf)


for u in units.iterkeys():
	unitpage(u)














#-------------------------------------------|
#BA $Version								|
#-------------------------------------------|
#Index | sides arm/core						|
#-------------------------------------------|
#Unitname									|
#-------------------------------------------|
#unitpic	|Main info:		|WEAPONS		|
#unitname	|health			|1 pew dps 		|
#-----------|metal			|---------------|
#Can build:	|energy			|weapon1allinfo-|
#1			|buildtime		|				|
#2			|cost			|				|
#3			|---------------|				|
#4			|allelse		|				|
#Built by:	|...			|				|
#			|				|				|
#--------------------------------------------
