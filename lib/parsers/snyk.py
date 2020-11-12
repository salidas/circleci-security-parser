"""
Parses output generated by the Snyk CircleCI Orb.
"""

import json
import re
from bs4 import BeautifulSoup

from markdown import markdown
from packaging.version import parse as parse_version


def node_parse_unresolvables(unparsed_dependencies, reporter):
    """
    Obtains all dependencies reported by Snyk as being vulnerable, that cannot be fixed solely by updating said dependencies. 

    Snyk has unresolvable dependencies because it may be the case that a vulnerable dependency is a sub-dependency, and its parent does not have a version available that leverages a more recent (and patched) version of the vulnerable one.
    
    Furthermore, for either the child or parent dependency it can be the case that they are no longer maintained, and a vulnerability for their last version has been found; because there isn't the possibility of updating to fix this, a different solution has to be identified.
    """

    # todo: what if a>b>c and a>b>c>d are unresolvable - how can i group by recommending resolving a>b, even though the dependencies are different (a or b)

    # What we need to do now is:
    # 1) Go through each unresolvable and obtain metadata associated with them
    # 2) Deduplicate each unresolvable, grouping by their name, path and latest version (to update to) 
    # 3) Create issues for each deduplicated dependency.

    # Initiate an empty list to store the metadata
    parsed_dependencies = []

    for unparsed_dependency in unparsed_dependencies:

        # Keep track of whether this is a nested dependency or not
        sub = False

        # Gather information on the dependency
        name = unparsed_dependency["packageName"]
        version = unparsed_dependency["version"]
        path = " > ".join(unparsed_dependency["from"][1:])
        path_length = len(unparsed_dependency["from"])

        # If our path length is greater than one, then it means we're dealing with a sub-dependency.
        if path_length > 1:
            sub = True

        # Gather information on what the dependency is vulnerable to
        vulnerability_name = unparsed_dependency["title"]
        
        # Dependencies with multiple branches may have different versions to update to depending on the branch you use.
        # Rule of thumb is to recommend updating to the latest possible (stable and secure) version, so lets go through the list of versions and save the latest.
        min_fix_version = "0.0.0"
        for fixed_version in unparsed_dependency["fixedIn"]:
            if parse_version(fixed_version) > parse_version(min_fix_version):
                min_fix_version = fixed_version

        # Gather Snyk-specific information
        snyk_vulnerability_id = unparsed_dependency["id"]

        # We will not report sub-dependencies as they may not be fixable by updating the core/parent dependency
        if not sub:
            parsed_dependencies.append(
                {
                    "name": name,
                    "sub": sub,
                    "path": path,
                    "vulnerability": vulnerability_name,
                    "version": version,
                    "update_min_versions": min_fix_version,
                    "snyk_vuln_ids": [
                        snyk_vulnerability_id + " - " + vulnerability_name
                    ],
                    "raw_output": [unparsed_dependency]
                }
            )

    # Now we have parsed issues - we have to merge them per dependency, version and path.
    merged_dependencies = []

    # Go through each parsed dependency only once
    for parsed_dependency in parsed_dependencies:

        # Check if merged_dependencies has any elements. If it doesn't, we'll add one to start off with!
        if len(merged_dependencies) == 0:
            merged_dependencies.append(parsed_dependency)

        else:
            for merged in merged_dependencies:

                # Check that the dependency names are the same
                if parsed_dependency["name"] == merged["name"]:

                    # Check if the paths match
                    if parsed_dependency["path"] == merged["path"]:
                        
                        # Name and path match - we're dealing with the same instance.

                        # Merge the Snyk ids by unrolling each list of ids into one.
                        merged["snyk_vuln_ids"] = [*merged["snyk_vuln_ids"], *parsed_dependency["snyk_vuln_ids"]]

                        # Insert a new element into raw_output to contain the raw output from parsed_dependency
                        merged["raw_output"] = [*merged["raw_output"], *parsed_dependency["raw_output"]]

                        # Identify the latest version to update to
                        if parse_version(parsed_dependency["update_min_versions"]) > parse_version(merged["update_min_versions"]):
                            merged["update_min_versions"] = parsed_dependency["update_min_versions"]

                    # Same dependency, different path. Report it individually.
                    else:
                        merged_dependencies.append(parsed_dependency)

                # If the names aren't the same, we're dealing with an entirely different dependency. Add it to the list.
                else:
                    merged_dependencies.append(parsed_dependency)
                    break

    # Okay, now we have deduplicated issues - pass them to reporter for output.
    for merged_dependency in merged_dependencies:

        name = merged_dependency["name"]
        sub = merged_dependency["sub"]
        path = merged_dependency["path"]

        min_fix_version = merged_dependency["update_min_versions"]

        issue_description = name + " is a "

        # The issue's contents, grammar, etc. change depending on whether we're dealing with a core dependency or a nested/sub-dependency.
        if sub:
            issue_title = "Vulnerable Node Sub-Dependency - " + merged_dependency["name"]
            issue_description += "sub-dependency of a Node package " 
        else:
            issue_title = "Vulnerable Node Dependency - " + merged_dependency["name"]
            issue_description += "dependency "

        # We need to detail the snyk ids and their associated vuln names here.
        issue_description += "used by the project in scope. The version in use is susceptible to publicly known vulnerabilities, listed further down below.\n\n"

        issue_recommendation = "Identify whether the vulnerabilities affect functionality used by the project and understand the associated risk to the project and business.\nConsider identifying the use of alternative dependencies that are maintained and provide the same functionality.\n\n"

        if sub:
            issue_description += "This issue has been reported because the ancestor/parent package never makes use of a more recent release of " + name + " (and its included security fixes).\nThis is likely due to a requirement for functionality from older code, or a lack of maintenance resulting in an unmanaged dependency falling behind the discovery of any relevant vulnerabilities."
    
            # We can't update because the parent dependencies do not make use of a more recent version (either due to functionality or a lack of maintenance)

            issue_recommendation += "Otherwise, the sub-dependency should be updated to at least version " + min_fix_version + " to mitigate against the reported vulnerabilities.\n\nThis can be done by manually updating the sub-dependency after invoking 'npm install', or using 'npm shrinkwrap' to keep track of sub-dependencies with specific version requirements.\nSee https://docs.npmjs.com/cli/shrinkwrap and https://choyzhihao.wordpress.com/2018/02/14/using-npm-shrinkwrap-to-lock-sub-dependency-versions/ for more information. "

        else:
            issue_description += "This issue has been reported because the dependency does not have a more recent version (to update to) that contains security fixes for the above."

        issue_description += "\n\n" + name + " is vulnerable to the following Snyk IDs:"

        for vuln_id in merged_dependency["snyk_vuln_ids"]:
            issue_description += "\n- " + vuln_id

        issue_type = "dependencies"
        tool_name = "snyk_node"

        reporter.add(
            issue_type,
            tool_name,
            issue_title,
            issue_description,
            path,
            issue_recommendation,
            raw_output = merged_dependency["raw_output"],
        )

    return len(merged_dependencies)


