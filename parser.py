
# -*- coding: utf-8 -*-

import json
import os
import constants
import re
from pprint import pprint

class Parser:
	"""
	Redirects files to their respective parsers to be processed.
	"""

	parsed_tools = {
		"nancy": "nancy",
		"burrow": "burrow",
		"Snyk [Node]": "snyk_node",
	}


	# """
	# Method that reads Anchore tool output and reports container findings to Reporter.
	# """
	# def parse_anchore(self, i_file):
	# 	a_output = json.load(i_file)
	# 	# Anchore outputs various information to multiple files,
	# 	# but we currently only care about the file containing identified vulnerabilities.
	# 	if "_latest-vuln" in i_file.name:
	# 		for vulnerability in a_output["vulnerabilities"]:
	# 		 	self.reporter.add_finding(
	# 				report_type="container_images",
	# 				tool="Anchore",
	# 				name="[" + vulnerability["severity"] + "] - " + vulnerability["vuln"],
	# 				description="A container package was identified as outdated and vulnerable.",
	# 				location="Package: " + vulnerability["package"],
	# 				raw_output=vulnerability,
	# 				i_file=i_file
	# 			)

	# """
	# Method that parses audit-ci output for packages using npm, forwarding vulnerable node dependency issues to Reporter.
	# """
	# def parse_audit_ci_npm(self, i_file):
	# 	report_type = "dependencies"
	# 	tool = "audit-ci [Node] [npm]"
	# 	# Some audit-ci runs do not generate output, let alone valid JSON
	# 	# To catch these we try to run json.load to parse the JSON.
	# 	# If the JSON is not well formed, then chances are there's no vulns.
	# 	# We'll inform the user, and carry on. It's okay.
	# 	# If we fail to parse then we can just grab the artifact from CircleCI and manually parse it.
	# 	try:
	# 		ac_output = json.load(i_file)
			
	# 		# Audit-CI output has a dictionary of advisories, with each key being the advisor number
	# 		# (similar to a CVE) and the value being another dictionary with further info.
	# 		# We may have to go recursive.
	# 		for advisory_number, advisory_info in ac_output["advisories"].items():

	# 			name = advisory_info["title"]

	# 			# If the issue has a severity prepend it to the issue name/title
	# 			if advisory_info["severity"]:
	# 				name = "[" + advisory_info["severity"].capitalize() + "] " + name

	# 			# Check if there's a CVE associated, in which case add this to the issue title
	# 			if advisory_info["cves"]:
	# 				name = "[" + ", ".join(advisory_info["cves"]) + "] " + name

	# 			# Description example: "123: This is the vuln issue. This is the vuln recommendation."
	# 			description = str(advisory_number) + ": " + advisory_info["overview"].rstrip() + " " + advisory_info["recommendation"].replace("\n", " ")

	# 			# Location example: "foobar 1.2.3 (foo>bar>foobar, bar>foo>foobar)"
	# 			location = "Package: " + advisory_info["module_name"] + " " + advisory_info["findings"][0]["version"] + " (" + ", ".join(advisory_info["findings"][0]["paths"]) + ")"

	# 			self.reporter.add_finding(
	# 				report_type=report_type,
	# 				tool=tool,
	# 				name=name,
	# 				description=description,
	# 				location=location,
	# 				raw_output=advisory_info,
	# 				i_file=i_file
	# 			)

	# 	except ValueError:
	# 		print("- Unable to parse JSON from " + os.path.basename(i_file.name) + "; skipping.")
		
	# 	print("- [✓] Done!")


	# """
	# Method that parses audit-ci output for packages using Yarn, forwarding vulnerable node dependency issues to Reporter.

	# audit-ci's parsing of Yarn packages is hella silly in my opinion.
	# It will output a JSON object for each vulnerability it finds, but does not bunch them together into an array
	# so that json.load() will not accept it. You can't slice the file to get each JSON body either as they are
	# prettified (so not single lined) and of different line lengths; ugh.
	# """
	# def parse_audit_ci_yarn(self, i_file):
	# 	report_type = "dependencies"
	# 	tool = "audit-ci [Node] [Yarn]"
		
	# 	formatted = []

	# 	# I'm going to try to fix the file first, by looking for closing brackets without whitespace before them (i.e. the last
	# 	# bracket of an object), and adding a comma to these (bar the last object, of course.)
	# 	# Afterwards, I will add opening and closing square brackets to the entire file to convert it into an array of JSON
	# 	# objects; json.load should be happy then.
	# 	lines = i_file.readlines()
	# 	for line in lines:
	# 		line = line.rstrip()
	# 		if line[0] != " " and line[-1] == "}":
	# 			formatted.append(line.rstrip() + ",")
	# 		else: 
	# 			formatted.append(line.rstrip())

	# 	# Get the first element and add an open square bracket to the beginning.
	# 	formatted[0] = "[" + formatted[0]
	# 	# Get the last element, remove the comma and replace it with a closed square bracket.
	# 	formatted[-1] = formatted[-1].replace(",", "]")

	# 	# Now we have to save the formatted array to a temporary file. 
	# 	import uuid
	# 	name = str(uuid.uuid4())
	# 	full_location = "/tmp/" + name
	# 	with open(full_location, 'w') as f:
	# 		f.write("\n".join(formatted))

	# 	# Using the temporary file, we can actually do the original parsing.
	# 	with open(full_location, 'r') as f:
	# 		try:
	# 			issues = json.load(f)
	# 			# Iterate through the individual issue objects, aside from the last objects (because it's just a
	# 			# summary count of the previous issues)
	# 			for issue in issues[:-1]:
	# 				advisory = issue['data']['advisory']

	# 				# resolution = issue['data']['resolution']
	# 				# pprint(resolution)

	# 				self.reporter.add_finding(
	# 					report_type=report_type,
	# 					tool=tool,
	# 					name="[" + advisory["severity"].capitalize() + "] " + advisory["title"],
	# 					description=advisory["overview"],
	# 					recommendation=advisory["recommendation"],
	# 					location="Package: " + "\n".join(advisory["findings"][0]["paths"]),
	# 					raw_output=advisory,
	# 					i_file=i_file
	# 				)

	# 		except ValueError:
	# 			print("- Unable to parse JSON from " + os.path.basename(i_file.name) + "; skipping.")

	# 	# Don't forget to delete the temporarily created file!
	# 	os.remove(full_location)

	# 	print("- [✓] Done!")


	# """
	# Method that parses detectsecrets output and forwards any potential credentials to Reporter.
	# """
	# def parse_detectsecrets(self, i_file):
	# 	ds_output = json.load(i_file)

	# 	for name, information in ds_output["results"].items():
	# 		self.reporter.add_finding(
	# 			report_type="secrets",
	# 			tool="detect-secrets",
	# 			name=information[0]["type"],
	# 			description="Potential credential found. Please check the reported file.",
	# 			location=str(name) + ", line " + str(information[0]["line_number"]),
	# 			raw_output=str(name) + ": " + str(information),
	# 			i_file=i_file
	# 		)


	# """
	# Method that parses DumpsterDiver output and forwards any potential credentials to Reporter.
	# """
	# def parse_dumpsterdiver(self, i_file):
	# 	dd_output = json.load(i_file) 

	# 	# If the JSON is an empty list, then there are no findings.
	# 	if len(dd_output) != 0:

	# 		# The loaded JSON is a list of findings.
	# 		for finding in dd_output:

	# 			# Check if a rule was triggered
	# 			if "Advanced rule" in finding["Finding"]:
	# 				# name = "DumpsterDiver Rule Triggered"
	# 				description = "A DumpsterDiver rule was triggered. Please check the raw output for further information."
	# 			else:
	# 				description = "Potential credential found: " + finding["Details"]["String"]

	# 			# Save finding, ready for reporting
	# 			self.reporter.add_finding(
	# 				report_type="secrets",
	# 				tool="DumpsterDiver",
	# 				name=finding["Finding"],
	# 				description=description,
	# 				location=finding["File"],
	# 				raw_output=finding,
	# 				i_file=i_file
	# 			)

	# 	else:
	# 		# Move on.
	# 		print("- [x] No output found in file; skipping.")


	def nancy(self, i_file):
		from lib import nancy
		nancy.parse(i_file, self.reporter)


	def burrow(self, i_file):
		from lib import burrow
		burrow.parse(i_file, self.reporter)


	def snyk_node(self, i_file):
		from lib import snyk
		snyk.parse_node(i_file, self.reporter)


	def get_file_source(self, i_file):
		"""
		Iterates through a dictionary of tools that can be parsed and compares their associated filename patterns with the file currently being processed.
		"""

		# Get the tool name ("Snyk [Node]" for example) and its associated matching filename ("snyk_node"), both from parsed_tools in KV format
		for toolname, filename_pattern in self.parsed_tools.items():
			# Alright, we've found a file from a tool that we support
			if filename_pattern in i_file.name:
				# Lets obtain a link to the correct tool parser we'll be using. Thanks getattr, you're the best!
				print("- Tool identified: " + toolname)
				# We could squash the below into one line but it's more confusing to understand if you don't know getattr.
				file_parser_method = getattr(self, filename_pattern)
				file_parser_method(i_file)


	def consume(self, files, reporter):
		"""
		Absorbs a list of files (and a reporter object) and attempts to have each file parsed depending on the tool (and support)
		"""

		# Set the output folder variable in case we need to save parsed output
		self.reporter = reporter

		for i_file in files:
			print(">" * constants.SEPARATOR_LENGTH)
			print("Parsing: " + os.path.basename(i_file.name))
			print("-" * constants.SEPARATOR_LENGTH)

			self.get_file_source(i_file)

			print("<" * constants.SEPARATOR_LENGTH + "\n")


