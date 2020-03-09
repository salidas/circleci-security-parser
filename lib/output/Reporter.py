import csv
import hashlib
import os
import time

from lib.issues.Issue import Issue, get_fieldnames
from lib.issues.IssueHolder import IssueHolder
from lib.output.OutputWrapper import OutputWrapper

class Reporter:


    def __init__(self, o_folder):
        self.output_wrapper = OutputWrapper()
        self.issue_holder = IssueHolder()
        self.temp_findings = []

        # Set up the filename_variables in preparation
        username = ""
        repo = ""
        branch = ""
        job_name = ""

        # Check if specific CircleCI environments are available and add their values to the output filename.
        if "CIRCLE_PROJECT_USERNAME" in os.environ:
            username = os.getenv("CIRCLE_PROJECT_USERNAME") + "_"
        if "CIRCLE_PROJECT_REPONAME" in os.environ:
            repo = os.getenv("CIRCLE_PROJECT_REPONAME").replace("_", "-") + "_"
        if "CIRCLE_BRANCH" in os.environ:
            branch = os.getenv("CIRCLE_BRANCH").replace("/", "-").replace("_", "-")
        if "CIRCLE_JOB" in os.environ:
            job_name = os.getenv("CIRCLE_JOB").replace("/", "-").replace("_", "-") + "_"

        # Determine the exact path to save the parsed output to.
        self.filename = "parsed_output_" + \
                        username + \
                        repo + \
                        job_name + \
                        str(int(time.time())) + ".csv"
        self.o_folder = o_folder
        self.ofile_name = self.o_folder + "/" + self.filename

        self.output_wrapper.set_title("Saving to: " + self.ofile_name)
        self.output_wrapper.flush()


    def get_issues(self):
        return self.issue_holder.get_issues()


    """
    Inserts a new issue to the list; the parameters force a reporting standard to be followed (i.e. each must have the first six parameters as "headings" in a report)
    """
    def add(
        self,
        issue_type,
        tool_name,
        title,
        description,
        location,
        recommendation,
        ifile_name = "",
        raw_output = "n/a",
        severity = "low",
        cve_value = "n/a",
    ):

        self.issue_holder.add(
            Issue(
                issue_type,
                tool_name,
                title,
                description,
                location,
                recommendation,
                ifile_name=ifile_name,
                raw_output=raw_output,
                severity=severity,
                cve_value=cve_value
            )
        )

    def deduplicate(self):
        """
        Goes through the list of submitted issues and removes any issues that have been reported more than once.

        The description and location of each issue is merged together and hashed - if this hash has not been dealt with (this parsing round) before then we'll accept it, otherwise ignore it.l¬
        """

        self.output_wrapper.set_title("Deduplicating...")

        # Create an empty list that will contain the unique issues.
        deduplicated_findings = []

        # Use a secondary list that will only contain issue descriptions as
        # keys. We'll use hashes of the combination of the description and 
        # location as existence oracles
        issue_hash_oracle = []

        # For each finding in the original list...
        for element in list(self.issue_holder.get_issues()):

            issue = element.get()

            issue_hash = hashlib.sha256(
                # issue["description"].encode("utf-8") + b":" + issue["location"].encode("utf-8")
                issue["description"].encode("utf-8") + b":" + issue["location"].encode("utf-8")
            ).hexdigest()

            # Check if the description for the issue's not already in the lookup table list
            if issue_hash not in issue_hash_oracle:

                # If we've reached this line, then it's a new issue we haven't seen before and we can report it.
                # Add the description to the oracle list
                issue_hash_oracle.append(issue_hash)

                # Add the full issue to the new list
                deduplicated_findings.append(issue)

        self.output_wrapper.add("- Array size: " + str(self.issue_holder.size()))
        self.output_wrapper.add("- Array size after deduplication: " + str(len(deduplicated_findings)))
        self.output_wrapper.flush()

        return deduplicated_findings


    def create_report(self):

        if self.issue_holder.size() == 0:
            self.output_wrapper.set_title("There were no issues found during this job.")
            self.output_wrapper.add("- Skipping CSV report creation...")
            self.output_wrapper.flush()
            # exit(6)

        self.output_wrapper.set_title("Attempting to generate CSV report...")

        self.temp_findings = self.deduplicate()

        fieldnames = [
            "issue_type",
            "tool_name",
            "title",
            "severity",
            "description",
            "cve_value",
            "location",
            "recommendation",
            "raw_output"
        ]

        with open(self.ofile_name, 'w+', newline="\n") as ofile_object:
            writer = csv.DictWriter(ofile_object, fieldnames=get_fieldnames())
            writer.writeheader()

            # Write a row in csv format for each finding that has been reported so far
            for finding in self.temp_findings:
                writer.writerow(finding)

        self.output_wrapper.add("[✓] Done!")
        self.output_wrapper.flush()
