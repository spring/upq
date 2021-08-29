import requests




def DictEquals(a, b):
	res = True

	if isinstance(a, list):
		for i in range(0, len(a)):
			res &= DictEquals(a[i], b[i])
		return res
	if isinstance(a, dict):
		for k, v in a.items():
			if v != b[k]:
				print("Unequal: %s != %s" %(v, b[k]))
				return False
		return res
	print(type(a))
	assert(False)

expected = [{'category': 'map', 'filename': 'deltasiegedry.sd7', 'md5': 'c66a147280a803193d8fa8ddf6bf9ea1', 'mirrors': ['https://springfiles.springrts.com/files/maps/deltasiegedry.sd7'], 'name': 'DeltaSiegeDry', 'sdp': '8ab1212b53ebd6d4042a26451c89b279', 'size': 17640007, 'springname': 'DeltaSiegeDry', 'tags': [], 'version': ''}]
r = requests.get("https://springfiles.springrts.com/json.php?springname=DeltaSiegeDry")
assert(DictEquals(expected, r.json()))

expected = [{"category":"engine_windows64","filename":"spring_105.0_win64-minimal-portable.7z","md5":"2b3443fa287744b20bb69540465df38a","mirrors":["https://springrts.com/dl/buildbot/default/master/105.0/win64/spring_105.0_win64-minimal-portable.7z"],"name":"spring","sdp":None,"size":11978575,"springname":"spring 105.0","tags":[],"version":"105.0"}]
r = requests.get("https://springfiles.springrts.com/json.php?springname=spring%20105.0&category=engine_windows64")
assert(DictEquals(expected, r.json()))


