"""
Parses output generated by the burrow tool.
"""

import json

def parse(i_file, reporter):
    """
    Isolates each individual burrow finding and sends them to reporter.
    """

    # The findings are essentially of the same structure, so we'll give them all the same skeleton.
    issue_type = "secrets"
    tool_name = "burrow"

    ifile_name = i_file.name

    recommendation = "Please identify whether this finding is a true or false positive. Consider adding the file and line to .burrowignore to prevent future reports if this issue is the latter."

    i_file_json_object = json.load(i_file)

    findings = i_file_json_object["findings"]

    print('- ' + str(len(findings)) + " findings reported by burrow!")

    for finding in findings:

        title = finding["match"]
        path = finding["file"]

        description = "A potentially hardcoded secret has been identified."
        
        location = path
        if isinstance(finding["line"], int):
            line = str(finding["line"])
            location += ":" + line

        raw_output = finding

        # Create an issue using all of the fields we have populated with values
        reporter.add(
            issue_type,
            tool_name,
            title,
            description,
            location,
            recommendation,
            ifile_name,
            raw_output = raw_output     
        )

    print("- [✓] Done!")