def node_parse_resolvables(upgradable_dependencies, reporter, project_name):
    """
    Snyk kindly identifies the path of least resistance when scanning a project and reports what dependencies will, when updated, fix as many vulnerabilities as possible (either within itself or its sub-dependencies).

    We'd rather report these grouped solutions rather than reporting each individual outdated (sub-)dependency, as this wastes both the security team and project developer's time.
    """

    issue_type = "dependencies"
    tool_name = "snyk_node"

    # Iterate through the list of dependencies
    # I think we have to invoke.items() rather than just for'ing because we're dealing with a dictionary of dictionaries
    for upgrade_key, upgrade_details in upgradable_dependencies.items():

        # The title changes for each dependency so we'll have to reset it in the for loop
        title = "Vulnerable Node Dependency - "
        
        # upgrade_key is in the format dependency_name@dependency_version, so split them to get their respective values
        dependency_name, dependency_version = upgrade_key.split("@")
        dependency_upgrade_version = upgrade_details["upgradeTo"].split("@")[1]
        
        # Add the dependency name to the title. Pretty clear.
        title += dependency_name

        description = "The project in scope required the " + dependency_name + " package as a dependency; the version in use is susceptible to publicly-known vulnerabilities, listed further in the issue description.\nThese vulnerabilities could be from either " + dependency_name + " or its sub-dependencies."

        # Enumerate vulnerablities the dependency and/or its sub-dependencies expose the project to
        associated_vulnerabilities = upgrade_details["vulns"]
        description += "\n\n" + dependency_name + " or its sub-dependencies are at risk from the following:"

        # Eeport each vulnerability introduced by the package
        for vuln in associated_vulnerabilities:

            # npm-reported vulnerabilities have an id of npm:<package>:<date> so we can split this via the colon characters.
            npm_format_split = vuln.split(":")

            # If we have a length of 1 then we didn't split successfully, which means it must be in the snyk format of SNYK-<lang>-<dependency>-<uid>. No problem, we'll split per hyphen instead.
            if len(npm_format_split) == 1:
                snyk_format_split = vuln.split("-")
                subdependency_name = snyk_format_split[2]
            else:
                subdependency_name = npm_format_split[1]
            description += "\n- "

            # If the vulnerability is to do with the parent package then we don't need to display the nested hierarchy
            if dependency_name == subdependency_name.lower():
                description += vuln
            else:
                description += dependency_name + " > " + subdependency_name + " is vulnerable to " + vuln

        recommendation = "By updating " + dependency_name + " to at least version " + dependency_upgrade_version + ", " + dependency_name + " will be patched and mitigated against the vulnerabilities listed in the description."

        # Enumerate the packages that would be updated as a result of updating the parent package
        subdependency_upgrades = upgrade_details["upgrades"]
        if subdependency_upgrades:
            recommendation += "\n\nFurthermore, by updating " + dependency_name + " to " + dependency_upgrade_version + " its following sub-dependencies will be updated:"
            for subdependency in subdependency_upgrades:
                # Split the syntax into name and version again
                subdependency_name, subdependency_update_version = subdependency.split("@")

                # Sometimes the parent package is also in the list of things to be updated so ignore outputting that (as it's done in the start of the recommendation section)
                if dependency_name not in subdependency_name:
                    recommendation += "\n- " + project_name  + " > " + dependency_name + " > " + subdependency_name + " will be updated to " + subdependency_update_version

        location=upgrade_key

        reporter.add(
            issue_type,
            tool_name,
            title,
            description,
            location,
            recommendation,
            raw_output = {upgrade_key: upgrade_details},
        )

    return len(upgradable_dependencies)


def parse_node(i_file, issue_holder, logger):
    """
    Attempts to carry out multiple steps on a Snyk scan's output:
    1) Report dependencies that, when updated, will fix one or more vulnerabilities
    2) Report any dependencies that cannot be fixed by updating (i.e. if a dependency is at its latest version, is no longer supported, etc.)
    """

    i_file_json_object = json.load(i_file)

    # Check if the output is for a scan that successfully completed. If it did, then there wouldn't be an error key.
    if "error" not in i_file_json_object:

        project_name = i_file_json_object["projectName"]
        remediation_key = i_file_json_object["remediation"]

        unresolved_dependencies = remediation_key["unresolved"]
        unresolve_count = node_parse_unresolvables(unresolved_dependencies, issue_holder)

        upgradable_dependencies = remediation_key["upgrade"]
        resolve_count = node_parse_resolvables(upgradable_dependencies, issue_holder, project_name)

        logger.debug(f"> snyk: {unresolve_count + resolve_count} issues reported\n")

    else:
        logger.warning("snyk: The results of this scan apparently failed!")
        logger.warning("snyk: Please see the following error obtained from the output file:")
        logger.warning(i_file_json_object["error"] + "\n")