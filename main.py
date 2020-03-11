#!/usr/bin/env python3

import argparse
import os
import traceback

from lib.input.Loader import Loader
from lib.issues.IssueHolder import IssueHolder
from lib.parsers.CoreParser import CoreParser
from lib.output.OutputWrapper import OutputWrapper
from lib.output.Reporter import Reporter

if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument(
		"-i",
		"--input",
		help="The directory to load security tool output from",
		required=True
	)
	parser.add_argument(
		"-o",
		"--output",
		help="The directory to store the parsed data to",
		default="."
	)
	parser.add_argument(
		"-v",
		"--verbose",
		help="Sets verbose mode",
		action="store_true"
	)
	parser.add_argument(
		"--fail",
		help="Return an error code for",
		choices=["critical", "high", "medium", "low", "informational"]
	)

	arguments = parser.parse_args()

	# Create variables to store where to load and save files from/to.
	input_folder = arguments.input
	output_folder = arguments.output
	verbose = arguments.verbose

	# Instantiate the various Object instances that we require
	output_wrapper = OutputWrapper(verbose)

	print()
	output_wrapper.add("CircleCI Security Output Parser (CSOP) - Hi there!")
	output_wrapper.add("To be used with https://https://circleci.com/orbs/registry/orb/salidas/security\n")
	output_wrapper.flush(show_time=False)

	issue_holder = IssueHolder(output_wrapper)
	loader = Loader(output_wrapper)

	# Get the absolute path for the output folder
	output_folder = os.path.abspath(output_folder)

	reporter = Reporter(output_wrapper, issue_holder, output_folder)

	# Create a variable to store the severity, but only if it exists.
	if arguments.fail:
		fail_threshold = arguments.fail
	else:
		fail_threshold = "off"

	output_wrapper.set_title("fail threshold: " + fail_threshold)
	output_wrapper.flush(verbose=True)

	# Get a list of files containing parsable tool output
	files = loader.load_from_folder(input_folder)

	# load_from_folder will return 0 if no files were found
	if files != 0:

		# Create Reporter and Parser objects then pass their required parameters to them.
		parser = CoreParser(output_wrapper, issue_holder, files)

		# Check if we have a severity threshold. If we do, error_code will be > 0 so return that value to force the build to fail.
		error_code = parser.check_threshold(fail_threshold)

		if error_code != 0:
			output_wrapper.set_title("[x] Exiting script with return code " + str(error_code) + "!")
			output_wrapper.flush()
			exit(error_code)

		reporter.create_csv_report()
		
	else:
		# We didn't find any files.
		output_wrapper.set_title("[x] No supported files were found! Did you target the right directory?")
		output_wrapper.flush()
