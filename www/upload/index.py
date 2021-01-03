#!/usr/bin/python3

import cgi, os

print("Content-type: text/html\n")

def ShowForm(vars):
	with open("form.html", "r") as f:
		content = f.read()
	for k, v in vars:
		content = content.replace("%" + k + "%", v)
	print(content)


def save_uploaded_file (fileitem, upload_dir):
	os.make_dirs(upload_dir, exist_ok=True)

	filename = fileitem.filename.replace("/", "_")
	with open(os.path.join(upload_dir, filename), 'wb') as fout:
		while 1:
			chunk = fileitem.file.read(100000)
			if not chunk: break
			fout.write(chunk)
	return filename

def CheckAuth(username, password):
	import xmlrpc.client
	proxy = xmlrpc.client.ServerProxy("https://springrts.com/api/uber/xmlrpc")
	res = proxy.get_account_info(username, password)
	print(res)

def CheckFields(form, required):
	for k in required:
		if not k in form:
			return False
	return True

def SaveUploadedFile(form):
	if not CheckFields(form, ["filename", "username", "password"]):
		return
	username = form["username"]
	password = form["password"]
	if not CheckAuth(username, password):
		return
	fileitem = form["filename"]
	if not fileitem.file:
		return
	filename = save_uploaded_file(fileitem, "/tmp/springfiles-upload")
	#FIXME: parse and add to db/mirror using pyseccomp

form = cgi.FieldStorage()

SaveUploadedFile(form)

ShowForm({})

